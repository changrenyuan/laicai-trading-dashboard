# 前端开发交接文档

## 项目概述

这是一个事件驱动的量化交易终端后端系统，采用 **Command/Stream** 架构模式。

### 核心设计原则

1. **事件驱动**：所有状态变更通过 EventBus 推送
2. **统一命令接口**：前端所有操作通过 `/api/command` 发送
3. **WebSocket 实时推送**：前端通过 WebSocket 接收所有事件
4. **前后端分离**：前端独立开发，不依赖后端代码

---

## API 端点总览

### 基础信息

- **服务端口**: `5000`
- **基础地址**: `http://localhost:5000`
- **WebSocket 地址**: `ws://localhost:5000/ws`
- **协议**: HTTP (REST API) + WebSocket (实时事件)

---

## 1. 统一命令接口

### POST /api/command

前端所有操作通过此接口发送。

#### 请求格式

```json
{
  "cmd": "start_strategy",
  "params": {
    "strategy_id": "market_maker",
    "instance_id": "strat_001"
  }
}
```

#### 响应格式

**成功**:
```json
{
  "success": true,
  "cmd": "start_strategy",
  "timestamp": "2024-12-16T12:00:00.000Z",
  "status": "started",
  "strategy_id": "market_maker"
}
```

**失败**:
```json
{
  "success": false,
  "cmd": "start_strategy",
  "error": "Strategy not found",
  "timestamp": "2024-12-16T12:00:00.000Z"
}
```

---

### 支持的命令类型

#### 1. 启动策略

**命令**: `start_strategy`

**参数**:
- `strategy_id`: 策略 ID（如 `market_maker`）
- `instance_id`: 实例 ID（可选，多策略模式下使用）

**示例**:
```json
{
  "cmd": "start_strategy",
  "params": {
    "strategy_id": "market_maker"
  }
}
```

#### 2. 停止策略

**命令**: `stop_strategy`

**参数**:
- `strategy_id`: 策略 ID
- `instance_id`: 实例 ID（可选）

**示例**:
```json
{
  "cmd": "stop_strategy",
  "params": {
    "strategy_id": "market_maker"
  }
}
```

#### 3. 下单

**命令**: `place_order`

**参数**:
- `symbol`: 交易对（必填）
- `side`: 方向（必填，`buy` 或 `sell`）
- `size`: 数量（必填）
- `type`: 订单类型（可选，默认 `limit`，支持 `limit`/`market`）
- `price`: 价格（限价单必填）

**示例**:
```json
{
  "cmd": "place_order",
  "params": {
    "symbol": "ETH-USDT",
    "side": "buy",
    "size": 0.01,
    "type": "limit",
    "price": 3800.0
  }
}
```

#### 4. 取消订单

**命令**: `cancel_order`

**参数**:
- `order_id`: 订单 ID（必填）
- `symbol`: 交易对（可选）

**示例**:
```json
{
  "cmd": "cancel_order",
  "params": {
    "order_id": "order_123",
    "symbol": "ETH-USDT"
  }
}
```

#### 5. 取消所有订单

**命令**: `cancel_all_orders`

**参数**:
- `symbol`: 交易对（可选，不填则取消所有）

**示例**:
```json
{
  "cmd": "cancel_all_orders",
  "params": {}
}
```

#### 6. 紧急停止

**命令**: `kill_switch`

**参数**: 无

**示例**:
```json
{
  "cmd": "kill_switch",
  "params": {}
}
```

---

## 2. 状态查询接口

### GET /api/state

获取当前完整状态快照。

#### 响应格式

```json
{
  "strategies": [
    {
      "instance_id": "strat_001",
      "strategy_name": "market_maker",
      "instance_name": "BTC-USDT MM",
      "is_running": true,
      "created_at": "2024-12-16T10:00:00.000Z",
      "last_active": "2024-12-16T12:00:00.000Z"
    }
  ],
  "orders": [
    {
      "orderId": "order_123",
      "symbol": "ETH-USDT",
      "side": "buy",
      "status": "open",
      "filled": 0.0,
      "price": 3800.0
    }
  ],
  "positions": [
    {
      "symbol": "ETH-USDT",
      "size": 0.02,
      "pnl": 100.0,
      "side": "long"
    }
  ],
  "balances": [
    {
      "currency": "USDT",
      "total": 10000.0,
      "available": 9500.0
    },
    {
      "currency": "ETH",
      "total": 0.5,
      "available": 0.48
    }
  ],
  "timestamp": "2024-12-16T12:00:00.000Z"
}
```

**使用场景**:
- 前端初始化时获取当前状态
- WebSocket 重连后恢复状态

---

## 3. WebSocket 接口

### 连接地址

```
ws://localhost:5000/ws
```

### 连接流程

1. 前端连接 WebSocket
2. 后端自动发送当前状态快照 (`type: "snapshot"`)
3. 后端持续推送实时事件

### 事件格式

所有事件都遵循统一格式：

```typescript
interface EngineEvent {
  type: "price" | "order_update" | "position" | "strategy" | "log" | "snapshot" | "error";
  timestamp: string;  // ISO 8601 格式
  [key: string]: any; // 其他字段根据事件类型不同
}
```

---

### 支持的事件类型

#### 1. 价格更新 (type: "price")

```json
{
  "type": "price",
  "symbol": "ETH-USDT",
  "price": 3821.3,
  "bid": 3820.0,
  "ask": 3822.0,
  "timestamp": "2024-12-16T12:00:00.000Z"
}
```

#### 2. 订单更新 (type: "order_update")

```json
{
  "type": "order_update",
  "orderId": "order_123",
  "status": "filled",
  "filled": 0.01,
  "symbol": "ETH-USDT",
  "price": 3800.0,
  "timestamp": "2024-12-16T12:00:00.000Z"
}
```

**status 字段值**:
- `pending`: 待处理
- `open`: 开放
- `filled`: 成交
- `canceled`: 已取消
- `failed`: 失败

#### 3. 仓位更新 (type: "position")

```json
{
  "type": "position",
  "symbol": "ETH-USDT",
  "size": 0.02,
  "pnl": 100.0,
  "side": "long",
  "timestamp": "2024-12-16T12:00:00.000Z"
}
```

#### 4. 策略状态 (type: "strategy")

```json
{
  "type": "strategy",
  "id": "market_maker",
  "status": "running",
  "config": {
    "trading_pair": "ETH-USDT",
    "order_amount": 0.01
  },
  "timestamp": "2024-12-16T12:00:00.000Z"
}
```

**status 字段值**:
- `running`: 运行中
- `stopped`: 已停止
- `error`: 错误

#### 5. 日志消息 (type: "log")

```json
{
  "type": "log",
  "level": "INFO",
  "msg": "Order filled: order_123",
  "logger": "strategy",
  "timestamp": "2024-12-16T12:00:00.000Z"
}
```

**level 字段值**:
- `INFO`: 信息
- `WARNING`: 警告
- `ERROR`: 错误
- `DEBUG`: 调试

#### 6. 错误事件 (type: "error")

```json
{
  "type": "error",
  "error_type": "order_failed",
  "message": "Insufficient balance",
  "details": {
    "order_id": "order_123",
    "required": 0.01,
    "available": 0.005
  },
  "timestamp": "2024-12-16T12:00:00.000Z"
}
```

#### 7. 状态快照 (type: "snapshot")

**WebSocket 连接后自动发送**，包含当前完整状态。

```json
{
  "type": "snapshot",
  "strategies": [...],
  "orders": [...],
  "positions": [...],
  "balances": [...],
  "timestamp": "2024-12-16T12:00:00.000Z"
}
```

---

## 4. 健康检查接口

### GET /api/health

检查服务健康状态。

#### 响应格式

```json
{
  "status": "ok",
  "timestamp": "2024-12-16T12:00:00.000Z",
  "active_clients": 3
}
```

---

## 5. API 根路径

### GET /

获取 API 基本信息。

#### 响应格式

```json
{
  "service": "Hummingbot Lite Trading API",
  "version": "2.0.0",
  "architecture": "Event-Driven",
  "endpoints": {
    "websocket": "/ws",
    "command": "/api/command",
    "state": "/api/state",
    "health": "/api/health"
  },
  "supported_commands": [
    "start_strategy",
    "stop_strategy",
    "place_order",
    "cancel_order",
    "cancel_all_orders",
    "kill_switch",
    "get_state"
  ]
}
```

---

## 前端集成指南

### 1. 初始化流程

```typescript
// 1. 连接 WebSocket
const ws = new WebSocket('ws://localhost:5000/ws');

// 2. 监听事件
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  // 根据事件类型更新状态
  switch (data.type) {
    case 'snapshot':
      // 初始化状态
      engineStore.setState(data);
      break;
    case 'order_update':
      engineStore.updateOrder(data);
      break;
    case 'position':
      engineStore.updatePosition(data);
      break;
    case 'strategy':
      engineStore.updateStrategy(data);
      break;
    case 'price':
      engineStore.updatePrice(data);
      break;
    case 'log':
      engineStore.addLog(data);
      break;
  }
};
```

### 2. 发送命令

```typescript
async function sendCommand(cmd: string, params: any) {
  const response = await fetch('http://localhost:5000/api/command', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ cmd, params }),
  });

  const result = await response.json();

  if (!result.success) {
    console.error('Command failed:', result.error);
  }

  return result;
}

// 示例：启动策略
await sendCommand('start_strategy', { strategy_id: 'market_maker' });

// 示例：下单
await sendCommand('place_order', {
  symbol: 'ETH-USDT',
  side: 'buy',
  size: 0.01,
  type: 'limit',
  price: 3800.0
});
```

### 3. 获取初始状态

```typescript
async function getInitialState() {
  const response = await fetch('http://localhost:5000/api/state');
  const state = await response.json();
  engineStore.setState(state);
}
```

### 4. WebSocket 重连处理

```typescript
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

function connectWebSocket() {
  const ws = new WebSocket('ws://localhost:5000/ws');

  ws.onopen = () => {
    console.log('WebSocket connected');
    reconnectAttempts = 0;
  };

  ws.onclose = () => {
    console.log('WebSocket disconnected');
    reconnectAttempts++;

    if (reconnectAttempts <= maxReconnectAttempts) {
      setTimeout(connectWebSocket, 3000);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  ws.onmessage = (event) => {
    // 处理事件
  };
}

connectWebSocket();
```

---

## TypeScript 类型定义

```typescript
// 事件类型
type EngineEventType =
  | "price"
  | "order_update"
  | "position"
  | "strategy"
  | "log"
  | "snapshot"
  | "error";

// 基础事件
interface BaseEvent {
  type: EngineEventType;
  timestamp: string;
}

// 价格事件
interface PriceEvent extends BaseEvent {
  type: "price";
  symbol: string;
  price: number;
  bid?: number;
  ask?: number;
}

// 订单事件
interface OrderEvent extends BaseEvent {
  type: "order_update";
  orderId: string;
  status: "pending" | "open" | "filled" | "canceled" | "failed";
  filled: number;
  symbol?: string;
  price?: number;
}

// 仓位事件
interface PositionEvent extends BaseEvent {
  type: "position";
  symbol: string;
  size: number;
  pnl: number;
  side: "long" | "short";
}

// 策略事件
interface StrategyEvent extends BaseEvent {
  type: "strategy";
  id: string;
  status: "running" | "stopped" | "error";
  config?: Record<string, any>;
}

// 日志事件
interface LogEvent extends BaseEvent {
  type: "log";
  level: "INFO" | "WARNING" | "ERROR" | "DEBUG";
  msg: string;
  logger?: string;
}

// 错误事件
interface ErrorEvent extends BaseEvent {
  type: "error";
  error_type: string;
  message: string;
  details?: Record<string, any>;
}

// 快照事件
interface SnapshotEvent extends BaseEvent {
  type: "snapshot";
  strategies: any[];
  orders: any[];
  positions: any[];
  balances: any[];
}

// 统一事件类型
type EngineEvent =
  | PriceEvent
  | OrderEvent
  | PositionEvent
  | StrategyEvent
  | LogEvent
  | ErrorEvent
  | SnapshotEvent;

// 命令请求
interface CommandRequest {
  cmd: string;
  params?: Record<string, any>;
}

// 命令响应
interface CommandResponse {
  success: boolean;
  cmd: string;
  timestamp: string;
  [key: string]: any;
}

// 状态快照
interface StateSnapshot {
  strategies: any[];
  orders: any[];
  positions: any[];
  balances: any[];
  timestamp: string;
}
```

---

## 注意事项

1. **事件格式统一**：所有 WebSocket 事件都遵循统一的格式，前端 engineStore 可以直接消费
2. **避免轮询**：前端不应轮询 `/api/state`，只在初始化或重连时调用
3. **命令统一入口**：所有操作都通过 `/api/command` 发送，不使用其他 REST API
4. **WebSocket 心跳**：建议前端定期发送 `{"type": "ping"}` 保持连接活跃
5. **错误处理**：所有命令错误都会在响应中返回，前端应检查 `success` 字段
6. **状态持久化**：后端会持久化状态到 JSON 文件，重启后可恢复

---

## 架构说明

### 后端架构

```
Frontend
    |
    | POST /api/command
    v
Command Handler
    |
    | 发布事件
    v
EventBus
    |
    | 推送事件
    +----> WebSocket Manager ----> WebSocket Clients
    |
    +----> 状态持久化 (JSON 文件)
```

### 数据流

1. **命令流**: Frontend → `/api/command` → Command Handler → 业务逻辑 → EventBus
2. **事件流**: EventBus → WebSocket Manager → WebSocket Clients
3. **状态流**: 业务逻辑 → 状态持久化 → `/api/state`

---

## 常见问题

### Q: 为什么所有操作都通过 `/api/command`？

A: 统一命令接口的好处：
- 前端只需一个 API 端点
- 更好的权限控制
- 便于审计和日志
- 支持扩展新命令

### Q: WebSocket 断线后如何恢复？

A:
1. 自动重连机制
2. 重连后自动接收 snapshot
3. 前端应用 snapshot 恢复状态

### Q: 如何区分不同的事件？

A: 通过 `type` 字段：
- `price`: 价格更新
- `order_update`: 订单状态变化
- `position`: 仓位变化
- `strategy`: 策略状态
- `log`: 日志消息
- `snapshot`: 状态快照
- `error`: 错误事件

### Q: 如何处理命令执行失败？

A:
1. 检查响应中的 `success` 字段
2. `success === false` 时查看 `error` 字段
3. 显示错误消息给用户

---

## 技术栈

- **后端**: Python 3.12+, FastAPI, asyncio
- **通信协议**: HTTP (REST API) + WebSocket
- **数据格式**: JSON
- **架构模式**: Event-Driven, Command/Stream

---

## 联系方式

如有问题，请联系后端开发团队。
