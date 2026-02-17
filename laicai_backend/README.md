# Laicai Trading Backend

Hummingbot Lite 量化交易机器人后端服务。

## 📁 目录结构

```
laicai_backend/
├── src/                      # 源代码
│   ├── connectors/           # 交易所连接器
│   ├── core/                 # 核心模块
│   │   ├── event_bus.py      # 事件总线
│   │   ├── command_handler.py
│   │   ├── ws_command_handler.py  # WebSocket 命令处理器
│   │   ├── position.py       # 仓位管理
│   │   ├── risk_manager.py   # 风控管理
│   │   ├── strategy.py       # 策略基类
│   │   └── strategy_manager.py  # 策略管理器
│   ├── strategies/           # 交易策略
│   ├── ui/                   # Web 服务
│   │   ├── web_server.py     # WebServer（事件驱动架构）
│   │   └── api_extension.py  # API 扩展
│   ├── main_demo.py          # 演示主程序
│   └── main_multi_strategy_demo.py  # 多策略演示程序
├── configs/                  # 配置文件
├── state/                    # 状态存储
├── requirements.txt          # Python 依赖
├── start_backend_debug.py    # 后端启动脚本
├── config.example.yaml       # 配置示例
└── config_proxy_example.py   # 代理配置示例
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 并配置 API 密钥：

```bash
cp .env.example .env
```

### 3. 启动后端服务

```bash
cd laicai_backend
python start_backend_debug.py
```

服务将运行在：
- **API**: `http://localhost:8000`
- **WebSocket**: `ws://localhost:8000/api/stream`

## 🔌 WebSocket API

### 连接端点

| 端点 | 说明 |
|------|------|
| `/api/stream` | 推荐 - 事件流端点 |
| `/ws` | 通用 WebSocket 端点 |
| `/ws/logs` | 日志专用端点 |

### 事件推送

后端通过 WebSocket 推送以下事件类型：

| 事件类型 | 说明 |
|---------|------|
| `connected` | 引擎已连接 |
| `disconnected` | 引擎断开连接 |
| `system_status` | 系统状态 |
| `price` | 价格更新 |
| `order_update` | 订单更新 |
| `trade` | 交易成交 |
| `position` | 仓位更新 |
| `balance` | 余额更新 |
| `strategy` | 策略状态 |
| `log` | 日志消息 |
| `connection` | 连接状态 |
| `error` | 错误事件 |
| `snapshot` | 状态快照 |

### 命令接口

通过 WebSocket 发送命令：

```json
{
  "cmd": "get_system_status"
}
```

支持的命令类型：
- 策略管理：`start_strategy`, `stop_strategy`, `create_strategy`, `get_strategies` 等
- 订单管理：`place_order`, `cancel_order`, `cancel_all_orders`, `get_orders`
- 系统命令：`start_engine`, `stop_engine`, `get_system_status`, `get_positions`, `get_balances`

详细文档请参考主项目的 README.md。

## 📝 示例

### 连接 WebSocket

```python
import asyncio
import websockets
import json

async def connect():
    uri = "ws://localhost:8000/api/stream"
    async with websockets.connect(uri) as ws:
        # 接收事件
        message = await ws.recv()
        data = json.loads(message)
        print(f"Received: {data}")

        # 发送命令
        await ws.send(json.dumps({"cmd": "get_system_status"}))

asyncio.run(connect())
```

## 🔧 开发

### 架构说明

采用**事件驱动架构**：
- 所有状态变更通过 EventBus 推送
- WebSocket 实时推送事件给前端
- 前端通过 WebSocket 发送命令

### 数据流

```
后端模块 → EventBus → WebSocket → 前端
前端 → WebSocket → Command Handler → 后端模块
```

## 📚 相关文档

- [主项目 README](../README.md)
- [Hummingbot 文档](../assets/hummingbot-2.12.0/hummingbot/README.md)
