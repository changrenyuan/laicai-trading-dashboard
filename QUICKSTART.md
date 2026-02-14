# Hummingbot Lite - 快速参考

## 项目概述

Hummingbot Lite 是一个基于 Hummingbot 架构的量化交易机器人 Python 复刻版本，专注于 OKX 交易所的实盘交易。

## 核心功能

### 1. OKX 交易所集成
- 完整的 REST API 支持
- 现货交易
- 订单管理（创建、取消、查询）
- 市场数据（行情、订单簿、K线）

### 2. 策略框架
- 事件驱动架构
- 策略基类（可扩展）
- 示例策略：做市策略

### 3. 仓位管理
- 自动跟踪开仓/平仓
- 实时计算盈亏（已实现/未实现）
- 仓位大小管理

### 4. 风控系统
- 止损自动触发
- 止盈自动触发
- 仓位大小限制
- 单笔订单限制
- 每日亏损限制

### 5. Web 控制面板
- 实时监控
- 策略启动/停止
- 订单管理
- 事件日志
- WebSocket 实时通信

## 快速开始

```bash
# 1. 安装依赖
./install.sh

# 2. 配置 API
vim config.yaml

# 3. 启动程序
./start.sh

# 4. 访问控制面板
http://localhost:5000
```

## 目录结构

```
hummingbot-lite/
├── src/
│   ├── core/                   # 核心框架
│   │   ├── event_bus.py       # 事件总线
│   │   ├── strategy.py        # 策略基类
│   │   ├── position.py        # 仓位管理
│   │   └── risk_manager.py    # 风控模块
│   ├── connectors/            # 交易所连接器
│   │   └── okx.py             # OKX 实现
│   ├── strategies/            # 交易策略
│   │   └── market_maker.py    # 做市策略
│   ├── ui/                    # Web 界面
│   │   └── web.py             # FastAPI + WebSocket
│   └── main.py                # 主程序入口
├── config.yaml                # 配置文件
├── config.example.yaml        # 配置模板
├── requirements.txt           # Python 依赖
├── install.sh                 # 安装脚本
├── start.sh                   # 启动脚本
├── README.md                  # 项目说明
└── TESTING.md                 # 测试指南
```

## API 端点

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | / | Web 控制面板 |
| GET | /api/status | 获取机器人状态 |
| GET | /api/balance | 获取账户余额 |
| GET | /api/orders | 获取订单列表 |
| POST | /api/start | 启动策略 |
| POST | /api/stop | 停止策略 |
| POST | /api/cancel-all-orders | 取消所有订单 |
| GET | /api/events | 获取事件历史 |
| GET | /api/performance | 获取策略表现 |

## WebSocket

连接：`ws://localhost:5000/ws`

消息类型：
- `status_update` - 状态更新
- `event` - 事件推送（order_filled, strategy_start 等）

## 配置参数

### 交易所配置
```yaml
exchange:
  api_key: "YOUR_API_KEY"
  secret_key: "YOUR_SECRET_KEY"
  passphrase: "YOUR_PASSPHRASE"
  sandbox: false  # true=测试网, false=实盘
```

### 策略配置
```yaml
strategy:
  trading_pair: "BTC-USDT"
  order_amount: 0.001
  bid_spread: 0.001      # 0.1%
  ask_spread: 0.001      # 0.1%
  order_refresh_time: 30 # 秒
```

### 风控配置
```yaml
risk_management:
  max_position_size: 0.1
  max_order_size: 0.01
  stop_loss_percentage: 0.02    # 2%
  take_profit_percentage: 0.03  # 3%
  max_daily_loss: 0.05          # 5%
```

## 代码示例

### 创建自定义策略

```python
from src.core.strategy import StrategyBase

class MyStrategy(StrategyBase):
    async def _run_loop(self):
        """策略主循环"""
        while self.is_running:
            # 你的逻辑
            pass

    async def on_tick(self, tick):
        """价格更新回调"""
        print(f"Price: {tick['last']}")

    async def on_order_book(self, order_book):
        """订单簿更新回调"""
        pass
```

### 使用事件总线

```python
# 订阅事件
event_bus.subscribe("order_filled", lambda data: print(data))

# 发布事件
await event_bus.publish("order_filled", {
    "order_id": "123",
    "symbol": "BTC-USDT",
    "price": 50000
})
```

### 仓位管理

```python
# 开仓
position = position_manager.open_position(
    symbol="BTC-USDT",
    side=PositionSide.LONG,
    size=0.01,
    entry_price=50000
)

# 平仓
closed = position_manager.close_position(
    symbol="BTC-USDT",
    side=PositionSide.LONG,
    exit_price=50500
)

# 获取盈亏
total_pnl = position_manager.get_total_realized_pnl()
```

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行程序
python src/main.py

# 测试模块导入
python -c "from src.core.event_bus import EventBus; print('OK')"

# 检查端口
lsof -i:5000

# 查看日志（如果有）
tail -f logs/*.log
```

## 故障排查

| 问题 | 解决方案 |
|------|---------|
| ModuleNotFoundError | 运行 `pip install -r requirements.txt` |
| 连接失败 | 检查 API 密钥和网络 |
| 端口被占用 | 修改 config.yaml 中的端口 |
| 订单被拒绝 | 检查账户余额和权限 |

## 最佳实践

1. **先测试后实盘**
   - 在沙盒环境充分测试
   - 使用小额资金验证

2. **合理设置风控**
   - 止损：2-5%
   - 止盈：3-10%
   - 每日亏损限制：3-10%

3. **定期监控**
   - 不要长时间无人值守
   - 关注市场波动
   - 检查订单状态

4. **备份数据**
   - 定期备份配置
   - 记录交易日志

5. **API 安全**
   - 启用 IP 白名单
   - 不要泄露 API 密钥
   - 定期更换密钥

## 技术栈

- **Python 3.12+**
- **FastAPI** - Web 框架
- **ccxt** - 交易所 API
- **WebSockets** - 实时通信
- **YAML** - 配置文件

## 扩展开发

### 添加新策略
1. 继承 `StrategyBase`
2. 实现 `_run_loop()`, `on_tick()`, `on_order_book()`
3. 在 `config.yaml` 中配置参数

### 添加新交易所
1. 在 `src/connectors/` 下创建新文件
2. 继承或参考 `OKXConnector`
3. 实现交易所特定接口

### 添加风控规则
1. 在 `RiskManager` 中添加方法
2. 在策略中调用风控检查
3. 在 config.yaml 中配置参数

## 相关资源

- [Hummingbot 官网](https://www.hummingbot.org)
- [OKX API 文档](https://www.okx.com/docs-v5)
- [ccxt 文档](https://docs.ccxt.com)
- [FastAPI 文档](https://fastapi.tiangolo.com)

## 免责声明

本软件仅供学习交流使用。使用本软件进行实盘交易所造成的任何损失，开发者不承担任何责任。

---

**版本**: 1.0.0
**更新日期**: 2024
