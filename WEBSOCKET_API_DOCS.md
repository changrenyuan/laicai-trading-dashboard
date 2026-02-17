# WebSocket API 完整文档

本文档详细说明了 Hummingbot Lite 后端的 WebSocket API，包括事件推送和命令处理。

---

## 🔗 连接方式

### 端点列表

| 端点 | 说明 |
|------|------|
| `/ws` | 通用 WebSocket 端点 |
| `/api/stream` | API Stream 端点（推荐） |
| `/ws/logs` | 日志专用端点 |

### 连接示例

#### JavaScript/TypeScript

```typescript
const ws = new WebSocket('ws://localhost:8000/api/stream');

ws.onopen = () => {
  console.log('✅ WebSocket connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('📥 Received:', data);
  
  // 根据事件类型处理
  switch (data.type) {
    case 'price':
      handlePriceUpdate(data);
      break;
    case 'order_update':
      handleOrderUpdate(data);
      break;
    // ... 其他事件类型
  }
};

ws.onerror = (error) => {
  console.error('❌ WebSocket error:', error);
};

ws.onclose = () => {
  console.log('🔌 WebSocket closed');
};
```

#### Python

```python
import asyncio
import websockets
import json

async def connect():
    uri = "ws://localhost:8000/api/stream"
    async with websockets.connect(uri) as ws:
        print("✅ Connected")

        while True:
            message = await ws.recv()
            data = json.loads(message)
            print(f"📥 Received: {data}")

asyncio.run(connect())
```

#### wscat (命令行工具)

```bash
wscat -c ws://localhost:8000/api/stream
```

---

## 📤 事件推送

后端会主动推送以下 10 种事件类型：

### 1. 引擎连接状态

#### connected - 引擎已连接

```json
{
  "type": "connected",
  "timestamp": "2024-02-17T13:46:40.000Z"
}
```

#### disconnected - 引擎断开连接

```json
{
  "type": "disconnected",
  "reason": "Connection lost",
  "timestamp": "2024-02-17T13:46:40.000Z"
}
```

---

### 2. 系统状态

#### system_status - 系统状态

```json
{
  "type": "system_status",
  "uptime": 86400,
  "bot_status": "running",
  "active_strategies": 3,
  "total_profit": 12453.00,
  "total_trades": 1284,
  "success_rate": 94.2,
  "timestamp": "2024-02-17T13:46:40.000Z"
}
```

**字段说明**:
- `uptime`: 引擎运行时间（秒）
- `bot_status`: 机器人状态 (`running` | `stopped`)
- `active_strategies`: 活跃策略数量
- `total_profit`: 总利润
- `total_trades`: 总交易次数
- `success_rate`: 成功率（百分比）

---

### 3. 价格更新

#### price - 价格更新

```json
{
  "type": "price",
  "symbol": "BTC-USDT",
  "price": 52345.00,
  "bid": 52340.00,
  "ask": 52350.00,
  "timestamp": "2024-02-17T13:46:40.000Z"
}
```

**字段说明**:
- `symbol`: 交易对符号（使用 `-` 分隔）
- `price`: 最新价格
- `bid`: 买一价（可选）
- `ask`: 卖一价（可选）

---

### 4. 订单更新

#### order_update - 订单状态更新

```json
{
  "type": "order_update",
  "orderId": "ORD-001",
  "status": "filled",
  "filled": 0.15,
  "remaining": 0.0,
  "price": 52345.00,
  "symbol": "BTC-USDT",
  "side": "buy",
  "strategy": "PMM Strategy",
  "timestamp": "2024-02-17T13:46:40.000Z"
}
```

**字段说明**:
- `orderId`: 订单ID
- `status`: 订单状态 (`pending` | `open` | `filled` | `canceled` | `rejected`)
- `filled`: 已成交数量
- `remaining`: 剩余数量
- `price`: 订单价格
- `symbol`: 交易对符号
- `side`: 方向 (`buy` | `sell`)
- `strategy`: 所属策略（可选）

---

### 5. 仓位更新

#### position - 仓位更新

```json
{
  "type": "position",
  "symbol": "BTC-USDT",
  "size": 0.15,
  "entry_price": 52000.00,
  "current_price": 52345.00,
  "pnl": 51.75,
  "pnl_percent": 0.66,
  "side": "long",
  "strategy": "PMM Strategy",
  "timestamp": "2024-02-17T13:46:40.000Z"
}
```

**字段说明**:
- `symbol`: 交易对符号
- `size`: 仓位大小（正数为多头，负数为空头）
- `entry_price`: 入场价格
- `current_price`: 当前价格
- `pnl`: 未实现盈亏（绝对值）
- `pnl_percent`: 未实现盈亏（百分比）
- `side`: 方向 (`long` | `short`)
- `strategy`: 所属策略（可选）

---

### 6. 余额更新

#### balance - 余额更新

```json
{
  "type": "balance",
  "asset": "USDT",
  "free": 10000.00,
  "used": 2345.00,
  "total": 12345.00,
  "exchange": "binance",
  "timestamp": "2024-02-17T13:46:40.000Z"
}
```

**字段说明**:
- `asset`: 资产名称
- `free`: 可用余额
- `used`: 已使用余额
- `total`: 总余额
- `exchange`: 交易所名称

---

### 7. 策略状态更新

#### strategy - 策略状态

```json
{
  "type": "strategy",
  "id": "str-001",
  "name": "PMM Strategy",
  "status": "running",
  "exchange": "binance",
  "pair": "BTC-USDT",
  "profit": 523.00,
  "trades": 324,
  "error_msg": null,
  "timestamp": "2024-02-17T13:46:40.000Z"
}
```

**字段说明**:
- `id`: 策略ID
- `name`: 策略名称
- `status`: 状态 (`running` | `stopped` | `paused` | `error`)
- `exchange`: 交易所
- `pair`: 交易对
- `profit`: 策略利润
- `trades`: 策略交易次数
- `error_msg`: 错误消息（如果有）

---

### 8. 日志事件

#### log - 日志消息

```json
{
  "type": "log",
  "level": "info",
  "msg": "Order filled: BUY 0.15 BTC @ $52,345.00",
  "source": "PMM Strategy",
  "timestamp": "2024-02-17T13:46:40.000Z"
}
```

**字段说明**:
- `level`: 日志级别 (`debug` | `info` | `warning` | `error`)
- `msg`: 日志消息
- `source`: 日志来源（可选）

---

### 9. 连接状态更新

#### connection - 交易所连接状态

```json
{
  "type": "connection",
  "exchange": "binance",
  "status": "connected",
  "message": "Connected successfully",
  "timestamp": "2024-02-17T13:46:40.000Z"
}
```

**字段说明**:
- `exchange`: 交易所名称
- `status`: 连接状态 (`connected` | `disconnected` | `connecting`)
- `message`: 状态消息（可选）

---

### 10. 交易成交事件

#### trade - 交易成交

```json
{
  "type": "trade",
  "trade_id": "TRD-001",
  "order_id": "ORD-001",
  "symbol": "BTC-USDT",
  "price": 52345.00,
  "amount": 0.15,
  "side": "buy",
  "fee": 7.85,
  "strategy": "PMM Strategy",
  "timestamp": "2024-02-17T13:46:40.000Z"
}
```

**字段说明**:
- `trade_id`: 交易ID
- `order_id`: 订单ID
- `symbol`: 交易对符号
- `price`: 成交价格
- `amount`: 成交数量
- `side`: 方向 (`buy` | `sell`)
- `fee`: 手续费
- `strategy`: 所属策略（可选）

---

## 📥 命令接口

客户端通过 WebSocket 发送命令，后端处理后返回响应。

### 命令格式

```json
{
  "cmd": "command_name",
  "param1": "value1",
  "param2": "value2"
}
```

### 响应格式

```json
{
  "success": true,
  "message": "Command executed successfully",
  "data": {},
  "error": null
}
```

---

### 策略管理命令

#### start_strategy - 启动策略

**请求**:
```json
{
  "cmd": "start_strategy",
  "id": "str-001"
}
```

**响应**:
```json
{
  "success": true,
  "message": "Strategy str-001 started"
}
```

#### stop_strategy - 停止策略

**请求**:
```json
{
  "cmd": "stop_strategy",
  "id": "str-001"
}
```

#### pause_strategy - 暂停策略

**请求**:
```json
{
  "cmd": "pause_strategy",
  "id": "str-001"
}
```

#### resume_strategy - 恢复策略

**请求**:
```json
{
  "cmd": "resume_strategy",
  "id": "str-001"
}
```

#### delete_strategy - 删除策略

**请求**:
```json
{
  "cmd": "delete_strategy",
  "id": "str-001"
}
```

#### create_strategy - 创建策略

**请求**:
```json
{
  "cmd": "create_strategy",
  "name": "My Strategy",
  "type": "pmm",
  "exchange": "binance",
  "pair": "BTC-USDT"
}
```

**响应**:
```json
{
  "success": true,
  "message": "Strategy 'My Strategy' created",
  "instance_id": "str-001"
}
```

#### get_strategies - 获取策略列表

**请求**:
```json
{
  "cmd": "get_strategies"
}
```

**响应**:
```json
{
  "success": true,
  "strategies": [...]
}
```

---

### 订单管理命令

#### place_order - 下市价单

**请求**:
```json
{
  "cmd": "place_order",
  "symbol": "BTC-USDT",
  "side": "buy",
  "type": "market",
  "size": 0.15
}
```

#### place_order - 下限价单

**请求**:
```json
{
  "cmd": "place_order",
  "symbol": "BTC-USDT",
  "side": "buy",
  "type": "limit",
  "price": 52000.00,
  "size": 0.15
}
```

**响应**:
```json
{
  "success": true,
  "message": "Order placed",
  "order_id": "ORD-001"
}
```

#### cancel_order - 取消订单

**请求**:
```json
{
  "cmd": "cancel_order",
  "order_id": "ORD-001"
}
```

**响应**:
```json
{
  "success": true,
  "message": "Order ORD-001 cancelled"
}
```

#### cancel_all_orders - 取消所有订单

**请求**:
```json
{
  "cmd": "cancel_all_orders"
}
```

或指定交易对：
```json
{
  "cmd": "cancel_all_orders",
  "symbol": "BTC-USDT"
}
```

**响应**:
```json
{
  "success": true,
  "message": "Cancelled 5 orders",
  "cancelled_count": 5
}
```

#### get_orders - 获取订单列表

**请求**:
```json
{
  "cmd": "get_orders"
}
```

支持筛选：
```json
{
  "cmd": "get_orders",
  "symbol": "BTC-USDT",
  "status": "filled",
  "strategy": "str-001"
}
```

**响应**:
```json
{
  "success": true,
  "orders": [...],
  "count": 10
}
```

---

### 连接管理命令

#### create_connection - 创建连接

**请求**:
```json
{
  "cmd": "create_connection",
  "exchange": "binance",
  "api_key": "your_api_key",
  "api_secret": "your_api_secret",
  "testnet": false
}
```

**响应**:
```json
{
  "success": true,
  "message": "Connection to binance created",
  "connection_id": "conn-001"
}
```

#### delete_connection - 删除连接

**请求**:
```json
{
  "cmd": "delete_connection",
  "id": "conn-001"
}
```

#### test_connection - 测试连接

**请求**:
```json
{
  "cmd": "test_connection",
  "id": "conn-001"
}
```

**响应**:
```json
{
  "success": true,
  "message": "Connection conn-001 is healthy"
}
```

---

### 系统命令

#### start_engine - 启动引擎

**请求**:
```json
{
  "cmd": "start_engine"
}
```

**响应**:
```json
{
  "success": true,
  "message": "Engine started"
}
```

#### stop_engine - 停止引擎

**请求**:
```json
{
  "cmd": "stop_engine"
}
```

**响应**:
```json
{
  "success": true,
  "message": "Engine stopped"
}
```

#### get_system_status - 获取系统状态

**请求**:
```json
{
  "cmd": "get_system_status"
}
```

**响应**:
```json
{
  "success": true,
  "uptime": 86400,
  "bot_status": "running",
  "active_strategies": 3,
  "total_profit": 12453.00,
  "total_trades": 1284,
  "success_rate": 94.2
}
```

#### get_positions - 获取仓位列表

**请求**:
```json
{
  "cmd": "get_positions"
}
```

**响应**:
```json
{
  "success": true,
  "positions": [...]
}
```

#### get_balances - 获取余额列表

**请求**:
```json
{
  "cmd": "get_balances"
}
```

**响应**:
```json
{
  "success": true,
  "balances": [...]
}
```

---

## 🔧 完整示例

### React Hook 示例

```typescript
import { useEffect, useState, useRef, useCallback } from 'react';

function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<any[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  // 连接 WebSocket
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/api/stream');

    ws.onopen = () => {
      setConnected(true);
      console.log('✅ WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents(prev => [...prev, data]);
      console.log('📥 Received:', data);
    };

    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
    };

    ws.onclose = () => {
      setConnected(false);
      console.log('🔌 WebSocket closed');
    };

    wsRef.current = ws;

    return () => ws.close();
  }, []);

  // 发送命令
  const sendCommand = useCallback((command: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(command));
    }
  }, []);

  // 启动策略
  const startStrategy = useCallback((id: string) => {
    sendCommand({ cmd: 'start_strategy', id });
  }, [sendCommand]);

  // 下单
  const placeOrder = useCallback((params: any) => {
    sendCommand({ cmd: 'place_order', ...params });
  }, [sendCommand]);

  return {
    connected,
    events,
    startStrategy,
    placeOrder,
    sendCommand,
  };
}
```

### Vue Composable 示例

```typescript
import { ref, onMounted, onUnmounted } from 'vue';

export function useWebSocket() {
  const connected = ref(false);
  const events = ref<any[]>([]);

  let ws: WebSocket | null = null;

  const connect = () => {
    ws = new WebSocket('ws://localhost:8000/api/stream');

    ws.onopen = () => {
      connected.value = true;
      console.log('✅ WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      events.value.push(data);
      console.log('📥 Received:', data);
    };

    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
    };

    ws.onclose = () => {
      connected.value = false;
      console.log('🔌 WebSocket closed');
    };
  };

  const sendCommand = (command: any) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(command));
    }
  };

  onMounted(connect);
  onUnmounted(() => ws?.close());

  return {
    connected,
    events,
    sendCommand,
  };
}
```

---

## 📚 相关文档

- [前端交接文档](./FRONTEND_HANDOFF.md)
- [WebSocket 403 修复文档](./WEBSOCKET_403_FIX.md)
- [API 文档](http://localhost:8000/docs)

---

## ⚠️ 注意事项

1. **端口配置**: 服务运行在 `8000` 端口（不是 5000）
2. **重连机制**: 客户端应实现自动重连逻辑
3. **事件顺序**: 事件按发布顺序推送
4. **命令超时**: 命令执行可能需要时间，建议设置超时
5. **错误处理**: 所有响应都包含 `success` 字段，应先检查
6. **CORS 配置**: 已配置允许跨域访问

---

## 🐛 常见问题

### Q1: 连接后立即断开？

可能原因：
1. 服务未启动
2. 端口错误
3. WebSocket 握手失败

检查服务状态：
```bash
curl http://localhost:8000/api/health
```

### Q2: 收不到事件？

可能原因：
1. 事件未触发（需要触发操作）
2. 订阅失败
3. 网络问题

检查浏览器控制台日志。

### Q3: 命令无响应？

可能原因：
1. 命令格式错误
2. 缺少必需参数
3. 服务器内部错误

检查命令格式是否符合文档要求。

---

**文档版本**: 1.0.0
**更新日期**: 2024-02-17
