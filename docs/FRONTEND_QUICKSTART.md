# 前端 WebSocket 心跳配合 - 快速指南

## 当前错误

```
readyState: 3  // WebSocket 已关闭
```

**原因**：客户端主动断开连接（code: 1001）

---

## ✅ 前端必须做的事

### 1. 通过 HTTP 访问（最重要！）

❌ **不要**直接打开 HTML 文件：
```
file://E:/git/laicai-trading-web/index.html
```

✅ **必须**通过服务器访问：
```
http://localhost:3000
或
http://localhost:5000
```

---

### 2. 响应服务器的 ping

在 WebSocket 的 `onmessage` 处理器中添加：

```typescript
ws.onmessage = (event: MessageEvent) => {
  try {
    const data = JSON.parse(event.data);

    // ⚠️ 必须：响应服务器的 ping
    if (data.type === 'ping') {
      ws.send(JSON.stringify({ type: 'pong' }));
      console.log('[WS] Responded to server ping');
      return;
    }

    // 处理其他消息...
  } catch (error) {
    console.error('[WS] Failed to parse:', error);
  }
};
```

---

## 🔄 可选但推荐做的事

### 3. 客户端主动心跳

```typescript
// 配置
const HEARTBEAT_INTERVAL = 15000;  // 15 秒
const PONG_TIMEOUT = 20000;        // 20 秒

let heartbeatTimer: NodeJS.Timeout | null = null;
let pongTimer: NodeJS.Timeout | null = null;

// 启动心跳
function startHeartbeat() {
  stopHeartbeat();

  heartbeatTimer = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }));
      console.log('[WS] Sent ping to server');

      // 超时检测
      pongTimer = setTimeout(() => {
        console.error('[WS] Pong timeout - reconnecting');
        reconnect();
      }, PONG_TIMEOUT);
    }
  }, HEARTBEAT_INTERVAL);
}

// 停止心跳
function stopHeartbeat() {
  if (heartbeatTimer) clearInterval(heartbeatTimer);
  if (pongTimer) clearTimeout(pongTimer);
  heartbeatTimer = null;
  pongTimer = null;
}

// 连接成功后启动
ws.onopen = () => {
  console.log('[WS] Connected');
  startHeartbeat();
};

// 收到 pong 时清除超时
ws.onmessage = (event: MessageEvent) => {
  const data = JSON.parse(event.data);

  if (data.type === 'pong') {
    if (pongTimer) {
      clearTimeout(pongTimer);
      pongTimer = null;
    }
    console.log('[WS] Received pong');
    return;
  }

  // ... 其他处理
};

// 断开时停止
ws.onclose = () => {
  stopHeartbeat();
};
```

---

## 后端心跳机制说明

### 后端会做什么：

1. **每 15 秒发送 ping**
   ```json
   {"type": "ping"}
   ```

2. **等待 20 秒的 pong 响应**

3. **超时自动关闭连接**（清理僵尸连接）

4. **响应客户端的 ping**
   - 收到 `{"type": "ping"}` → 返回 `{"type": "pong"}`

---

## 检查清单

### 基础要求（必须）

- [ ] 通过 HTTP 服务器访问（不是 file://）
- [ ] 响应服务器的 ping
- [ ] 处理连接错误

### 增强功能（推荐）

- [ ] 客户端主动发送 ping
- [ ] pong 超时检测
- [ ] 自动重连
- [ ] 显示连接状态

---

## 测试方法

### 1. 启动服务

**后端**：
```bash
cd laicai_backend
python start_backend_debug.py
```

**前端**：
```bash
cd laicai-trading-web
pnpm dev
```

### 2. 访问页面

```
http://localhost:3000
```

### 3. 查看控制台

**前端**应该看到：
```
[WS] Connected
[WS] Responded to server ping  ← 这个必须有
```

**后端**应该看到：
```
💓 [WS] Server ping sent
💓 [WS] Server pong received  ← 这个必须有
```

### 4. 测试超时

1. 关闭网络
2. 等待 20 秒
3. 观察断开日志

---

## 最简实现（最小可用）

```typescript
const ws = new WebSocket('ws://localhost:8000/api/stream');

ws.onopen = () => {
  console.log('[WS] Connected');
};

ws.onmessage = (event: MessageEvent) => {
  const data = JSON.parse(event.data);

  // 唯一必须的：响应 ping
  if (data.type === 'ping') {
    ws.send(JSON.stringify({ type: 'pong' }));
    return;
  }

  // 处理其他消息
  console.log('[WS] Received:', data);
};

ws.onerror = (error) => {
  console.error('[WS] Error:', error);
};

ws.onclose = (event) => {
  console.log('[WS] Closed:', event.code);
};
```

---

## 故障排查

### 连接立即断开

**检查**：
1. 是否通过 HTTP 访问？
2. 浏览器控制台有错误吗？
3. 后端日志显示什么？

### 没有收到 ping

**正常**：心跳每 15 秒发送一次，等待即可。

### 连接频繁断开

**检查**：
1. 是否响应了 ping？
2. 网络是否稳定？
3. 查看错误码和原因

---

## 总结

### 后端 ✅

- 每 15 秒发送 ping
- 等待 20 秒 pong
- 超时关闭连接
- 响应客户端 ping

### 前端 ⚠️

**必须**：
- 响应服务器的 ping
- 通过 HTTP 访问

**推荐**：
- 主动发送 ping
- 超时检测
- 自动重连

---

## 文档

详细文档：`laicai_backend/docs/FRONTEND_REQUIREMENTS.md`
