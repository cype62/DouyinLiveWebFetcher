'''
Author: diudiu62 115522593@qq.com
Date: 2025-01-07 16:24:00
LastEditors: diudiu62 115522593@qq.com
LastEditTime: 2025-01-07 17:20:46
FilePath: /DouyinLiveWebFetcher/component/nocobase_api.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''

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

import aiohttp
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import os

# 加载 .env 文件
load_dotenv()

# 创建一个线程池，最大线程数为 5
executor = ThreadPoolExecutor(max_workers=5)


async def postNocobaseApi(live_id, user_id, user_name, msg):

    async def _post():
        api_url = os.getenv('NOCOBASE_API_URL') + "/api/live_msg:create"
        data = {
            "user_id": user_id,
            "user_name": user_name,
            "msg": msg,
            "type": "douyin",
            "live_id": live_id
        }
        headers = {
            'Authorization': f'Bearer {os.getenv('NOCOBASE_API_KEY')}',
            'Content-Type': 'application/json'
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=data, headers=headers) as response:
                response.raise_for_status()  # 检查请求是否成功

    # 使用 asyncio.run 来运行异步函数
    executor.submit(asyncio.run, _post())
