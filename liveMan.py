#!/usr/bin/python
# coding:utf-8

# @FileName:    liveMan.py
# @Time:        2024/1/2 21:51
# @Author:      bubu
# @Project:     douyinLiveWebFetcher

import asyncio
import codecs
from collections import deque
import gzip
import hashlib
import logging
import random
import re
import string
import subprocess
import threading
import urllib.parse
from contextlib import contextmanager
from py_mini_racer import MiniRacer
from unittest.mock import patch

import requests
import websocket

from protobuf.douyin import *

from component.message_handler import MessageHandler

# Handler = MessageHandler()


@contextmanager
def patched_popen_encoding(encoding='utf-8'):
    original_popen_init = subprocess.Popen.__init__

    def new_popen_init(self, *args, **kwargs):
        kwargs['encoding'] = encoding
        original_popen_init(self, *args, **kwargs)

    with patch.object(subprocess.Popen, '__init__', new_popen_init):
        yield


def generateSignature(wss, script_file='sign.js'):
    """
    出现gbk编码问题则修改 python模块subprocess.py的源码中Popen类的__init__函数参数encoding值为 "utf-8"
    """
    params = ("live_id,aid,version_code,webcast_sdk_version,"
              "room_id,sub_room_id,sub_channel_id,did_rule,"
              "user_unique_id,device_platform,device_type,ac,"
              "identity").split(',')
    wss_params = urllib.parse.urlparse(wss).query.split('&')
    wss_maps = {i.split('=')[0]: i.split("=")[-1] for i in wss_params}
    tpl_params = [f"{i}={wss_maps.get(i, '')}" for i in params]
    param = ','.join(tpl_params)
    md5 = hashlib.md5()
    md5.update(param.encode())
    md5_param = md5.hexdigest()

    with codecs.open(script_file, 'r', encoding='utf8') as f:
        script = f.read()

    ctx = MiniRacer()
    ctx.eval(script)

    try:
        signature = ctx.call("get_sign", md5_param)
        return signature
    except Exception as e:
        logging.error(e)

    # 以下代码对应js脚本为sign_v0.js
    # context = execjs.compile(script)
    # with patched_popen_encoding(encoding='utf-8'):
    #     ret = context.call('getSign', {'X-MS-STUB': md5_param})
    # return ret.get('X-Bogus')


def generateMsToken(length=107):
    """
    产生请求头部cookie中的msToken字段，其实为随机的107位字符
    :param length:字符位数
    :return:msToken
    """
    random_str = ''
    base_str = string.ascii_letters + string.digits + '=_'
    _len = len(base_str) - 1
    for _ in range(length):
        random_str += base_str[random.randint(0, _len)]
    return random_str


class DouyinLiveWebFetcher:

    def __init__(self, live_id, redis_client):
        """
        直播间弹幕抓取对象
        :param live_id: 直播间的直播id，打开直播间web首页的链接如：https://live.douyin.com/261378947940，
                        其中的261378947940即是live_id
        """
        self.recent_like_users = set()  # 存储最近点赞用户的ID
        self.recent_like_queue = deque(maxlen=10)  # 维护最近10个点赞用户的队列

        self.__ttwid = None
        self.__room_id = None
        self.live_id = live_id
        self.live_url = "https://live.douyin.com/"
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
                          "Chrome/120.0.0.0 Safari/537.36"

        self.heartbeat_interval = 15  # 心跳间隔时间，单位为秒
        self.heartbeat_timer = None  # 心跳定时器

        # 初始化 MessageHandler，并传入 Redis 客户端
        self.message_handler = MessageHandler(redis_client)

    def start(self):
        self._connectWebSocket()

    def stop(self):
        if self.ws:
            self.ws.close()
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()
        self.recent_like_users.clear()
        self.recent_like_queue.clear()

    def _start_heartbeat(self):
        """
        启动心跳定时器
        """
        self.heartbeat_timer = threading.Timer(
            self.heartbeat_interval, self._send_heartbeat)
        self.heartbeat_timer.start()

    def _send_heartbeat(self):
        """
        发送心跳包
        """
        if self.ws and self.ws.sock and self.ws.sock.connected:
            try:
                # 发送心跳包
                self.ws.send("heartbeat", websocket.ABNF.OPCODE_PING)
                # logging.info("[!] 发送心跳检查...")
            except Exception as e:
                logging.error(f"[?] 心跳检查异常: {e}")
            finally:
                # 重新启动心跳定时器
                self._start_heartbeat()
        else:
            logging.info("[-] WebSocket连接断开，停止心跳检查。")

    @property
    def ttwid(self):
        """
        产生请求头部cookie中的ttwid字段，访问抖音网页版直播间首页可以获取到响应cookie中的ttwid
        :return: ttwid
        """
        if self.__ttwid:
            return self.__ttwid
        headers = {
            "User-Agent": self.user_agent,
        }
        try:
            response = requests.get(self.live_url, headers=headers)
            response.raise_for_status()
        except Exception as err:
            logging.error("【X】Request the live url error: ", err)
        else:
            self.__ttwid = response.cookies.get('ttwid')
            return self.__ttwid

    @property
    def room_id(self):
        """
        根据直播间的地址获取到真正的直播间roomId，有时会有错误，可以重试请求解决
        :return:room_id
        """
        if self.__room_id:
            return self.__room_id
        url = self.live_url + self.live_id
        headers = {
            "User-Agent": self.user_agent,
            "cookie": f"ttwid={self.ttwid}&msToken={generateMsToken()}; __ac_nonce=0123407cc00a9e438deb4",
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except Exception as err:
            logging.error("【X】Request the live room url error: ", err)
        else:
            match = re.search(r'roomId\\":\\"(\d+)\\"', response.text)
            if match is None or len(match.groups()) < 1:
                logging.warning("【X】No match found for roomId")

            self.__room_id = match.group(1)

            return self.__room_id

    def _connectWebSocket(self):
        """
        连接抖音直播间websocket服务器，请求直播间数据
        """
        wss = ("wss://webcast5-ws-web-hl.douyin.com/webcast/im/push/v2/?app_name=douyin_web"
               "&version_code=180800&webcast_sdk_version=1.0.14-beta.0"
               "&update_version_code=1.0.14-beta.0&compress=gzip&device_platform=web&cookie_enabled=true"
               "&screen_width=1536&screen_height=864&browser_language=zh-CN&browser_platform=Win32"
               "&browser_name=Mozilla"
               "&browser_version=5.0%20(Windows%20NT%2010.0;%20Win64;%20x64)%20AppleWebKit/537.36%20(KHTML,"
               "%20like%20Gecko)%20Chrome/126.0.0.0%20Safari/537.36"
               "&browser_online=true&tz_name=Asia/Shanghai"
               "&cursor=d-1_u-1_fh-7392091211001140287_t-1721106114633_r-1"
               f"&internal_ext=internal_src:dim|wss_push_room_id:{
                   self.room_id}|wss_push_did:7319483754668557238"
               f"|first_req_ms:1721106114541|fetch_time:1721106114633|seq:1|wss_info:0-1721106114633-0-0|"
               f"wrds_v:7392094459690748497"
               f"&host=https://live.douyin.com&aid=6383&live_id=1&did_rule=3&endpoint=live_pc&support_wrds=1"
               f"&user_unique_id=7319483754668557238&im_path=/webcast/im/fetch/&identity=audience"
               f"&need_persist_msg_count=15&insert_task_id=&live_reason=&room_id={self.room_id}&heartbeatDuration=0")

        signature = generateSignature(wss)
        wss += f"&signature={signature}"

        headers = {
            "cookie": f"ttwid={self.ttwid}",
            'user-agent': self.user_agent,
        }
        self.ws = websocket.WebSocketApp(wss,
                                         header=headers,
                                         on_open=self._wsOnOpen,
                                         on_message=self._wsOnMessage,
                                         on_error=self._wsOnError,
                                         on_close=self._wsOnClose)
        try:
            self.ws.run_forever()
        except Exception:
            self.stop()
            raise

    def _wsOnOpen(self, ws):
        """
        连接建立成功
        """
        logging.info("[+] WebSocket已连接.")
        # 启动心跳定时器
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()
        self._start_heartbeat()

    def _wsOnMessage(self, ws, message):
        """
        接收到数据
        :param ws: websocket实例
        :param message: 数据
        """
        try:
            # 根据proto结构体解析对象
            package = PushFrame().parse(message)
            response = Response().parse(gzip.decompress(package.payload))

            # 返回直播间服务器链接存活确认消息，便于持续获取数据
            if response.need_ack:
                ack = PushFrame(log_id=package.log_id,
                                payload_type='ack',
                                payload=response.internal_ext.encode('utf-8')
                                ).SerializeToString()
                ws.send(ack, websocket.ABNF.OPCODE_BINARY)

            # 根据消息类别解析消息体
            for msg in response.messages_list:
                method = msg.method
                try:
                    parser = {
                        'WebcastChatMessage': self._parseChatMsg,  # 聊天消息
                        'WebcastGiftMessage': self._parseGiftMsg,  # 礼物消息
                        'WebcastLikeMessage': self._parseLikeMsg,  # 点赞消息
                        'WebcastMemberMessage': self._parseMemberMsg,  # 进入直播间消息
                        'WebcastSocialMessage': self._parseSocialMsg,  # 关注消息
                        'WebcastRoomUserSeqMessage': self._parseRoomUserSeqMsg,  # 直播间统计
                        'WebcastFansclubMessage': self._parseFansclubMsg,  # 粉丝团消息
                        'WebcastControlMessage': self._parseControlMsg,  # 直播间状态消息
                        'WebcastEmojiChatMessage': self._parseEmojiChatMsg,  # 聊天表情包消息
                        'WebcastRoomStatsMessage': self._parseRoomStatsMsg,  # 直播间统计信息
                        'WebcastRoomMessage': self._parseRoomMsg,  # 直播间信息
                        'WebcastRoomRankMessage': self._parseRankMsg,  # 直播间排行榜信息
                    }.get(method)
                    if parser:
                        parser(msg.payload)
                    else:
                        # 如果没有对应的解析方法，打印未处理的消息类型
                        # logging.info(f"【未处理的消息类型】{method}")
                        pass
                except Exception:
                    pass
        except Exception as e:
            logging.error(f"数据处理异常: {e}")

    def _wsOnError(self, ws, error):
        # logging.info("WebSocket error: ", error)
        logging.warning("[!] 重新连接！")
        self._connectWebSocket()

    def _wsOnClose(self, ws, *args):
        logging.info("WebSocket connection closed.")

    def _parseChatMsg(self, payload):
        """聊天消息"""
        message = ChatMessage().parse(payload)
        user_name = message.user.nick_name
        user_id = message.user.id
        content = message.content
        asyncio.run(self.message_handler.handle_chat_message(
            user_id, user_name, content))

    def _parseGiftMsg(self, payload):
        """礼物消息"""
        message = GiftMessage().parse(payload)
        user_name = message.user.nick_name
        user_id = message.user.id
        gift_name = message.gift.name
        gift_cnt = message.combo_count
        asyncio.run(self.message_handler.handle_gift_message(
            user_id, user_name, gift_name, gift_cnt))

    def _parseLikeMsg(self, payload):
        """点赞消息"""
        message = LikeMessage().parse(payload)
        user_name = message.user.nick_name
        user_id = message.user.id
        count = message.count
        asyncio.run(self.message_handler.handle_like_message(
            user_id, user_name, count))

    def _parseMemberMsg(self, payload):
        """进入直播间消息"""
        message = MemberMessage().parse(payload)
        user_name = message.user.nick_name
        user_id = message.user.id
        gender = ["女", "男"][message.user.gender]
        # print(f"【进场msg】 {user_name} {user_id} {gender}")
        asyncio.run(self.message_handler.handle_member_message(
            user_id, user_name))

    def _parseSocialMsg(self, payload):
        """关注消息"""
        message = SocialMessage().parse(payload)
        user_name = message.user.nick_name
        user_id = message.user.id
        asyncio.run(self.message_handler.handle_social_message(
            user_id, user_name))

    def _parseRoomUserSeqMsg(self, payload):
        """直播间统计"""
        message = RoomUserSeqMessage().parse(payload)
        current = message.total
        total = message.total_pv_for_anchor
        asyncio.run(
            self.message_handler.handle_room_user_seq_message(current, total))

    def _parseFansclubMsg(self, payload):
        '''粉丝团消息'''
        message = FansclubMessage().parse(payload)
        content = message.content
        logging.info(f"【粉丝团msg】 {content}")

    def _parseEmojiChatMsg(self, payload):
        '''聊天表情包消息'''
        message = EmojiChatMessage().parse(payload)
        emoji_id = message.emoji_id
        user = message.user
        common = message.common
        default_content = message.default_content
        logging.info(f"【聊天表情包id】 {emoji_id},user：{user},common:{
                     common},default_content:{default_content}")

    def _parseRoomMsg(self, payload):
        message = RoomMessage().parse(payload)
        common = message.common
        room_id = common.room_id
        logging.info(f"【直播间msg】直播间id:{room_id}")

    def _parseRoomStatsMsg(self, payload):
        message = RoomStatsMessage().parse(payload)
        display_long = message.display_long
        logging.info(f"【直播间统计msg】{display_long}")

    def _parseRankMsg(self, payload):
        message = RoomRankMessage().parse(payload)
        ranks_list = message.ranks_list
        # logging.info(f"【直播间排行榜msg】{ranks_list}")

    def _parseControlMsg(self, payload):
        '''直播间状态消息'''
        message = ControlMessage().parse(payload)

        if message.status == 3:
            logging.info("直播间已结束")
            self.stop()
