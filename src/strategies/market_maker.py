"""
做市策略
在买卖价差之间挂单，赚取差价
"""
from typing import Dict
from datetime import datetime
import asyncio
import logging

from ..core.strategy import StrategyBase
from ..core.event_bus import EventBus
from ..core.position import PositionManager, PositionSide
from ..core.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class MarketMakerStrategy(StrategyBase):
    """做市策略"""

    def __init__(self, event_bus: EventBus, position_manager: PositionManager,
                 risk_manager: RiskManager, config: Dict):
        super().__init__(event_bus, position_manager, risk_manager, config)

        # 策略参数
        self.trading_pair = config.get("trading_pair", "BTC-USDT")
        self.order_amount = config.get("order_amount", 0.001)
        self.bid_spread = config.get("bid_spread", 0.001)
        self.ask_spread = config.get("ask_spread", 0.001)
        self.order_refresh_time = config.get("order_refresh_time", 30)

        # 当前价格和订单簿
        self.current_price = 0.0
        self.best_bid = 0.0
        self.best_ask = 0.0

        # 策略状态
        self.last_order_refresh = 0
        self.bid_order_id: str = None
        self.ask_order_id: str = None

        # 统计数据
        self.total_orders = 0
        self.total_fills = 0
        self.total_trades = 0

        logger.info(f"MarketMakerStrategy initialized for {self.trading_pair}")

    async def _run_loop(self):
        """策略主循环"""
        logger.info("MarketMakerStrategy main loop started")

        while self.is_running:
            try:
                if self.is_active:
                    await self._strategy_logic()

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in strategy loop: {e}", exc_info=True)
                await self.event_bus.publish("strategy_error", {
                    "strategy": "MarketMakerStrategy",
                    "error": str(e)
                })
                await asyncio.sleep(5)

    async def _strategy_logic(self):
        """策略逻辑"""
        now = datetime.utcnow().timestamp()

        # 定期刷新订单
        if now - self.last_order_refresh > self.order_refresh_time:
            await self._refresh_orders()
            self.last_order_refresh = now

        # 检查止损止盈
        await self._check_risk_levels()

    async def _refresh_orders(self):
        """刷新挂单"""
        try:
            # 取消现有订单
            if self.bid_order_id:
                await self._cancel_order(self.bid_order_id)
            if self.ask_order_id:
                await self._cancel_order(self.ask_order_id)

            # 计算新的挂单价格
            if self.current_price > 0:
                mid_price = (self.best_bid + self.best_ask) / 2

                # 考虑仓位平衡调整价格
                position_sizes = self.position_manager.get_position_size(
                    self.trading_pair
                )
                base_asset_size = position_sizes.get("long", 0.0) - \
                                position_sizes.get("short", 0.0)

                # 仓位不平衡时调整价格
                price_adjustment = 0
                if self.config.get("auto_rebalance", True):
                    inventory_target = self.config.get(
                        "inventory_target_base_pct", 0.5
                    )
                    # 简化的库存偏差调整
                    if abs(base_asset_size) > 0:
                        price_adjustment = -0.0005 * (1 if base_asset_size > 0 else -1)

                bid_price = mid_price * (1 - self.bid_spread + price_adjustment)
                ask_price = mid_price * (1 + self.ask_spread + price_adjustment)

                # 创建新订单
                self.bid_order_id = await self._create_order(
                    symbol=self.trading_pair,
                    side="buy",
                    size=self.order_amount,
                    price=bid_price
                )

                self.ask_order_id = await self._create_order(
                    symbol=self.trading_pair,
                    side="sell",
                    size=self.order_amount,
                    price=ask_price
                )

                if self.bid_order_id or self.ask_order_id:
                    self.total_orders += 1
                    logger.info(f"Orders refreshed: bid@{bid_price} ask@{ask_price}")

        except Exception as e:
            logger.error(f"Error refreshing orders: {e}", exc_info=True)

    async def _check_risk_levels(self):
        """检查风控触发"""
        if self.current_price == 0:
            return

        # 检查所有仓位的止损止盈
        for key, position in self.position_manager.get_all_positions().items():
            # 检查止损
            stop_triggered, stop_order = self.risk_manager.check_stop_loss(
                position.symbol,
                position.side.value,
                self.current_price
            )

            if stop_triggered:
                logger.warning(f"Stop loss triggered for {position.symbol}")
                # 平仓
                close_side = "sell" if position.side == PositionSide.LONG else "buy"
                await self._create_order(
                    symbol=position.symbol,
                    side=close_side,
                    size=position.size,
                    price=self.current_price
                )

            # 检查止盈
            tp_triggered, tp_order = self.risk_manager.check_take_profit(
                position.symbol,
                position.side.value,
                self.current_price
            )

            if tp_triggered:
                logger.info(f"Take profit triggered for {position.symbol}")
                # 平仓
                close_side = "sell" if position.side == PositionSide.LONG else "buy"
                await self._create_order(
                    symbol=position.symbol,
                    side=close_side,
                    size=position.size,
                    price=self.current_price
                )

    async def on_tick(self, tick: Dict):
        """价格数据更新"""
        self.current_price = tick.get("last", 0.0)
        self.best_bid = tick.get("bid", 0.0)
        self.best_ask = tick.get("ask", 0.0)

        # 更新仓位未实现盈亏
        self.position_manager.update_unrealized_pnl(
            self.trading_pair,
            self.current_price
        )

    async def on_order_book(self, order_book: Dict):
        """订单簿更新"""
        if order_book.get("bids") and order_book.get("asks"):
            self.best_bid = order_book["bids"][0][0] if order_book["bids"] else 0.0
            self.best_ask = order_book["asks"][0][0] if order_book["asks"] else 0.0

            # 更新当前价格
            if self.current_price == 0:
                self.current_price = (self.best_bid + self.best_ask) / 2

    def get_performance(self) -> Dict:
        """获取策略表现"""
        return {
            "strategy_name": "MarketMakerStrategy",
            "trading_pair": self.trading_pair,
            "total_orders": self.total_orders,
            "total_fills": self.total_fills,
            "total_trades": self.total_trades,
            "current_price": self.current_price,
            "realized_pnl": self.position_manager.get_total_realized_pnl(),
            "unrealized_pnl": self.position_manager.get_total_unrealized_pnl(),
            "active_orders": {
                "bid": self.bid_order_id,
                "ask": self.ask_order_id
            }
        }

    def to_dict(self) -> Dict:
        """转换为字典"""
        base_dict = super().get_status()
        base_dict.update({
            "trading_pair": self.trading_pair,
            "order_amount": self.order_amount,
            "current_price": self.current_price,
            "performance": self.get_performance()
        })
        return base_dict
