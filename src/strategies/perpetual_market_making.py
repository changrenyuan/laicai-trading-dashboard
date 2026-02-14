"""
永续合约做市策略 (Perpetual Market Making)
基于 Hummingbot 的 perpetual_market_making 策略
"""
import asyncio
import logging
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

from ..core.strategy import StrategyBase
from ..core.position import PositionSide
from ..core.event_bus import EventBus


@dataclass
class PriceSize:
    """价格和数量"""
    price: Decimal
    size: Decimal


@dataclass
class Proposal:
    """订单提案"""
    buy: PriceSize
    sell: PriceSize


class PerpetualMarketMakingStrategy(StrategyBase):
    """
    永续合约做市策略

    特性：
    - 支持多头和空头止盈
    - 支持止损
    - 支持多级订单
    - 支持杠杆交易
    """

    def __init__(
        self,
        event_bus: EventBus,
        position_manager,
        risk_manager,
        config: Dict
    ):
        super().__init__(event_bus, position_manager, risk_manager, config)

        # 策略配置
        self.trading_pair = config.get('trading_pair', 'BTC-USDT-SWAP')
        self.leverage = config.get('leverage', 10)
        self.position_mode = config.get('position_mode', 'one_way')  # one_way or hedge

        # 订单配置
        self.order_amount = Decimal(str(config.get('order_amount', 0.001)))
        self.bid_spread = Decimal(str(config.get('bid_spread', 0.001)))
        self.ask_spread = Decimal(str(config.get('ask_spread', 0.001)))
        self.minimum_spread = Decimal(str(config.get('minimum_spread', 0.0005)))
        self.order_refresh_time = config.get('order_refresh_time', 30)
        self.order_refresh_tolerance_pct = Decimal(str(config.get('order_refresh_tolerance_pct', -1)))
        self.filled_order_delay = config.get('filled_order_delay', 60)

        # 止盈止损配置
        self.long_profit_taking_spread = Decimal(str(config.get('long_profit_taking_spread', 0.02)))
        self.short_profit_taking_spread = Decimal(str(config.get('short_profit_taking_spread', 0.02)))
        self.stop_loss_spread = Decimal(str(config.get('stop_loss_spread', 0.05)))
        self.time_between_stop_loss_orders = config.get('time_between_stop_loss_orders', 60)
        self.stop_loss_slippage_buffer = Decimal(str(config.get('stop_loss_slippage_buffer', 0.001)))

        # 多级订单配置
        self.order_levels = config.get('order_levels', 1)
        self.order_level_spread = Decimal(str(config.get('order_level_spread', 0.0005)))
        self.order_level_amount = Decimal(str(config.get('order_level_amount', 0.001)))

        # 价格区间
        self.price_ceiling = Decimal(str(config.get('price_ceiling', -1))) if config.get('price_ceiling') else None
        self.price_floor = Decimal(str(config.get('price_floor', -1))) if config.get('price_floor') else None

        # 订单优化
        self.order_optimization_enabled = config.get('order_optimization_enabled', False)
        self.ask_order_optimization_depth = Decimal(str(config.get('ask_order_optimization_depth', 1)))
        self.bid_order_optimization_depth = Decimal(str(config.get('bid_order_optimization_depth', 1)))

        # 价格源
        self.price_type = config.get('price_type', 'mid_price')

        # 内部状态
        self._last_order_refresh_time = 0
        self._last_fill_time = 0
        self._last_stop_loss_time = 0
        self._buy_levels = self.order_levels
        self._sell_levels = self.order_levels

        self.logger.info(f"永续合约做市策略初始化: {self.trading_pair}, 杠杆: {self.leverage}x")

    async def on_tick(self, ticker: Dict):
        """价格更新回调"""
        await super().on_tick(ticker)

        current_time = datetime.now().timestamp()

        # 检查止盈止损
        await self._check_take_profit_stop_loss(ticker)

        # 检查订单刷新
        if current_time - self._last_order_refresh_time > self.order_refresh_time:
            await self._refresh_orders(ticker)

    async def on_order_book(self, order_book: Dict):
        """订单簿更新回调"""
        await super().on_order_book(order_book)
        # 可以基于订单簿优化订单

    def _calculate_order_prices(self, mid_price: Decimal, ticker: Dict) -> List[Proposal]:
        """计算订单价格"""
        proposals = []

        # 计算买单价
        bid_price = mid_price * (Decimal(1) - self.bid_spread / Decimal(100))
        ask_price = mid_price * (Decimal(1) + self.ask_spread / Decimal(100))

        # 应用价格区间
        if self.price_ceiling is not None:
            ask_price = min(ask_price, self.price_ceiling)
        if self.price_floor is not None:
            bid_price = max(bid_price, self.price_floor)

        # 创建提案
        proposals.append(Proposal(
            buy=PriceSize(price=bid_price, size=self.order_amount),
            sell=PriceSize(price=ask_price, size=self.order_amount)
        ))

        # 多级订单
        if self.order_levels > 1:
            for level in range(1, self.order_levels):
                level_bid_price = bid_price * (Decimal(1) - self.order_level_spread * level / Decimal(100))
                level_ask_price = ask_price * (Decimal(1) + self.order_level_spread * level / Decimal(100))

                level_size = self.order_amount + (self.order_level_amount * level)

                proposals.append(Proposal(
                    buy=PriceSize(price=level_bid_price, size=level_size),
                    sell=PriceSize(price=level_ask_price, size=level_size)
                ))

        return proposals

    async def _refresh_orders(self, ticker: Dict):
        """刷新订单"""
        try:
            mid_price = ticker.get('last', ticker.get('bid', 0))
            if mid_price == 0:
                return

            # 检查最小价差
            current_spread = (ticker.get('ask', 0) - ticker.get('bid', 0)) / ticker.get('last', 1)
            if current_spread < self.minimum_spread:
                self.logger.debug(f"当前价差 {current_spread} 小于最小价差 {self.minimum_spread}，跳过")
                return

            proposals = self._calculate_order_prices(mid_price, ticker)

            # 取消现有订单
            await self._cancel_all_orders()

            # 提交新订单
            for proposal in proposals:
                await self._place_orders(proposal)

            self._last_order_refresh_time = datetime.now().timestamp()

        except Exception as e:
            self.logger.error(f"刷新订单失败: {e}")

    async def _place_orders(self, proposal: Proposal):
        """下订单"""
        try:
            # 买单
            if await self.risk_manager.can_create_order(proposal.buy.size, proposal.buy.price):
                buy_order_id = await self.create_order_callback(
                    self.trading_pair, 'buy', float(proposal.buy.size), float(proposal.buy.price), 'limit'
                )
                if buy_order_id:
                    self.logger.info(f"买单下单成功: {proposal.buy.price} x {proposal.buy.size}")

            # 卖单
            if await self.risk_manager.can_create_order(proposal.sell.size, proposal.sell.price):
                sell_order_id = await self.create_order_callback(
                    self.trading_pair, 'sell', float(proposal.sell.size), float(proposal.sell.price), 'limit'
                )
                if sell_order_id:
                    self.logger.info(f"卖单下单成功: {proposal.sell.price} x {proposal.sell.size}")

        except Exception as e:
            self.logger.error(f"下单失败: {e}")

    async def _cancel_all_orders(self):
        """取消所有订单"""
        try:
            cancelled = await self.cancel_all_orders_callback()
            if cancelled > 0:
                self.logger.info(f"取消了 {cancelled} 个订单")
        except Exception as e:
            self.logger.error(f"取消订单失败: {e}")

    async def _check_take_profit_stop_loss(self, ticker: Dict):
        """检查止盈止损"""
        try:
            current_price = ticker.get('last', 0)
            if current_price == 0:
                return

            # 检查多头仓位
            long_position = self.position_manager.get_position(self.trading_pair, PositionSide.LONG)
            if long_position and long_position.size > 0:
                entry_price = long_position.entry_price
                pnl_pct = (current_price - entry_price) / entry_price

                # 止盈
                if pnl_pct >= self.long_profit_taking_spread:
                    self.logger.info(f"多头止盈: 入场 {entry_price}, 当前 {current_price}, 盈利 {pnl_pct:.2%}")
                    await self._close_position(PositionSide.LONG, 'sell')

                # 止损
                elif pnl_pct <= -self.stop_loss_spread:
                    self.logger.info(f"多头止损: 入场 {entry_price}, 当前 {current_price}, 亏损 {pnl_pct:.2%}")
                    await self._close_position(PositionSide.LONG, 'sell')

            # 检查空头仓位
            short_position = self.position_manager.get_position(self.trading_pair, PositionSide.SHORT)
            if short_position and short_position.size > 0:
                entry_price = short_position.entry_price
                pnl_pct = (entry_price - current_price) / entry_price

                # 止盈
                if pnl_pct >= self.short_profit_taking_spread:
                    self.logger.info(f"空头止盈: 入场 {entry_price}, 当前 {current_price}, 盈利 {pnl_pct:.2%}")
                    await self._close_position(PositionSide.SHORT, 'buy')

                # 止损
                elif pnl_pct <= -self.stop_loss_spread:
                    self.logger.info(f"空头止损: 入场 {entry_price}, 当前 {current_price}, 亏损 {pnl_pct:.2%}")
                    await self._close_position(PositionSide.SHORT, 'buy')

        except Exception as e:
            self.logger.error(f"检查止盈止损失败: {e}")

    async def _close_position(self, side: PositionSide, order_side: str):
        """平仓"""
        try:
            position = self.position_manager.get_position(self.trading_pair, side)
            if position:
                order_id = await self.create_order_callback(
                    self.trading_pair,
                    order_side,
                    float(position.size),
                    0,  # 市价单
                    'market'
                )
                if order_id:
                    self.logger.info(f"平仓订单已提交: {side.value} {position.size}")
        except Exception as e:
            self.logger.error(f"平仓失败: {e}")

    async def _run_loop(self):
        """策略主循环"""
        while self.is_running:
            try:
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"永续合约做市策略主循环错误: {e}")

    def get_status(self) -> Dict:
        """获取策略状态"""
        return {
            "strategy": "perpetual_market_making",
            "trading_pair": self.trading_pair,
            "leverage": self.leverage,
            "position_mode": self.position_mode,
            "order_amount": str(self.order_amount),
            "bid_spread": str(self.bid_spread),
            "ask_spread": str(self.ask_spread),
            "long_profit_taking_spread": str(self.long_profit_taking_spread),
            "short_profit_taking_spread": str(self.short_profit_taking_spread),
            "stop_loss_spread": str(self.stop_loss_spread),
            "order_levels": self.order_levels,
            "is_running": self.is_running
        }
