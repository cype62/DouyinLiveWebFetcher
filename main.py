from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import multiprocessing
from liveMan import DouyinLiveWebFetcher
from component.redis_cli import RedisClient


app = FastAPI()

# 用于存储当前运行的进程和队列
processes = {}
queues = {}


class ActionRequest(BaseModel):
    action: str
    live_id: str


@app.post("/live")
async def handle_live_action(request: ActionRequest):
    action = request.action
    live_id = request.live_id

    if action == "start":
        if live_id in processes:
            # 如果进程已经在运行，先终止它
            process = processes[live_id]
            process.terminate()  # 终止当前进程
            process.join()  # 等待进程结束
            del processes[live_id]  # 移除已结束的进程
            del queues[live_id]  # 移除对应的队列
            print(f"[-] 重启live_id为{live_id}的进程")

        # 创建队列用于进程间通信
        queue = multiprocessing.Queue()
        queues[live_id] = queue

        # 创建子进程来运行 fetcher
        process = multiprocessing.Process(
            target=start_fetcher, args=(live_id, queue), daemon=True)
        process.start()  # 启动子进程
        processes[live_id] = process  # 记录进程
        return {"status": "success", "live_id": live_id}

    elif action == "stop":
        if live_id not in processes:
            raise HTTPException(status_code=404, detail="live_id not found")

        process = processes[live_id]
        process.terminate()  # 终止进程
        process.join()  # 等待进程结束
        del processes[live_id]  # 移除进程
        del queues[live_id]  # 移除对应的队列
        return {"status": "success", "live_id": live_id, "action": "closed"}

    elif action == "get_data":
        if live_id not in queues:
            raise HTTPException(status_code=404, detail="live_id not found")

        queue = queues[live_id]
        if not queue.empty():
            data = queue.get()
            return {"status": "success", "live_id": live_id, "data": data}
        else:
            return {"status": "success", "live_id": live_id, "data": None}

    else:
        raise HTTPException(status_code=400, detail="Invalid action")


def start_fetcher(live_id, queue):
    # 在子进程中初始化 RedisClient
    redis_client = RedisClient()

    fetcher = DouyinLiveWebFetcher(live_id, redis_client)
    # 假设 fetcher.start() 会返回抓取的数据
    data = fetcher.start()
    # 将数据放入队列中
    queue.put(data)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
