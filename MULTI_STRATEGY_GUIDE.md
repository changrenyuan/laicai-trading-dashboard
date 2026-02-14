# Hummingbot Lite - 多策略管理文档

## 概述

Hummingbot Lite 现在支持多策略实例管理，可以同时运行多个不同类型的策略，实现更加灵活的量化交易。

## 支持的策略类型

### 1. Market Maker (经典做市)
- 在买卖价差之间挂单
- 适用于流动性较好的交易对
- 无特殊参数

### 2. Pure Market Making (现货做市)
- 纯现货做市策略
- **新特性**:
  - 库存偏差管理: 自动调整订单以维持目标库存比例
  - Ping-Pong 模式: 交替买卖，适合趋势市场
  - 动态价格带: 自动调整价格上下限
  - 多级订单: 同时挂多档订单
  - 挂单模式: 成交后保留另一边订单

### 3. Perpetual Market Making (永续合约做市)
- 永续合约做市策略
- **新特性**:
  - 止盈功能: 多头/空头分别设置止盈
  - 止损功能: 自动止损保护
  - 杠杆交易: 支持 1x-100x 杠杆
  - 仓位模式: 支持单向和双向持仓
  - 多级订单: 同时挂多档订单

### 4. Spot-Perpetual Arbitrage (现货永续套利)
- 在现货和永续合约之间套利
- **新特性**:
  - 自动检测套利机会
  - 对冲风险（现货买+永续卖，或相反）
  - 自动开仓和平仓
  - 滑点缓冲保护
  - 冷却时间控制

## 启动多策略管理

### 演示模式（无需 API 密钥）

```bash
python src/main_multi_strategy_demo.py
```

访问 http://localhost:5000 查看控制面板

### 实盘模式

```bash
python src/main_multi_strategy.py
```

## Web 控制面板功能

### 创建策略实例

1. 在控制面板顶部选择策略类型
2. 输入策略配置（YAML 格式）
3. 点击"创建策略"

示例配置：
```yaml
trading_pair: BTC-USDT-SWAP
bid_spread: 0.1
ask_spread: 0.1
order_amount: 0.001
long_profit_taking_spread: 2.0
stop_loss_spread: 5.0
leverage: 10
```

### 管理策略实例

每个策略实例卡片显示：
- 策略名称和类型
- 运行状态（运行中/已停止）
- 关键参数和状态
- 控制按钮：
  - **启动**: 启动策略
  - **停止**: 停止策略
  - **删除**: 删除策略实例

### 事件日志

实时显示：
- 策略实例创建/启动/停止事件
- 订单成交事件
- 策略状态变化

## API 接口

### 获取可用策略列表

```bash
GET /api/strategies
```

响应示例：
```json
{
  "strategies": [
    {
      "name": "market_maker",
      "display_name": "Market Maker",
      "description": "经典做市策略，在买卖价差之间挂单"
    },
    ...
  ]
}
```

### 获取所有策略实例

```bash
GET /api/strategy-instances
```

### 创建策略实例

```bash
POST /api/strategy-instances
Content-Type: application/json

{
  "strategy_name": "perpetual_market_making",
  "config": {
    "trading_pair": "BTC-USDT-SWAP",
    "bid_spread": 0.1,
    "order_amount": 0.001
  }
}
```

### 启动策略实例

```bash
POST /api/strategy-instances/{instance_id}/start
```

### 停止策略实例

```bash
POST /api/strategy-instances/{instance_id}/stop
```

### 删除策略实例

```bash
DELETE /api/strategy-instances/{instance_id}
```

### 更新策略配置

```bash
PUT /api/strategy-instances/{instance_id}/config
Content-Type: application/json

{
  "config": {
    "bid_spread": 0.2
  }
}
```

## 策略配置文件模板

所有策略配置模板位于 `configs/` 目录：

- `conf_perpetual_market_making_strategy_TEMPLATE.yml` - 永续合约做市
- `conf_pure_market_making_strategy_TEMPLATE.yml` - 纯现货做市
- `conf_spot_perpetual_arbitrage_strategy_TEMPLATE.yml` - 现货永续套利

## 使用示例

### 示例 1: 同时运行多个永续合约策略

1. 创建第一个策略（BTC 做市）
   ```bash
   POST /api/strategy-instances
   {
     "strategy_name": "perpetual_market_making",
     "config": {
       "trading_pair": "BTC-USDT-SWAP",
       "bid_spread": 0.1,
       "ask_spread": 0.1,
       "order_amount": 0.001,
       "leverage": 10
     }
   }
   ```

2. 创建第二个策略（ETH 做市）
   ```bash
   POST /api/strategy-instances
   {
     "strategy_name": "perpetual_market_making",
     "config": {
       "trading_pair": "ETH-USDT-SWAP",
       "bid_spread": 0.15,
       "ask_spread": 0.15,
       "order_amount": 0.01,
       "leverage": 5
     }
   }
   ```

3. 同时启动两个策略

### 示例 2: 混合策略运行

1. 创建现货做市策略
   ```bash
   POST /api/strategy-instances
   {
     "strategy_name": "pure_market_making",
     "config": {
       "trading_pair": "BTC-USDT",
       "bid_spread": 0.1,
       "ping_pong_enabled": true
     }
   }
   ```

2. 创建套利策略
   ```bash
   POST /api/strategy-instances
   {
     "strategy_name": "spot_perpetual_arbitrage",
     "config": {
       "spot_trading_pair": "BTC-USDT",
       "perp_trading_pair": "BTC-USDT-SWAP",
       "order_amount": 0.001,
       "min_opening_arbitrage_pct": 0.001
     }
   }
   ```

3. 同时运行，套利策略捕获价差，做市策略提供流动性

## 注意事项

1. **资金管理**: 同时运行多个策略时，确保账户资金充足
2. **风险控制**: 每个策略独立应用风控规则
3. **性能监控**: 注意观察系统负载和延迟
4. **策略冲突**: 避免同一交易对上运行冲突策略
5. **仓位管理**: 永续合约策略注意仓位风险

## 常见问题

### Q: 同时运行多少个策略合适？

A: 取决于账户资金和交易对数量。建议开始时运行 2-3 个策略，逐步增加。

### Q: 不同策略可以使用相同的交易对吗？

A: 可以，但需要注意：
- 确保总仓位不超过风控限制
- 避免策略间相互干扰
- 监控总风险敞口

### Q: 如何停止所有策略？

A: 在控制面板上逐个点击"停止"按钮，或调用 API：
```bash
# 获取所有运行中的实例
GET /api/strategy-instances

# 逐个停止
POST /api/strategy-instances/{instance_id}/stop
```

### Q: 策略配置可以在线修改吗？

A: 可以，通过更新配置接口：
```bash
PUT /api/strategy-instances/{instance_id}/config
```

注意：部分配置修改需要重启策略生效。

## 技术架构

```
┌─────────────────────────────────────────┐
│         Web Control Panel               │
│  (多策略管理界面 + 实时事件展示)          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│       Strategy Manager                  │
│   (策略实例管理 + 事件分发 + 回调)       │
└──────┬────────────────────────┬─────────┘
       │                        │
       ▼                        ▼
┌──────────────┐        ┌──────────────┐
│  Instance 1  │        │  Instance N  │
│  (Strategy)  │  ...   │  (Strategy)  │
└──────┬───────┘        └──────┬───────┘
       │                        │
       └────────────┬───────────┘
                    ▼
           ┌────────────────┐
           │   Exchange     │
           │   (交易所API)   │
           └────────────────┘
```

## 下一步

- [ ] 添加更多策略类型（网格、马丁等）
- [ ] 策略性能分析和报告
- [ ] 策略回测功能
- [ ] 多交易所支持
- [ ] 移动端控制面板
