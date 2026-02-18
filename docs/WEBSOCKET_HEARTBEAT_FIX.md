# WebSocket 心跳修复说明

## 问题诊断

从日志发现多个错误：

### 1. 服务器心跳任务冲突

```
❌ [WS] Error waiting for pong: cannot call recv while another coroutine is already waiting for the next message
```

**原因**：
- 主循环在 `while True: data = await websocket.receive_text()` 中等待消息
- 服务器心跳任务也在 `await websocket.receive_text()` 中等待消息
- 两个协程同时等待同一个 WebSocket 的消息，导致冲突

### 2. OKXConnector 方法不存在

```
Failed to get server time: 'OKXConnector' object has no attribute 'get_server_time'
```

**原因**：
- OKXConnector 没有 `get_server_time()` 方法
- 应该使用 `test_connection()` 方法

### 3. EventBus 方法名错误

```
Failed to publish connection event: 'EventBus' object has no attribute 'publish_event'
```

**原因**：
- EventBus 的方法是 `publish(event_type, data)`
- 不是 `publish_event(event)`

---

## 修复方案

### 1. 移除服务器心跳任务

**问题**：服务器心跳任务与主循环冲突

**解决方案**：
- ❌ 移除服务器心跳任务（不主动发送 ping）
- ✅ 只响应客户端的 ping
- ✅ 客户端负责心跳检测和超时重连

**优点**：
- 避免协程冲突
- 简化逻辑
- 降低服务器负载

### 2. 修复 OKXConnector 方法调用

**修改前**：
```python
server_time = await connector.get_server_time()
```

**修改后**：
```python
is_healthy = await connector.test_connection()
logger.info(f"OKX connection test: {'success' if is_healthy else 'failed'}")
```

### 3. 修复 EventBus 方法调用

**修改前**：
```python
await self.event_bus.publish_event({
    "type": "connection",
    "event": "created",
    ...
})
```

**修改后**：
```python
await self.event_bus.publish("connection", {
    "event": "created",
    ...
})
```

---

## 心跳机制说明

### 修复前（双向心跳）

```
前端 (15s) --ping--> 后端 --pong--> 前端
    ^                          |
    | pong                    |
    |                          v
前端 <--pong-- 后端 (15s) --ping--> 前端
    ^                          |
    | ❌ 冲突                  |
    +--------------------------+
```

**问题**：两个协程同时等待消息

### 修复后（客户端心跳）

```
前端 (15s) --ping--> 后端
                     |
                     v
                 响应 pong
                     |
                     v
前端 --pong-- 后端
```

**优点**：
- ✅ 无冲突
- ✅ 简单可靠
- ✅ 客户端控制超时

---

## 前端配合要求

### 必须实现

1. **客户端主动心跳**（每 15 秒）
2. **响应服务器 ping**
3. **pong 超时检测**（20 秒）
4. **超时自动重连**

### 实现示例

```typescript
// 1. 启动心跳
const HEARTBEAT_INTERVAL = 15000;
const PONG_TIMEOUT = 20000;

let heartbeatTimer: NodeJS.Timeout;
let pongTimer: NodeJS.Timeout;

function startHeartbeat() {
  stopHeartbeat();

  heartbeatTimer = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "ping" }));
      
      // 启动 pong 超时检测
      pongTimer = setTimeout(() => {
        console.error("Pong timeout - reconnecting");
        ws.close();
        setTimeout(() => connect(), 2000);
      }, PONG_TIMEOUT);
    }
  }, HEARTBEAT_INTERVAL);
}

// 2. 响应服务器 ping
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "ping") {
    ws.send(JSON.stringify({ type: "pong" }));
    return;
  }

  if (data.type === "pong") {
    // 清除 pong 超时定时器
    if (pongTimer) {
      clearTimeout(pongTimer);
      pongTimer = null;
    }
    return;
  }

  // 处理其他消息...
};
```

---

## 日志输出

### 正常连接

```
✅ [WS] WebSocket client connected to /api/stream
💓 [WS] Server heartbeat started (interval: 15.0s, timeout: 20.0s)  ← 已移除
[WS] Received ping from client
[WS] Sending pong
```

### 修复后

```
✅ [WS] WebSocket client connected to /api/stream
[WS] Published connected event (delayed)
[WS] Received message: {"type":"ping"}
[WS] Received ping, sending pong
```

---

## 验证测试

### 1. 测试心跳

```bash
# 启动后端
cd laicai_backend
python start_backend_debug.py
```

```bash
# 启动前端
cd laicai-trading-web
pnpm dev
```

### 2. 查看日志

**前端控制台**：
```
[WS] Connected
[WS] Sent ping to server
[WS] Received pong - connection is alive
```

**后端日志**：
```
[WS] Received message: {"type":"ping"}
[WS] Parsed message: {'type': 'ping'}
[WS] Received ping, sending pong
```

### 3. 测试超时

1. 关闭网络
2. 等待 20 秒
3. 观察重连日志

---

## 总结

### 修复内容

1. ✅ 移除服务器心跳任务（避免协程冲突）
2. ✅ 修复 OKXConnector 方法调用
3. ✅ 修复 EventBus 方法调用

### 心跳机制

- **客户端心跳**：每 15 秒发送 ping
- **服务器响应**：收到 ping 后返回 pong
- **超时检测**：客户端检测 20 秒超时
- **自动重连**：超时后自动重连

### 优点

- 无协程冲突
- 简单可靠
- 客户端控制
- 降低服务器负载

### 前端配合

- 必须实现客户端心跳
- 必须响应服务器 ping
- 必须实现超时检测
- 必须实现自动重连

详细的前端配合要求请参考：
- `laicai_backend/docs/FRONTEND_QUICKSTART.md`
- `laicai_backend/docs/FRONTEND_REQUIREMENTS.md`
