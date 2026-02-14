"""
纯做市策略 (Pure Market Making)
基于 Hummingbot 的 pure_market_making 策略
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


class PureMarketMakingStrategy(StrategyBase):
    """
    纯做市策略 (现货)

    特性：
    - 在买卖价差之间挂单
    - 支持多级订单
    - 支持库存偏差管理
    - 支持 Ping-Pong 模式
    - 支持挂单 (Hanging Orders)
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
        self.trading_pair = config.get('trading_pair', 'BTC-USDT')

        # 订单配置
        self.order_amount = Decimal(str(config.get('order_amount', 0.001)))
        self.bid_spread = Decimal(str(config.get('bid_spread', 0.001)))
        self.ask_spread = Decimal(str(config.get('ask_spread', 0.001)))
        self.minimum_spread = Decimal(str(config.get('minimum_spread', 0.0005)))
        self.order_refresh_time = config.get('order_refresh_time', 30)
        self.max_order_age = config.get('max_order_age', 1800)
        self.order_refresh_tolerance_pct = Decimal(str(config.get('order_refresh_tolerance_pct', -1)))
        self.filled_order_delay = config.get('filled_order_delay', 60)

        # 价格区间
        self.price_ceiling = Decimal(str(config.get('price_ceiling', -1))) if config.get('price_ceiling') else None
        self.price_floor = Decimal(str(config.get('price_floor', -1))) if config.get('price_floor') else None

        # 动态价格带
        self.moving_price_band_enabled = config.get('moving_price_band_enabled', False)
        self.price_ceiling_pct = Decimal(str(config.get('price_ceiling_pct', 0.1)))
        self.price_floor_pct = Decimal(str(config.get('price_floor_pct', 0.1)))
        self.price_band_refresh_time = config.get('price_band_refresh_time', 300)

        # Ping-Pong 模式
        self.ping_pong_enabled = config.get('ping_pong_enabled', False)
        self._ping_pong_state = 'buy'  # 'buy' or 'sell'

        # 库存偏差管理
        self.inventory_skew_enabled = config.get('inventory_skew_enabled', False)
        self.inventory_target_base_pct = Decimal(str(config.get('inventory_target_base_pct', 0.5)))
        self.inventory_range_multiplier = Decimal(str(config.get('inventory_range_multiplier', 0.1)))
        self.inventory_price = Decimal(str(config.get('inventory_price', 0)))

        # 多级订单
        self.order_levels = config.get('order_levels', 1)
        self.order_level_spread = Decimal(str(config.get('order_level_spread', 0.0005)))
        self.order_level_amount = Decimal(str(config.get('order_level_amount', 0.001)))

        # 挂单模式
        self.hanging_orders_enabled = config.get('hanging_orders_enabled', False)
        self.hanging_orders_cancel_pct = Decimal(str(config.get('hanging_orders_cancel_pct', 0.1)))

        # 订单优化
        self.order_optimization_enabled = config.get('order_optimization_enabled', False)
        self.ask_order_optimization_depth = Decimal(str(config.get('ask_order_optimization_depth', 1)))
        self.bid_order_optimization_depth = Decimal(str(config.get('bid_order_optimization_depth', 1)))

        # 价格源
        self.price_type = config.get('price_type', 'mid_price')

        # 内部状态
        self._last_order_refresh_time = 0
        self._last_fill_time = 0
        self._last_price_band_refresh_time = 0
        self._moving_ceiling = None
        self._moving_floor = None

        self.logger.info(f"纯做市策略初始化: {self.trading_pair}")

    async def on_tick(self, ticker: Dict):
        """价格更新回调"""
        await super().on_tick(ticker)

        current_time = datetime.now().timestamp()

        # 更新动态价格带
        if self.moving_price_band_enabled:
            await self._update_moving_price_band(ticker, current_time)

        # 检查订单刷新
        if current_time - self._last_order_refresh_time > self.order_refresh_time:
            await self._refresh_orders(ticker)

    def _update_moving_price_band(self, ticker: Dict, current_time: float):
        """更新动态价格带"""
        if current_time - self._last_price_band_refresh_time < self.price_band_refresh_time:
            return

        current_price = ticker.get('last', 0)
        if current_price == 0:
            return

        self._moving_ceiling = current_price * (Decimal(1) + self.price_ceiling_pct)
        self._moving_floor = current_price * (Decimal(1) - self.price_floor_pct)
        self._last_price_band_refresh_time = current_time

        self.logger.debug(f"动态价格带更新: [{self._moving_floor}, {self._moving_ceiling}]")

    def _get_effective_price_ceiling(self) -> Optional[Decimal]:
        """获取有效的价格上限"""
        if self._moving_ceiling is not None:
            return self._moving_ceiling
        return self.price_ceiling

    def _get_effective_price_floor(self) -> Optional[Decimal]:
        """获取有效的价格下限"""
        if self._moving_floor is not None:
            return self._moving_floor
        return self.price_floor

    def _calculate_order_prices(self, mid_price: Decimal, ticker: Dict) -> List[Dict]:
        """计算订单价格"""
        proposals = []

        # 库存偏差调整
        bid_adjustment = Decimal(0)
        ask_adjustment = Decimal(0)

        if self.inventory_skew_enabled:
            bid_adjustment, ask_adjustment = self._calculate_inventory_skew_adjustment()

        # 计算买单价
        bid_price = mid_price * (Decimal(1) - (self.bid_spread + bid_adjustment) / Decimal(100))
        ask_price = mid_price * (Decimal(1) + (self.ask_spread + ask_adjustment) / Decimal(100))

        # 应用价格区间
        price_ceiling = self._get_effective_price_ceiling()
        price_floor = self._get_effective_price_floor()

        if price_ceiling is not None:
            ask_price = min(ask_price, price_ceiling)
        if price_floor is not None:
            bid_price = max(bid_price, price_floor)

        # Ping-Pong 模式
        if self.ping_pong_enabled:
            if self._ping_pong_state == 'buy':
                proposals.append({
                    'buy': {'price': bid_price, 'size': self.order_amount},
                    'sell': None
                })
            else:
                proposals.append({
                    'buy': None,
                    'sell': {'price': ask_price, 'size': self.order_amount}
                })
        else:
            # 正常模式
            proposals.append({
                'buy': {'price': bid_price, 'size': self.order_amount},
                'sell': {'price': ask_price, 'size': self.order_amount}
            })

        # 多级订单
        if self.order_levels > 1 and not self.ping_pong_enabled:
            for level in range(1, self.order_levels):
                level_bid_price = bid_price * (Decimal(1) - self.order_level_spread * level / Decimal(100))
                level_ask_price = ask_price * (Decimal(1) + self.order_level_spread * level / Decimal(100))

                level_size = self.order_amount + (self.order_level_amount * level)

                proposals.append({
                    'buy': {'price': level_bid_price, 'size': level_size},
                    'sell': {'price': level_ask_price, 'size': level_size}
                })

        return proposals

    def _calculate_inventory_skew_adjustment(self) -> tuple:
        """计算库存偏差调整"""
        try:
            balance = asyncio.create_task(self.get_balance_callback()).result() if self.get_balance_callback else {}
            base_balance = Decimal(str(balance.get(self.trading_pair.split('-')[0], 0)))
            quote_balance = Decimal(str(balance.get(self.trading_pair.split('-')[1], 0)))

            if quote_balance == 0:
                return Decimal(0), Decimal(0)

            current_base_pct = base_balance * self.inventory_price / quote_balance
            deviation = (current_base_pct - self.inventory_target_base_pct) / self.inventory_range_multiplier

            # 调整价差
            bid_adjustment = max(Decimal(0), deviation)  # 增加买单价（更接近中间价）
            ask_adjustment = max(Decimal(0), -deviation)  # 减少卖单价（更接近中间价）

            return bid_adjustment, ask_adjustment

        except Exception as e:
            self.logger.error(f"计算库存偏差调整失败: {e}")
            return Decimal(0), Decimal(0)

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

    async def _place_orders(self, proposal: Dict):
        """下订单"""
        try:
            # 买单
            if proposal.get('buy'):
                if await self.risk_manager.can_create_order(proposal['buy']['size'], proposal['buy']['price']):
                    buy_order_id = await self.create_order_callback(
                        self.trading_pair, 'buy',
                        float(proposal['buy']['size']),
                        float(proposal['buy']['price']),
                        'limit'
                    )
                    if buy_order_id:
                        self.logger.info(f"买单下单成功: {proposal['buy']['price']} x {proposal['buy']['size']}")

            # 卖单
            if proposal.get('sell'):
                if await self.risk_manager.can_create_order(proposal['sell']['size'], proposal['sell']['price']):
                    sell_order_id = await self.create_order_callback(
                        self.trading_pair, 'sell',
                        float(proposal['sell']['size']),
                        float(proposal['sell']['price']),
                        'limit'
                    )
                    if sell_order_id:
                        self.logger.info(f"卖单下单成功: {proposal['sell']['price']} x {proposal['sell']['size']}")

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

    def on_order_filled(self, event: Dict):
        """订单成交回调"""
        super().on_order_filled(event)

        self._last_fill_time = datetime.now().timestamp()

        # Ping-Pong 模式切换
        if self.ping_pong_enabled:
            if event.get('side') == 'buy':
                self._ping_pong_state = 'sell'
            else:
                self._ping_pong_state = 'buy'

            self.logger.info(f"Ping-Pong 模式切换到: {self._ping_pong_state}")

    def get_status(self) -> Dict:
        """获取策略状态"""
        return {
            "strategy": "pure_market_making",
            "trading_pair": self.trading_pair,
            "order_amount": str(self.order_amount),
            "bid_spread": str(self.bid_spread),
            "ask_spread": str(self.ask_spread),
            "order_levels": self.order_levels,
            "ping_pong_enabled": self.ping_pong_enabled,
            "ping_pong_state": self._ping_pong_state if self.ping_pong_enabled else None,
            "inventory_skew_enabled": self.inventory_skew_enabled,
            "inventory_target_base_pct": str(self.inventory_target_base_pct),
            "moving_price_band_enabled": self.moving_price_band_enabled,
            "is_running": self.is_running
        }
