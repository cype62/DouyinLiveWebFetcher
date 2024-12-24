# 接口文档

## 概述
该 API 提供了启动和关闭抖音直播抓取器的功能。用户可以通过指定 `action` 和 `live_id` 来控制抓取器的运行状态。

## 基本信息

- **服务地址**: `http://localhost:8001`
- **请求格式**: JSON

## 接口

### 1. 启动直播抓取器

- **URL**: `/live`
- **方法**: `POST`
- **请求体**:
  ```json
  {
      "action": "start",
      "live_id": "XXXX"
  }
  ```
- **请求参数**:
  - `action`: 字符串，必须为 `start`。表示要启动新的抓取器进程。
  - `live_id`: 字符串，必须。指定要监听的直播 ID。

- **成功返回**:
  - **状态码**: `200 OK`
  - **响应体**:
    ```json
    {
        "status": "success",
        "live_id": "XXXX"
    }
    ```

- **错误返回**:
  - **状态码**: `400 Bad Request`
    - **响应体**:
      ```json
      {
          "detail": "Live XXXX is already running."
      }
      ```
    - 原因：指定的 `live_id` 已有正在运行的抓取器。
  
  - **状态码**: `400 Bad Request`
    - **响应体**:
      ```json
      {
          "detail": "Invalid action. Must be 'start' or 'stop'."
      }
      ```
    - 原因：`action` 参数必须为 `start` 或 `stop`。

---

### 2. 关闭直播抓取器

- **URL**: `/live`
- **方法**: `POST`
- **请求体**:
  ```json
  {
      "action": "stop",
      "live_id": "XXXX"
  }
  ```
- **请求参数**:
  - `action`: 字符串，必须为 `stop`。表示要关闭对应的抓取器进程。
  - `live_id`: 字符串，必须。指定要关闭监听的直播 ID。

- **成功返回**:
  - **状态码**: `200 OK`
  - **响应体**:
    ```json
    {
        "status": "success",
        "live_id": "XXXX"
    }
    ```

- **错误返回**:
  - **状态码**: `404 Not Found`
    - **响应体**:
      ```json
      {
          "detail": "Live XXXX is not running."
      }
      ```
    - 原因：指定的 `live_id` 没有正在运行的抓取器。

---

## 注意事项
- 访问此 API 之前，请确保 FastAPI 服务已启动。
- 每个 `live_id` 只能有一个活跃的抓取器进程，不能重复启动。