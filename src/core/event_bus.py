"""
事件总线 - Hummingbot 的核心机制
实现发布-订阅模式，用于组件间通信
"""
from typing import Callable, Dict, List, Any
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EventType:
    """事件类型定义"""
    # 订单事件
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_EXPIRED = "order_expired"
    ORDER_FAILED = "order_failed"

    # 市场事件
    MARKET_TICK = "market_tick"
    MARKET_ORDER_BOOK = "market_order_book"
    MARKET_TRADE = "market_trade"

    # 账户事件
    ACCOUNT_BALANCE = "account_balance"
    POSITION_UPDATE = "position_update"

    # 策略事件
    STRATEGY_START = "strategy_start"
    STRATEGY_STOP = "strategy_stop"
    STRATEGY_ERROR = "strategy_error"

    # 风控事件
    RISK_LIMIT_BREACH = "risk_limit_breach"
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"
    TAKE_PROFIT_TRIGGERED = "take_profit_triggered"


class EventBus:
    """事件总线实现"""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_history: List[Dict] = []
        self._max_history = 1000

    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.info(f"Subscribed to event: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)
            logger.info(f"Unsubscribed from event: {event_type}")

    async def publish(self, event_type: str, data: Any = None):
        """发布事件（异步）"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }

        # 记录事件历史
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        logger.debug(f"Publishing event: {event_type} - {data}")

        # 通知所有订阅者
        if event_type in self._subscribers:
            tasks = []
            for callback in self._subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        tasks.append(callback(data))
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Error in event callback: {e}", exc_info=True)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

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
