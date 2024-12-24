# 使用官方 Python 作为基础镜像
FROM python:3.11-slim

RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple 
RUN pip config set install.trusted-host mirrors.aliyun.com

# 设置工作目录
WORKDIR /app

# 复制当前目录下的所有文件到容器中的 /app 目录
COPY . /app

# 安装 Python 依赖
RUN pip install -r requirements.txt

# 暴露应用运行的端口
EXPOSE 8001

# 设置环境变量，告诉 uvicorn 应用实例的位置
ENV UVICORN_CMD="uvicorn main:app --host 0.0.0.0 --port 8001 --reload"

# 默认运行 uvicorn 来启动 FastAPI 应用
CMD ["sh", "-c", "$UVICORN_CMD"]