"""
统一事件总线 - Hummingbot 的核心机制
实现发布-订阅模式，用于组件间通信
支持标准化的前端事件格式
"""
from typing import Callable, Dict, List, Any, Optional
import asyncio
import logging
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class EngineEventType(Enum):
    """引擎事件类型 - 与前端 engineStore 对齐"""
    # 连接状态
    CONNECTED = "connected"              # 引擎已连接
    DISCONNECTED = "disconnected"        # 引擎断开连接
    CONNECTION = "connection"            # 交易所连接状态更新

    # 系统状态
    SYSTEM_STATUS = "system_status"      # 系统状态（uptime、profit等）

    # 交易数据
    PRICE = "price"                      # 价格更新
    ORDER_UPDATE = "order_update"        # 订单更新
    TRADE = "trade"                      # 交易成交
    POSITION = "position"                # 仓位更新
    BALANCE = "balance"                  # 余额更新

    # 策略管理
    STRATEGY = "strategy"                # 策略状态

    # 系统日志
    LOG = "log"                          # 日志消息
    SNAPSHOT = "snapshot"                # 状态快照（重连时发送）
    ERROR = "error"                      # 错误事件


class EventBus:
    """
    统一事件总线实现

    事件格式标准化：
    {
        "type": "price" | "order_update" | "position" | "strategy" | "log" | "snapshot",
        "timestamp": "ISO 8601",
        ... 其他字段根据事件类型不同
    }
    """

    def __init__(self):
        # 订阅者：type -> [callbacks]
        self._subscribers: Dict[str, List[Callable]] = {}
        # 事件历史
        self._event_history: List[Dict] = []
        self._max_history = 1000
        # 事件队列（保证顺序）
        self._event_queue: asyncio.Queue = asyncio.Queue()
        # 是否正在处理队列
        self._processing = False

    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.info(f"Subscribed to event: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                logger.info(f"Unsubscribed from event: {event_type}")
            except ValueError:
                pass

    async def publish(self, event_type: str, data: Dict):
        """
        发布事件（异步）

        Args:
            event_type: 事件类型（price, order_update, position, strategy, log）
            data: 事件数据（必须包含必要字段）
        """
        # 构建标准化事件
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            **data
        }

        # 记录事件历史
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        logger.debug(f"Publishing event: {event_type}")

        # 将事件加入队列（保证顺序）
        await self._event_queue.put(event)

        # 启动处理队列（如果未启动）
        if not self._processing:
            asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        """处理事件队列"""
        self._processing = True

        while not self._event_queue.empty():
            event = await self._event_queue.get()
            event_type = event["type"]

            # 通知所有订阅者
            if event_type in self._subscribers:
                tasks = []
                for callback in self._subscribers[event_type]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            tasks.append(callback(event))
                        else:
                            callback(event)
                    except Exception as e:
                        logger.error(f"Error in event callback: {e}", exc_info=True)

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

        self._processing = False

    def get_event_history(self, event_type: str = None, limit: int = 100):
        """获取事件历史"""
        if event_type:
            events = [e for e in self._event_history if e["type"] == event_type]
        else:
            events = self._event_history

        return events[-limit:]

    def clear_history(self):
        """清空事件历史"""
        self._event_history.clear()

    # ============ 便捷方法 - 标准化事件推送 ============

    async def publish_price(self, symbol: str, price: float, bid: float = None, ask: float = None):
        """
        推送价格更新

        格式: { "type": "price", "symbol": "ETH-USDT", "price": 3821.3, "bid": 3820.0, "ask": 3822.0 }
        """
        data = {
            "symbol": symbol,
            "price": price
        }
        if bid is not None:
            data["bid"] = bid
        if ask is not None:
            data["ask"] = ask

        await self.publish(EngineEventType.PRICE.value, data)

    async def publish_order_update(
        self,
        order_id: str,
        status: str,
        symbol: str = None,
        filled: float = 0,
        price: float = None
    ):
        """
        推送订单更新

        格式: { "type": "order_update", "orderId": "A12", "status": "filled", "filled": 0.01, "symbol": "ETH-USDT" }
        """
        data = {
            "orderId": order_id,
            "status": status,
            "filled": filled
        }
        if symbol:
            data["symbol"] = symbol
        if price is not None:
            data["price"] = price

        await self.publish(EngineEventType.ORDER_UPDATE.value, data)

    async def publish_position(self, symbol: str, size: float, pnl: float = 0, side: str = "long"):
        """
        推送仓位更新

        格式: { "type": "position", "symbol": "ETH-USDT", "size": 0.02, "pnl": 100, "side": "long" }
        """
        await self.publish(EngineEventType.POSITION.value, {
            "symbol": symbol,
            "size": size,
            "pnl": pnl,
            "side": side
        })

    async def publish_strategy(self, strategy_id: str, status: str, config: Dict = None):
        """
        推送策略状态

        格式: { "type": "strategy", "id": "market_maker", "status": "running", "config": {...} }
        """
        data = {
            "id": strategy_id,
            "status": status
        }
        if config:
            data["config"] = config

        await self.publish(EngineEventType.STRATEGY.value, data)

    async def publish_log(self, level: str, msg: str, logger_name: str = None):
        """
        推送日志消息

        格式: { "type": "log", "level": "INFO", "msg": "order filled", "logger": "strategy" }
        """
        data = {
            "level": level,
            "msg": msg
        }
        if logger_name:
            data["logger"] = logger_name

        await self.publish(EngineEventType.LOG.value, data)

    async def publish_error(self, error_type: str, message: str, details: Dict = None):
        """
        推送错误事件

        格式: { "type": "error", "error_type": "order_failed", "message": "...", "details": {...} }
        """
        data = {
            "error_type": error_type,
            "message": message
        }
        if details:
            data["details"] = details

        await self.publish(EngineEventType.ERROR.value, data)

    async def publish_snapshot(self, snapshot_data: Dict):
        """
        推送状态快照（重连时使用）

        格式: {
            "type": "snapshot",
            "strategies": [...],
            "orders": [...],
            "positions": [...],
            "balances": [...]
        }
        """
        await self.publish(EngineEventType.SNAPSHOT.value, snapshot_data)

    # ============ 新增事件类型 ============

    async def publish_connected(self):
        """
        推送引擎连接状态 - 已连接

        格式: { "type": "connected", "timestamp": 1739800800 }
        """
        await self.publish(EngineEventType.CONNECTED.value, {})

    async def publish_disconnected(self, reason: str = None):
        """
        推送引擎连接状态 - 断开连接

        格式: { "type": "disconnected", "reason": "Connection lost", "timestamp": 1739800800 }
        """
        data = {}
        if reason:
            data["reason"] = reason
        await self.publish(EngineEventType.DISCONNECTED.value, data)

    async def publish_system_status(
        self,
        uptime: int,
        bot_status: str,
        active_strategies: int = 0,
        total_profit: float = 0.0,
        total_trades: int = 0,
        success_rate: float = 0.0
    ):
        """
        推送系统状态

        格式: {
            "type": "system_status",
            "uptime": 86400,
            "bot_status": "running",
            "active_strategies": 3,
            "total_profit": 12453.00,
            "total_trades": 1284,
            "success_rate": 94.2,
            "timestamp": 1739800800
        }
        """
        await self.publish(EngineEventType.SYSTEM_STATUS.value, {
            "uptime": uptime,
            "bot_status": bot_status,
            "active_strategies": active_strategies,
            "total_profit": total_profit,
            "total_trades": total_trades,
            "success_rate": success_rate
        })

    async def publish_balance(
        self,
        asset: str,
        free: float,
        used: float,
        total: float,
        exchange: str = "okx"
    ):
        """
        推送余额更新

        格式: {
            "type": "balance",
            "asset": "USDT",
            "free": 10000.00,
            "used": 2345.00,
            "total": 12345.00,
            "exchange": "binance",
            "timestamp": 1739800800
        }
        """
        await self.publish(EngineEventType.BALANCE.value, {
            "asset": asset,
            "free": free,
            "used": used,
            "total": total,
            "exchange": exchange
        })

    async def publish_connection(
        self,
        exchange: str,
        status: str,
        message: str = None
    ):
        """
        推送连接状态更新

        格式: {
            "type": "connection",
            "exchange": "binance",
            "status": "connected",
            "message": "Connected successfully",
            "timestamp": 1739800800
        }
        """
        data = {
            "exchange": exchange,
            "status": status
        }
        if message:
            data["message"] = message
        await self.publish(EngineEventType.CONNECTION.value, data)

    async def publish_trade(
        self,
        trade_id: str,
        order_id: str,
        symbol: str,
        price: float,
        amount: float,
        side: str,
        fee: float = 0.0,
        strategy: str = None
    ):
        """
        推送交易成交事件

        格式: {
            "type": "trade",
            "trade_id": "TRD-001",
            "order_id": "ORD-001",
            "symbol": "BTC/USDT",
            "price": 52345.00,
            "amount": 0.15,
            "side": "buy",
            "fee": 7.85,
            "strategy": "PMM Strategy",
            "timestamp": 1739800800
        }
        """
        data = {
            "trade_id": trade_id,
            "order_id": order_id,
            "symbol": symbol,
            "price": price,
            "amount": amount,
            "side": side,
            "fee": fee
        }
        if strategy:
            data["strategy"] = strategy
        await self.publish(EngineEventType.TRADE.value, data)
