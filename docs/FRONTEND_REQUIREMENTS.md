# WebSocket 双向心跳机制 - 前端配合要求

## 当前问题诊断

从错误信息看：
```javascript
readyState: 3  // WebSocket 已关闭
```

后端日志显示：
```
INFO:     connection open
DEBUG:    Event sent to client: connected
INFO:     WebSocket client disconnected (code: 1001, reason: )
INFO:     connection closed
```

**状态码 1001**：客户端主动断开连接

---

## 后端已实现的功能

### 1. 服务器心跳机制

后端已实现服务器端心跳，会：

✅ 每 15 秒发送 ping 给前端
✅ 等待前端响应 pong
✅ 20 秒超时检测
✅ 超时自动关闭连接

### 2. 响应客户端 ping

后端会响应客户端发送的 ping：

✅ 收到 `{"type": "ping"}` → 返回 `{"type": "pong"}`

---

## 前端需要实现的功能

### ✅ 必须实现

#### 1. 响应服务器 ping

当收到服务器的 ping 时，必须发送 pong：

```typescript
// 处理 WebSocket 消息
ws.onmessage = (event: MessageEvent) => {
  try {
    const data = JSON.parse(event.data);

    // ⚠️ 必须响应服务器的 ping
    if (data.type === "ping") {
      console.log("[WS] Received ping from server, sending pong");
      ws.send(JSON.stringify({ type: "pong" }));
      return;
    }

    // 处理其他消息...
  } catch (error) {
    console.error("[WS] Failed to parse message:", error);
  }
};
```

#### 2. 客户端心跳（可选但推荐）

前端也可以主动发送 ping 来检测连接：

```typescript
// 配置
const HEARTBEAT_INTERVAL = 15000;  // 15 秒
const PONG_TIMEOUT = 20000;        // 20 秒超时

let heartbeatTimer: NodeJS.Timeout | null = null;
let pongTimer: NodeJS.Timeout | null = null;

function startHeartbeat() {
  stopHeartbeat();

  heartbeatTimer = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "ping" }));
      console.log("[WS] Sent ping to server");

      // 启动 pong 超时检测
      pongTimer = setTimeout(() => {
        console.error("[WS] Pong timeout - connection may be dead");
        ws.close(1000, "Heartbeat timeout");
      }, PONG_TIMEOUT);
    }
  }, HEARTBEAT_INTERVAL);
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
  if (pongTimer) {
    clearTimeout(pongTimer);
    pongTimer = null;
  }
}

// 连接成功后启动心跳
ws.onopen = () => {
  console.log("[WS] Connected");
  startHeartbeat();
};

// 收到 pong 时清除超时定时器
ws.onmessage = (event: MessageEvent) => {
  const data = JSON.parse(event.data);

  // 清除 pong 超时定时器
  if (data.type === "pong") {
    if (pongTimer) {
      clearTimeout(pongTimer);
      pongTimer = null;
    }
    console.log("[WS] Received pong - connection is alive");
    return;
  }

  // 处理其他消息...
};
```

---

## 当前错误排查

### 错误：readyState: 3

readyState: 3 表示 WebSocket 已关闭。

**可能原因**：

1. **通过 file:// 协议访问页面**
   ```
   file://E:/git/laicai-trading-web/.next/...
   ```
   ❌ 浏览器安全策略阻止 WebSocket

   ✅ 正确方式：通过 HTTP 服务器访问
   ```
   http://localhost:3000
   或
   http://localhost:5000
   ```

2. **前端页面加载问题**
   - 检查是否有 JavaScript 错误
   - 检查是否正确初始化 WebSocket

3. **CORS 或其他安全限制**
   - 后端已配置 `allow_origins=["*"]`
   - 检查浏览器控制台是否有 CORS 错误

---

## 前端实现检查清单

### ✅ 基础要求

- [ ] 通过 HTTP 服务器访问页面（不是 file://）
- [ ] 正确初始化 WebSocket 连接
- [ ] 响应服务器的 ping 消息
- [ ] 处理连接错误和重连
- [ ] 显示连接状态给用户

### 🔄 可选增强

- [ ] 客户端主动发送 ping
- [ ] pong 超时检测
- [ ] 自动重连机制
- [ ] 心跳日志输出

---

## 最简实现示例

### 最小可用版本

```typescript
// 1. 创建 WebSocket
const ws = new WebSocket('ws://localhost:8000/api/stream');

// 2. 连接成功
ws.onopen = () => {
  console.log('[WS] Connected');
};

// 3. 处理消息（必须响应 ping）
ws.onmessage = (event: MessageEvent) => {
  try {
    const data = JSON.parse(event.data);

    // ⚠️ 必须：响应服务器的 ping
    if (data.type === 'ping') {
      ws.send(JSON.stringify({ type: 'pong' }));
      return;
    }

    // 处理其他消息
    console.log('[WS] Received:', data);
  } catch (error) {
    console.error('[WS] Failed to parse:', error);
  }
};

// 4. 处理错误
ws.onerror = (error) => {
  console.error('[WS] Error:', error);
};

// 5. 处理关闭
ws.onclose = (event) => {
  console.log('[WS] Closed:', event.code, event.reason);
};
```

---

## 测试验证

### 1. 查看后端日志

启动后端后，观察日志：

```
✅ 正常连接：
💓 [WS] Server heartbeat started
💓 [WS] Server ping sent
💓 [WS] Server pong received

❌ 无响应：
💓 [WS] Server ping sent
❌ [WS] Server pong timeout - closing connection
```

### 2. 查看前端控制台

```
✅ 正常响应：
[WS] Received ping from server, sending pong

❌ 未响应：
无日志输出
```

### 3. 使用测试页面

访问测试页面：
```
http://localhost:3000/ws-test.html
```

观察连接状态和消息收发。

---

## 常见问题

### Q1: 为什么连接立即断开？

**A**: 检查：
1. 是否通过 HTTP 服务器访问（不是 file://）
2. 前端是否有 JavaScript 错误
3. 浏览器控制台是否有 CORS 错误

### Q2: 必须实现客户端心跳吗？

**A**: 不是必须的。
- 最小要求：只需响应服务器的 ping
- 推荐：也实现客户端心跳，双向检测更可靠

### Q3: 心跳间隔是多少？

**A**:
- 服务器心跳：15 秒
- 推荐客户端心跳：15 秒
- pong 超时：20 秒

### Q4: 如何确认心跳工作正常？

**A**:
1. 查看前端日志：`[WS] Received ping from server, sending pong`
2. 查看后端日志：`💓 [WS] Server pong received`
3. 连接保持稳定，不会频繁断开

---

## 消息格式

### Ping（服务器 → 客户端）

```json
{
  "type": "ping"
}
```

### Pong（客户端 → 服务器）

```json
{
  "type": "pong"
}
```

---

## 推荐实现方式

### 使用现有 WebSocket 客户端库

如果已有 WebSocket 客户端代码，只需添加 ping 响应：

```typescript
// 在 handleMessage 函数中添加
private handleMessage(event: EngineEvent): void {
  // 响应服务器 ping
  if (event.type === "ping") {
    this.ws?.send(JSON.stringify({ type: "pong" }));
    console.log("[WS] Sent pong to server");
    return;
  }

  // 处理其他消息
  // ...
}
```

---

## 总结

### 后端已实现 ✅

- 服务器心跳（15 秒）
- 响应客户端 ping
- pong 超时检测（20 秒）
- 自动清理僵尸连接

### 前端必须实现 ⚠️

- 响应服务器的 ping（返回 pong）
- 通过 HTTP 服务器访问页面

### 前端推荐实现 💡

- 客户端主动心跳
- pong 超时检测
- 自动重连机制
- 详细日志输出

---

## 参考资料

- [WebSocket RFC 6455](https://tools.ietf.org/html/rfc6455)
- [FastAPI WebSocket 文档](https://fastapi.tiangolo.com/advanced/websockets/)
