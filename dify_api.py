import logging
import aiohttp
import asyncio
from concurrent.futures import ThreadPoolExecutor
from redis_cli import RedisClient

# 创建一个线程池，最大线程数为 5
executor = ThreadPoolExecutor(max_workers=5)

# 初始化 Redis 客户端
redis_client = RedisClient()

async def post_Dify_api(user_id, query):
    async def _post():
        try:
            # 检查 Redis 中是否存在 user_id 对应的 conversation_id
            conversation_id = redis_client.get(f"dify_conversation_id:{user_id}")
            
            api_url = "http://10.10.6.31:30099/v1/chat-messages"  # 更新为实际的 API URL
            data = {
                "inputs": {},
                "query": query,
                "response_mode": "blocking",
                "conversation_id": conversation_id,  # 可选，根据实际需求改动
                "user": 'douyinLive',
            }
            headers = {
                'Authorization': f'Bearer app-Wwae49gdkQvQGmQ9DBHjKBwW',  
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=data, headers=headers) as response:
                    response.raise_for_status()  # 检查请求是否成功
                    
                    response_data = await response.json()
                    # 检查是否包含 conversation_id
                    new_conversation_id = response_data.get('conversation_id')
                    
                    if user_id != None and new_conversation_id and new_conversation_id != conversation_id:
                        # 保存会话ID
                        redis_client.set(f"dify_conversation_id:{user_id}", new_conversation_id)                    
                    logging.info("消息已发送至外部 API")
        except aiohttp.ClientError as e:
            logging.error(f"发送消息至外部 API 时出错: {e}")
        except Exception as e:
            logging.error(f"发生未知错误: {e}")
        finally:
            # 关闭 Redis 连接
            redis_client.close()
    
    # 使用 asyncio.run 来运行异步函数
    executor.submit(asyncio.run, _post())