import requests
import redis
from concurrent.futures import ThreadPoolExecutor

# 创建一个线程池，最大线程数为 5
executor = ThreadPoolExecutor(max_workers=5)

# 连接到 Redis
redis_client = redis.Redis(host='10.10.6.31', port=30379, db=12, password='interlib')

def post_Dify_api(user_id, query):
    def _post():
        # 检查 Redis 中是否存在 user_id 对应的 conversation_id
        conversation_id = redis_client.get(f"dify_conversation_id:{user_id}")
        
        api_url = "http://k.gzspark.cn:30099/v1/chat-messages"  # 更新为实际的 API URL
        data = {
            "inputs": {},
            "query": query,
            "response_mode": "blocking",
            "conversation_id": conversation_id,  # 可选，根据实际需求改动
            "user": 'douyinLive',
        }
        header = {
            'Authorization': f'Bearer app-Wwae49gdkQvQGmQ9DBHjKBwW',  
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(api_url, json=data, headers=header)
            response.raise_for_status()  # 检查请求是否成功
            

            response_data = response.json()
            # 检查是否包含 conversation_id
            conversation_id = response_data.get('conversation_id')
            
            if conversation_id:
                redis_client.set(f"dify_conversation_id:{user_id}", conversation_id)

                print(f"已保存 user_id: {user_id}, conversation_id: {conversation_id} 到 Redis")


            
            print("消息已发送至外部 API")
        except requests.RequestException as e:
            print(f"发送消息至外部 API 时出错: {e}")
    
    # 将任务提交到线程池
    executor.submit(_post)