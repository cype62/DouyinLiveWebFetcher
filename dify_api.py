import requests

def post_Dify_api(query):
    # 调用外部 API，并传递消息和用户信息
    api_url = "http://k.gzspark.cn:30099/v1/chat-messages"  # 更新为实际的 API URL
    data = {
        "inputs": {},
        "query": query,
        "response_mode": "streaming",
        "conversation_id": "",  # 可选，根据实际需求改动
        "user": 'douyinLive',
       
    }
    header = {
        'Authorization': f'Bearer app-Wwae49gdkQvQGmQ9DBHjKBwW',  
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(api_url, json=data, headers=header)
        response.raise_for_status()  # 检查请求是否成功
        # print("消息已发送至外部 API")
    except requests.RequestException as e:
        print(f"发送消息至外部 API 时出错: {e}")

