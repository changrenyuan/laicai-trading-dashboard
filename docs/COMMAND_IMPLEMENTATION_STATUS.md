# WebSocket 命令实现状态报告

## 概述

检查所有 WebSocket 命令的实现状态，发现部分命令是 TODO 占位符。

---

## 实现状态总览

| 类别 | 命令数 | 已实现 | TODO占位符 | 依赖外部 |
|------|--------|--------|-----------|---------|
| 策略管理 | 7 | 7 | 0 | 7 (strategy_manager) |
| 订单管理 | 4 | 2 | 2 | 2 (exchange) |
| 连接管理 | 4 | 4 | 0 | 0 |
| 系统命令 | 5 | 5 | 0 | 2 (exchange, position_manager) |
| **总计** | **20** | **18** | **2** | **11** |

---

## 详细状态

### 1. 策略管理命令 (7/7 已实现)

✅ 所有命令已实现，但依赖 `self.bot.strategy_manager`

| 命令 | 状态 | 依赖 | 说明 |
|------|------|------|------|
| `start_strategy` | ✅ 已实现 | `bot.strategy_manager` | 启动策略实例 |
| `stop_strategy` | ✅ 已实现 | `bot.strategy_manager` | 停止策略实例 |
| `pause_strategy` | ✅ 已实现 | `bot.strategy_manager` | 暂停策略实例 |
| `resume_strategy` | ✅ 已实现 | `bot.strategy_manager` | 恢复策略实例 |
| `delete_strategy` | ✅ 已实现 | `bot.strategy_manager` | 删除策略实例 |
| `create_strategy` | ✅ 已实现 | `bot.strategy_manager` | 创建策略实例 |
| `get_strategies` | ✅ 已实现 | `bot.strategy_manager` | 获取策略列表 |

**依赖检查**：
```python
# start_backend_debug.py
self.strategy_manager = None  # ⚠️ 目前为 None
```

**状态**：代码已实现，但 `strategy_manager` 为 None，实际调用会失败。

---

### 2. 订单管理命令 (2/4 已实现)

⚠️ **2个命令是 TODO 占位符**

| 命令 | 状态 | 依赖 | 说明 |
|------|------|------|------|
| `place_order` | ❌ TODO占位符 | 无 | 只返回假订单ID |
| `cancel_order` | ❌ TODO占位符 | 无 | 只返回假响应 |
| `cancel_all_orders` | ✅ 已实现 | `bot.exchange` | 调用 exchange API |
| `get_orders` | ✅ 已实现 | `bot.exchange` | 调用 exchange API |

#### TODO占位符详情

**`_place_order`**：
```python
async def _place_order(self, command: Dict) -> Dict:
    # ... 参数检查 ...

    try:
        # 这里需要调用实际的交易所下单接口
        # 临时实现
        order_id = f"ORD-{int(datetime.utcnow().timestamp())}"
        return {
            "success": True,
            "message": "Order placed",
            "order_id": order_id
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**`_cancel_order`**：
```python
async def _cancel_order(self, command: Dict) -> Dict:
    # ... 参数检查 ...

    try:
        # 这里需要调用实际的交易所取消订单接口
        # 临时实现
        return {
            "success": True,
            "message": f"Order {order_id} cancelled"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

### 3. 连接管理命令 (4/4 已实现)

✅ 所有命令已实现（刚刚完成）

| 命令 | 状态 | 依赖 | 说明 |
|------|------|------|------|
| `create_connection` | ✅ 已实现 | OKXConnector | 创建真实连接 |
| `delete_connection` | ✅ 已实现 | 无 | 关闭连接 |
| `test_connection` | ✅ 已实现 | OKXConnector | 测试连接健康 |
| `get_connections` | ✅ 已实现 | 无 | 获取连接列表 |

**状态**：完全实现，可以实际使用。

---

### 4. 系统命令 (5/5 已实现)

✅ 所有命令已实现，但部分依赖外部组件

| 命令 | 状态 | 依赖 | 说明 |
|------|------|------|------|
| `start_engine` | ✅ 已实现 | 无 | 设置 is_running = True |
| `stop_engine` | ✅ 已实现 | 无 | 设置 is_running = False |
| `get_system_status` | ✅ 已实现 | `bot.strategy_manager` | 获取系统状态 |
| `get_positions` | ✅ 已实现 | `bot.position_manager` | 获取仓位列表 |
| `get_balances` | ✅ 已实现 | `bot.exchange` | 获取余额列表 |

**依赖检查**：
```python
# start_backend_debug.py
self.position_manager = PositionManager()  # ✅ 已初始化
self.strategy_manager = None               # ⚠️ 目前为 None
# exchange 需要通过 create_connection 创建
```

---

## 关键问题

### 🔴 严重问题

#### 1. `_place_order` 和 `_cancel_order` 是 TODO 占位符

**影响**：
- 无法真正下单
- 无法真正取消订单
- 只返回假的订单ID和响应

**需要实现**：
```python
async def _place_order(self, command: Dict) -> Dict:
    # 需要从 connections 获取连接器
    # 调用 connector.place_order()
    # 返回真实的订单ID
    pass
```

#### 2. `strategy_manager` 为 None

**影响**：
- 所有策略管理命令会返回 "Strategy manager not available"
- 无法启动、停止、创建策略

**需要修复**：
```python
# start_backend_debug.py
from src.core.strategy_manager import StrategyManager
self.strategy_manager = StrategyManager(self.event_bus, self.bot)
```

### 🟡 中等问题

#### 3. 订单命令依赖 `bot.exchange`

**影响**：
- `cancel_all_orders` 和 `get_orders` 依赖 `bot.exchange`
- 需要先创建连接并设置到 bot

**需要修复**：
```python
# 在 create_connection 后，将 connector 设置到 bot
self.bot.exchange = connector
```

---

## 修复优先级

### P0 - 立即修复（阻塞功能）

1. **实现 `_place_order`**
   - 连接到 OKX 下单 API
   - 返回真实订单ID
   - 发布订单事件

2. **实现 `_cancel_order`**
   - 连接到 OKX 取消订单 API
   - 返回真实响应
   - 发布订单事件

3. **初始化 `strategy_manager`**
   - 在 start_backend_debug.py 中初始化
   - 确保策略管理命令可用

### P1 - 高优先级（影响体验）

4. **修复订单命令依赖**
   - 在 create_connection 时设置 bot.exchange
   - 确保 cancel_all_orders 和 get_orders 可用

5. **测试所有命令**
   - 创建完整的测试用例
   - 验证每个命令的功能

### P2 - 中优先级（增强功能）

6. **添加订单事件**
   - 订单创建事件
   - 订单取消事件
   - 订单更新事件

7. **添加策略事件**
   - 策略启动事件
   - 策略停止事件
   - 策略更新事件

---

## 实现建议

### 1. 实现 `_place_order`

```python
async def _place_order(self, command: Dict) -> Dict:
    """下单"""
    connection_id = command.get("connection_id")
    symbol = command.get("symbol")
    side = command.get("side")
    order_type = command.get("type")
    size = command.get("size")
    price = command.get("price")

    # 获取连接器
    if connection_id not in self.connections:
        return {"success": False, "error": "Connection not found"}

    connector = self.connections[connection_id]["connector"]

    # 调用交易所下单接口
    try:
        order_result = await connector.place_order(
            trading_pair=symbol,
            amount=Decimal(str(size)),
            price=Decimal(str(price)) if order_type == "limit" else None,
            side=side,
            order_type=order_type
        )

        # 发布订单事件
        await self.event_bus.publish_event({
            "type": "order_update",
            "event": "created",
            "order_id": order_result.get("order_id"),
            "symbol": symbol,
            "side": side,
            "size": size,
            "price": price
        })

        return {
            "success": True,
            "message": "Order placed",
            "order_id": order_result.get("order_id"),
            "order": order_result
        }
    except Exception as e:
        logger.error(f"Place order failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### 2. 实现 `_cancel_order`

```python
async def _cancel_order(self, command: Dict) -> Dict:
    """取消订单"""
    connection_id = command.get("connection_id")
    order_id = command.get("order_id")

    # 获取连接器
    if connection_id not in self.connections:
        return {"success": False, "error": "Connection not found"}

    connector = self.connections[connection_id]["connector"]

    # 调用交易所取消订单接口
    try:
        result = await connector.cancel_order(order_id)

        # 发布订单事件
        await self.event_bus.publish_event({
            "type": "order_update",
            "event": "cancelled",
            "order_id": order_id,
            "result": result
        })

        return {
            "success": True,
            "message": f"Order {order_id} cancelled",
            "result": result
        }
    except Exception as e:
        logger.error(f"Cancel order failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### 3. 初始化 `strategy_manager`

```python
# start_backend_debug.py
from src.core.strategy_manager import StrategyManager

class MockBot:
    def __init__(self):
        self.is_running = False
        self.strategy = None
        self.position_manager = PositionManager()
        self.risk_manager = RiskManager({})
        from src.core.event_bus import EventBus
        self.event_bus = EventBus()

        # ✅ 初始化策略管理器
        self.strategy_manager = StrategyManager(self.event_bus, self)
```

### 4. 修复订单命令依赖

```python
async def _create_connection(self, command: Dict) -> Dict:
    # ... 创建连接器 ...

    # 设置到 bot，供订单命令使用
    self.bot.exchange = connector

    # ...
```

---

## 测试清单

### 策略管理
- [ ] `start_strategy` - 启动策略
- [ ] `stop_strategy` - 停止策略
- [ ] `pause_strategy` - 暂停策略
- [ ] `resume_strategy` - 恢复策略
- [ ] `delete_strategy` - 删除策略
- [ ] `create_strategy` - 创建策略
- [ ] `get_strategies` - 获取策略列表

### 订单管理
- [ ] `place_order` - 下单 ⚠️ 需要实现
- [ ] `cancel_order` - 取消订单 ⚠️ 需要实现
- [ ] `cancel_all_orders` - 取消所有订单
- [ ] `get_orders` - 获取订单列表

### 连接管理
- [x] `create_connection` - 创建连接 ✅ 已实现
- [x] `delete_connection` - 删除连接 ✅ 已实现
- [x] `test_connection` - 测试连接 ✅ 已实现
- [x] `get_connections` - 获取连接列表 ✅ 已实现

### 系统命令
- [ ] `start_engine` - 启动引擎
- [ ] `stop_engine` - 停止引擎
- [ ] `get_system_status` - 获取系统状态
- [ ] `get_positions` - 获取仓位列表
- [ ] `get_balances` - 获取余额列表

---

## 总结

### ✅ 已完成

1. 连接管理命令完全实现
2. 系统命令代码已实现
3. 策略管理命令代码已实现
4. 订单管理部分实现

### ❌ 需要修复

1. `_place_order` - TODO 占位符
2. `_cancel_order` - TODO 占位符
3. `strategy_manager` - 未初始化
4. 订单命令依赖 - 需要设置 bot.exchange

### 📊 实现进度

- **代码实现**：18/20 (90%)
- **实际可用**：约 50%（部分依赖未初始化）
- **完全可用**：约 30%（需要修复 P0 问题）

---

## 下一步行动

1. **立即修复 P0 问题**
   - 实现 `_place_order`
   - 实现 `_cancel_order`
   - 初始化 `strategy_manager`

2. **修复 P1 问题**
   - 设置 bot.exchange
   - 测试所有命令

3. **完善 P2 功能**
   - 添加订单事件
   - 添加策略事件
   - 完善错误处理
