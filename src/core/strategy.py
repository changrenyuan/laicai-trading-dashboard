"""
策略基类
所有交易策略的基础框架
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Callable
from datetime import datetime
import asyncio
import logging

from .event_bus import EventBus
from .position import PositionManager, PositionSide
from .risk_manager import RiskManager

logger = logging.getLogger(__name__)


class StrategyBase(ABC):
    """策略基类"""

    def __init__(self, event_bus: EventBus, position_manager: PositionManager,
                 risk_manager: RiskManager, config: Dict):
        self.event_bus = event_bus
        self.position_manager = position_manager
        self.risk_manager = risk_manager
        self.config = config
        self.is_running = False
        self.is_active = False

        # 回调函数（由交易所提供）
        self.create_order_callback: Optional[Callable] = None
        self.cancel_order_callback: Optional[Callable] = None
        self.get_balance_callback: Optional[Callable] = None

        # 订单跟踪
        self.active_orders: Dict[str, Dict] = {}

        # 订阅事件
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅相关事件"""
        self.event_bus.subscribe(
            "order_filled",
            self._on_order_filled
        )

    def set_callbacks(self, create_order: Callable, cancel_order: Callable,
                     get_balance: Callable):
        """设置回调函数"""
        self.create_order_callback = create_order
        self.cancel_order_callback = cancel_order
        self.get_balance_callback = get_balance

    async def start(self):
        """启动策略"""
        if self.is_running:
            logger.warning("Strategy is already running")
            return

        self.is_running = True
        self.is_active = True
        logger.info(f"Strategy {self.__class__.__name__} started")

        await self.event_bus.publish("strategy_start", {
            "strategy": self.__class__.__name__,
            "timestamp": datetime.utcnow().isoformat()
        })

        # 启动策略主循环
        asyncio.create_task(self._run_loop())

    async def stop(self):
        """停止策略"""
        if not self.is_running:
            return

        self.is_running = False
        self.is_active = False
        logger.info(f"Strategy {self.__class__.__name__} stopped")

        # 取消所有活动订单
        await self._cancel_all_orders()

        await self.event_bus.publish("strategy_stop", {
            "strategy": self.__class__.__name__,
            "timestamp": datetime.utcnow().isoformat()
        })

    @abstractmethod
    async def _run_loop(self):
        """策略主循环（由子类实现）"""
        pass

    @abstractmethod
    async def on_tick(self, tick: Dict):
        """价格数据更新回调（由子类实现）"""
        pass

    @abstractmethod
    async def on_order_book(self, order_book: Dict):
        """订单簿更新回调（由子类实现）"""
        pass

    async def _on_order_filled(self, data: Dict):
        """订单成交回调"""
        order_id = data.get("order_id")
        if order_id in self.active_orders:
            order_info = self.active_orders[order_id]
            logger.info(f"Order filled: {order_id} {order_info}")

            # 更新仓位
            side = order_info.get("side")
            size = order_info.get("size")
            price = order_info.get("price")
            symbol = order_info.get("symbol")

            # 判断是开仓还是平仓
            position = self.position_manager.get_position(symbol,
                                                        PositionSide(side))
            if position:
                # 平仓
                if (position.side == PositionSide.LONG and side == "sell") or \
                   (position.side == PositionSide.SHORT and side == "buy"):
                    closed_pos = self.position_manager.close_position(
                        symbol, PositionSide(side), price
                    )
                    if closed_pos:
                        self.risk_manager.update_daily_pnl(closed_pos.realized_pnl)
            else:
                # 开仓
                self.position_manager.open_position(
                    symbol, PositionSide(side), size, price
                )

            # 更新止损止盈
            await self._update_risk_orders(symbol, side, price)

            # 移除活动订单
            del self.active_orders[order_id]

    async def _update_risk_orders(self, symbol: str, side: str, price: float):
        """更新止损止盈订单"""
        if self.risk_manager.config.get("enable_stop_loss"):
            self.risk_manager.set_stop_loss(symbol, side, price)

        if self.risk_manager.config.get("enable_take_profit"):
            self.risk_manager.set_take_profit(symbol, side, price)

    async def _create_order(self, symbol: str, side: str, size: float,
                           price: float, order_type: str = "limit") -> Optional[str]:
        """创建订单"""
        if not self.create_order_callback:
            logger.error("create_order_callback not set")
            return None

        # 风控检查
        allowed, msg = self.risk_manager.check_order_size(size)
        if not allowed:
            logger.warning(f"Order rejected by risk manager: {msg}")
            return None

        # 检查仓位限制
        position_sizes = self.position_manager.get_position_size(symbol)
        current_size = position_sizes.get(side, 0.0)
        allowed, msg = self.risk_manager.check_position_limit(
            symbol, current_size, size
        )
        if not allowed:
            logger.warning(f"Position limit exceeded: {msg}")
            return None

        try:
            order_id = await self.create_order_callback(
                symbol=symbol,
                side=side,
                size=size,
                price=price,
                order_type=order_type
            )

            if order_id:
                self.active_orders[order_id] = {
                    "symbol": symbol,
                    "side": side,
                    "size": size,
                    "price": price,
                    "order_type": order_type,
                    "created_at": datetime.utcnow()
                }

                await self.event_bus.publish("order_submitted", {
                    "order_id": order_id,
                    "symbol": symbol,
                    "side": side,
                    "size": size,
                    "price": price
                })

                logger.info(f"Order created: {order_id} {symbol} {side} {size}@{price}")
                return order_id

        except Exception as e:
            logger.error(f"Error creating order: {e}", exc_info=True)

        return None

    async def _cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        if not self.cancel_order_callback:
            return False

        if order_id not in self.active_orders:
            logger.warning(f"Order {order_id} not found in active orders")
            return False

        try:
            result = await self.cancel_order_callback(order_id)
            if result:
                del self.active_orders[order_id]
                await self.event_bus.publish("order_cancelled", {
                    "order_id": order_id
                })
                logger.info(f"Order cancelled: {order_id}")
                return True
        except Exception as e:
            logger.error(f"Error cancelling order: {e}", exc_info=True)

        return False

    async def _cancel_all_orders(self):
        """取消所有活动订单"""
        order_ids = list(self.active_orders.keys())
        for order_id in order_ids:
            await self._cancel_order(order_id)

    def get_status(self) -> Dict:
        """获取策略状态"""
        return {
            "is_running": self.is_running,
            "is_active": self.is_active,
            "active_orders_count": len(self.active_orders),
            "strategy_name": self.__class__.__name__,
            "config": self.config
        }
