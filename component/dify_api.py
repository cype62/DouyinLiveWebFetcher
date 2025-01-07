
#!/usr/bin/env python
# coding=utf-8
###
# @FilePath     : /DouyinLiveWebFetcher/component/dify_api.py
# @Description  :
# @Author       : diudiu62
# @Version      : 0.0.1
# @LastEditors  : diudiu62
# @LastEditTime : 2025-01-07 14:07:57
# @Copyright (c) 2025 by diudiu62, All Rights Reserved.
###

import logging
import aiohttp
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import os

# 加载 .env 文件
load_dotenv()

# 创建一个线程池，最大线程数为 5
executor = ThreadPoolExecutor(max_workers=5)


async def postDifyApi(user_id, query, redis_client):

    async def _post():
        try:
            # 检查 Redis 中是否存在 user_id 对应的 conversation_id
            try:
                conversation_id = redis_client.get(
                    f"dify_conversation_id:{user_id}")
            except Exception as e:
                conversation_id = None

            api_url = os.getenv('DIFY_API_URL')  # 更新为实际的 API URL
            data = {
                "inputs": {},
                "query": query,
                "response_mode": "blocking",
                "conversation_id": conversation_id,  # 可选，根据实际需求改动
                "user": os.getenv('DIFY_USER'),
            }
            headers = {
                'Authorization': f'Bearer {os.getenv('DIFY_API_KEY')}',
                'Content-Type': 'application/json'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=data, headers=headers) as response:
                    response.raise_for_status()  # 检查请求是否成功

                    response_data = await response.json()
                    # 检查是否包含 conversation_id
                    new_conversation_id = response_data.get('conversation_id')

                    if user_id != None and new_conversation_id and new_conversation_id != conversation_id:
                        try:
                            # 保存会话ID
                            redis_client.set(f"dify_conversation_id:{
                                user_id}", new_conversation_id)
                        except Exception as e:
                            logging.warning('redis保存会话错误:', e)
                    # logging.info("消息已发送至外部 API")
        except aiohttp.ClientError as e:
            logging.error(f"发送消息至外部 API 时出错: {e}")
        except Exception as e:
            logging.error(f"发生未知错误: {e}")

    # 使用 asyncio.run 来运行异步函数
    executor.submit(asyncio.run, _post())
