# Hummingbot Lite 🚀

基于 Hummingbot 架构的量化交易机器人 Python 复刻版本

## ✨ 特性

- ✅ **完整的 OKX 交易所集成** - 支持现货交易，使用 ccxt 库实现
- 🤖 **做市策略** - 经典的做市策略，在买卖价差之间挂单
- 💰 **仓位管理** - 自动跟踪开仓/平仓，计算盈亏
- 🛡️ **风险控制** - 止损、止盈、仓位限制、每日亏损限制
- 📊 **Web UI 控制面板** - 实时监控策略状态、仓位、盈亏
- 🔄 **WebSocket 实时通信** - 实时推送交易事件和市场数据
- 🎯 **事件驱动架构** - 模块化设计，易于扩展新策略

## 🏗️ 架构

```
hummingbot-lite/
├── src/
│   ├── core/                   # 核心框架
│   │   ├── event_bus.py       # 事件总线（发布-订阅模式）
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
├── requirements.txt           # Python 依赖
└── README.md                  # 本文件
```

## 📋 系统要求

- Python 3.12+
- OKX API Key（需要先在 OKX 开通 API）

## 🚀 快速开始

### 1. 克隆项目

```bash
cd /workspace/projects
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置代理（如需要）

⚠️ **注意**: OKX 交易所在中国大陆需要通过代理访问。

#### 支持的代理配置方式

**方式 1: Clash 代理（推荐）**
```yaml
exchange:
  proxy: "clash"  # 或 "clash-socks5" (需安装 aiohttp-socks)
```

**方式 2: HTTP 代理**
```yaml
exchange:
  proxy: "http://127.0.0.1:7890"
```

**方式 3: SOCKS5 代理**
```yaml
exchange:
  proxy: "socks5://127.0.0.1:7891"
```

**方式 4: 端口号**
```yaml
exchange:
  proxy: "7890"  # 自动使用 HTTP 协议
```

#### 测试代理连接

```bash
python test_proxy.py
```

详细配置请参考 [PROXY_CONFIG.md](PROXY_CONFIG.md)。

### 4. 配置 OKX API

编辑 `config.yaml` 文件，填写您的 OKX API 信息：

```yaml
exchange:
  name: "okx"
  api_key: "YOUR_API_KEY"          # 替换为你的 OKX API Key
  secret_key: "YOUR_SECRET_KEY"    # 替换为你的 OKX Secret Key
  passphrase: "YOUR_PASSPHRASE"    # 替换为你的 OKX Passphrase
  sandbox: false                   # 是否使用沙盒环境（测试网）
```

**获取 OKX API Key：**

1. 登录 [OKX 官网](https://www.okx.com)
2. 进入「API 管理」
3. 创建 API Key
4. 选择权限：交易、读取
5. **重要**：启用 IP 白名单（推荐）

### 5. 配置策略参数

在 `config.yaml` 中调整策略参数：

```yaml
strategy:
  name: "market_maker"             # 策略名称
  trading_pair: "BTC-USDT"         # 交易对
  order_amount: 0.001              # 订单数量（BTC）
  bid_spread: 0.001                # 买单价差 (0.1%)
  ask_spread: 0.001                # 卖单价差 (0.1%)
  order_refresh_time: 30           # 订单刷新时间（秒）
```

### 6. 配置风控参数

```yaml
risk_management:
  max_position_size: 0.1           # 最大仓位（BTC）
  max_order_size: 0.01             # 单笔最大订单（BTC）
  stop_loss_percentage: 0.02       # 止损百分比 (2%)
  take_profit_percentage: 0.03     # 止盈百分比 (3%)
  max_daily_loss: 0.05             # 每日最大亏损 (5%)
```

### 7. 启动程序

```bash
python src/main.py
```

### 8. 访问 Web 控制面板

打开浏览器访问：http://localhost:5000

控制面板功能：
- 📊 实时查看策略状态
- 💰 查看仓位和盈亏
- 🛡️ 查看风控状态
- ▶️ 启动/停止策略
- ❌ 取消所有订单
- 📋 实时事件日志

## 💡 使用指南

### 演示模式（无需 API 密钥）

如果只是想预览界面和体验功能，可以使用演示模式：

```bash
python src/main_demo.py
```

演示模式特点：
- ✅ 无需 API 密钥
- ✅ 使用模拟交易所
- ✅ 模拟价格波动和订单成交
- ✅ 完整的 UI 功能展示

### 启动策略

1. 打开 Web 控制面板
2. 点击「启动」按钮
3. 策略开始自动运行

### 停止策略

点击「停止」按钮，策略会：
- 停止创建新订单
- 取消所有活动订单
- 保持仓位跟踪

### 调整参数

编辑 `config.yaml` 文件后需要重启程序。

### 查看日志

- 控制台：实时输出彩色日志
- Web 界面：事件日志区域

## 🔧 核心模块说明

### 1. 事件总线 (EventBus)

采用发布-订阅模式，用于组件间通信：

```python
# 订阅事件
event_bus.subscribe("order_filled", callback)

# 发布事件
await event_bus.publish("order_filled", data)
```

### 2. 策略基类 (StrategyBase)

所有策略继承自 `StrategyBase`，实现以下方法：

```python
class MyStrategy(StrategyBase):
    async def _run_loop(self):
        """策略主循环"""
        pass

    async def on_tick(self, tick):
        """价格更新回调"""
        pass

    async def on_order_book(self, order_book):
        """订单簿更新回调"""
        pass
```

### 3. 仓位管理 (PositionManager)

自动跟踪开仓/平仓：

```python
# 开仓
position = position_manager.open_position(
    symbol="BTC-USDT",
    side=PositionSide.LONG,
    size=0.001,
    entry_price=50000
)

# 平仓
closed_pos = position_manager.close_position(
    symbol="BTC-USDT",
    side=PositionSide.LONG,
    exit_price=50500
)

# 获取盈亏
total_pnl = position_manager.get_total_realized_pnl()
```

### 4. 风控管理 (RiskManager)

多层风控保护：

```python
# 检查订单大小
allowed, msg = risk_manager.check_order_size(size)

# 设置止损
risk_manager.set_stop_loss(symbol, side, entry_price, 0.02)

# 检查止损触发
triggered, order = risk_manager.check_stop_loss(symbol, side, current_price)
```

## 📝 API 接口

### REST API

- `GET /` - Web 控制面板
- `GET /api/status` - 获取机器人状态
- `GET /api/balance` - 获取账户余额
- `GET /api/orders` - 获取订单列表
- `POST /api/start` - 启动策略
- `POST /api/stop` - 停止策略
- `POST /api/cancel-all-orders` - 取消所有订单
- `GET /api/events` - 获取事件历史
- `GET /api/performance` - 获取策略表现

### WebSocket

连接：`ws://localhost:5000/ws`

消息类型：
- `status_update` - 状态更新
- `event` - 事件推送

## ⚠️ 风险提示

1. **投资有风险**：量化交易存在资金损失风险
2. **先测试后实盘**：建议先在沙盒环境测试
3. **合理配置风控**：根据资金量设置合理的风控参数
4. **定期监控**：不要长时间无人值守运行
5. **API 安全**：妥善保管 API 密钥，设置 IP 白名单

## 🔮 未来计划

- [ ] 添加更多策略（网格交易、趋势跟踪等）
- [ ] 支持更多交易所（Binance、Bybit 等）
- [ ] 添加回测功能
- [ ] 支持永续合约
- [ ] 添加数据持久化
- [ ] 性能监控和报警

## 📄 许可证

本项目仅供学习和研究使用，不构成任何投资建议。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 支持

如有问题，请查看日志输出或提交 Issue。

---

**免责声明**：本软件仅供学习交流使用。使用本软件进行实盘交易所造成的任何损失，开发者不承担任何责任。请在充分了解风险的前提下谨慎使用。
