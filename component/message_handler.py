#!/usr/bin/env python
# coding=utf-8
###
# @FilePath     : /DouyinLiveWebFetcher/component/message_handler.py
# @Description  :
# @Author       : diudiu62
# @Version      : 0.0.1
# @LastEditors  : diudiu62
# @LastEditTime : 2025-01-07 13:08:18
# @Copyright (c) 2025 by diudiu62, All Rights Reserved.
###

from collections import deque
import logging
import random

from component.dify_api import postDifyApi
from component.nocobase_api import postNocobaseApi


class MessageHandler:
    def __init__(self, redis_client):
        self.recent_like_users = set()  # 存储最近点赞用户的ID
        self.recent_like_queue = deque(maxlen=10)  # 维护最近10个点赞用户的队列
        self.redis_client = redis_client  # 传入的 Redis 客户端

    async def handle_chat_message(self, live_id, user_id, user_name, content):
        """处理聊天消息"""
        logging.info(f"【聊天msg】[{user_id}]{user_name}: {content}")
        await self._post_to_dify(user_id, f"action:聊天msg,user_name:{user_name},msg:留言：{content}")
        await self._post_to_nocobase(live_id, user_id, user_name, content)

    async def handle_gift_message(self, user_id, user_name, gift_name, gift_cnt):
        """处理礼物消息"""
        logging.info(f"【礼物msg】{user_name} 送出了 {gift_name}x{gift_cnt}")
        await self._post_to_dify(user_id, f"action:礼物msg,user_name:{user_name},msg:送出了：{gift_name}x{gift_cnt}")

    async def handle_like_message(self, user_id, user_name, count):
        """处理点赞消息"""
        logging.info(f"【点赞msg】{user_name} 点了{count}个赞")
        if user_id not in self.recent_like_users:
            self.recent_like_users.add(user_id)
            self.recent_like_queue.append(user_id)
            await self._post_to_dify(user_id, f"action:点赞msg,user_name:{user_name},msg:点了{count}个赞")
        if len(self.recent_like_queue) >= 10:
            oldest_user_id = self.recent_like_queue.popleft()
            self.recent_like_users.remove(oldest_user_id)

    async def handle_member_message(self, user_id, user_name):
        """处理进入直播间消息"""
        logging.info(f"【进场msg】{user_name} 进入了直播间")
        await self._post_to_dify(user_id, f"action:进入直播间msg,user_name:{user_name},msg:进了直播间")

    async def handle_social_message(self, user_id, user_name):
        """处理关注消息"""
        logging.info(f"【关注msg】[{user_id}]{user_name} 关注了主播")
        await self._post_to_dify(user_id, f"action:关注msg,user_name:{user_name},msg:关注了主播")

    async def handle_room_user_seq_message(self, current, total):
        """处理直播间统计消息"""
        logging.info(f"【统计msg】当前观看人数: {current}, 累计观看人数: {total}")
        if current > 5:
            call_probability = 0.05  # 例如，5% 的概率调用 post_Dify_api
            if random.random() < call_probability:
                await self._post_to_dify(None, f"action:统计msg,msg:当前直播间有{current}人")

    async def _post_to_dify(self, user_id, message):
        """调用 post_Dify_api"""
        await postDifyApi(user_id, message, self.redis_client)

    async def _post_to_nocobase(self, live_id, user_id, user_name, content):
        """调用 post_Dify_api"""
        await postNocobaseApi(live_id, user_id, user_name, content)
