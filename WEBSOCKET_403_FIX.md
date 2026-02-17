# WebSocket 403 Forbidden 错误修复

## 问题描述

客户端尝试连接 WebSocket 端点 `/api/stream` 时，服务端返回 `403 Forbidden` 错误。

```
INFO:     127.0.0.1:51540 - "WebSocket /api/stream" 403
INFO:     connection rejected (403 Forbidden)
INFO:     connection closed
```

## 根本原因

服务端配置的 WebSocket 端点是 `/ws` 和 `/ws/logs`，**没有** `/api/stream` 端点。

当客户端尝试连接不存在的 WebSocket 端点时，FastAPI 返回 `403 Forbidden` 错误。

## 解决方案

在 `src/ui/web_multi_strategy.py` 中添加 `/api/stream` WebSocket 端点，使其与 `/ws` 端点行为一致。

### 修改内容

```python
@self.app.websocket("/api/stream")
async def api_stream_endpoint(websocket: WebSocket):
    """API Stream WebSocket 端点 - 用于事件广播（兼容客户端）"""
    await websocket.accept()
    self.websocket_clients.append(websocket)
    logger.info("WebSocket client connected to /api/stream")

    try:
        while True:
            data = await websocket.receive_text()
            # 可以处理客户端发送的消息
            logger.info(f"Received WebSocket message: {data}")

    except WebSocketDisconnect:
        if websocket in self.websocket_clients:
            self.websocket_clients.remove(websocket)
        logger.info("WebSocket client disconnected from /api/stream")
```

## 可用的 WebSocket 端点

| 端点 | 说明 | 用途 |
|------|------|------|
| `/ws` | 通用 WebSocket | 用于事件广播 |
| `/api/stream` | API Stream | 用于事件广播（兼容客户端） |
| `/ws/logs` | 日志 WebSocket | 用于实时日志推送 |

## 客户端连接示例

### JavaScript/TypeScript

```javascript
// 连接到 /api/stream
const ws = new WebSocket('ws://localhost:8000/api/stream');

ws.onopen = () => {
  console.log('WebSocket connected');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket closed');
};
```

### Python

```python
import asyncio
import websockets

async def connect():
    uri = "ws://localhost:8000/api/stream"
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")

        # 接收消息
        while True:
            message = await websocket.recv()
            print(f"Received: {message}")

asyncio.run(connect())
```

### wscat (命令行工具)

```bash
wscat -c ws://localhost:8000/api/stream
```

## 验证服务是否正常

### 1. 检查服务是否运行

```bash
curl http://localhost:8000/api/health
```

### 2. 查看 API 文档

浏览器访问：`http://localhost:8000/docs`

### 3. 测试 WebSocket 连接

使用 wscat 测试：

```bash
wscat -c ws://localhost:8000/api/stream
```

如果连接成功，你会看到：
```
Connected (press CTRL+C to quit)
```

## 相关配置

### CORS 配置

服务端已经配置了 CORS 中间件，允许跨域访问：

```python
self.app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（开发环境）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有请求头
)
```

### 端口配置

- 服务端口：`8000`
- 主机：`0.0.0.0`（允许外部访问）

## 常见问题

### Q1: 仍然返回 403 Forbidden？

可能原因：
1. 服务未重启 - 修改代码后需要重启服务
2. 端口错误 - 检查连接的端口是否为 8000
3. 防火墙限制 - 检查防火墙是否阻止连接

### Q2: 连接后立即断开？

可能原因：
1. 客户端发送了不符合预期的消息格式
2. 服务端内部错误 - 检查服务日志

### Q3: 没有收到任何消息？

这是正常的。WebSocket 连接后需要等待服务端推送事件。你可以：
1. 触发一些操作（如启动策略、下单等）
2. 检查服务端日志是否有事件发布

## 下一步

1. 重启服务
2. 测试 WebSocket 连接
3. 确认可以正常接收消息
4. 集成到前端代码
