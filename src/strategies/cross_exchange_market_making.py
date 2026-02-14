"""
跨交易所做市策略 (Cross-Exchange Market Making)
基于 Hummingbot 的 cross_exchange_market_making 策略
在两个交易所之间进行做市
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
class CrossExchangePosition:
    """跨交易所仓位"""
    maker_market: str
    taker_market: str
    trading_pair: str
    size: Decimal
    entry_price: Decimal
    is_open: bool


class CrossExchangeMarketMakingStrategy(StrategyBase):
    """
    跨交易所做市策略

    原理：
    - 在 Maker 交易所（费用低）挂单提供流动性
    - 在 Taker 交易所（费用高）对冲风险
    - 利用两个交易所的价差获利

    特性：
    - 双交易所协同做市
    - 自动风险对冲
    - 费用优化
    - 库存同步
    """

    def __init__(
        self,
        event_bus: EventBus,
        position_manager,
        risk_manager,
        config: Dict
    ):
        super().__init__(event_bus, position_manager, risk_manager, config)

        # 交易所配置
        self.maker_market = config.get('maker_market', 'binance')
        self.taker_market = config.get('taker_market', 'okx')
        self.trading_pair = config.get('trading_pair', 'BTC-USDT')

        # 订单配置
        self.order_amount = Decimal(str(config.get('order_amount', 0.001)))
        self.min_profitability = Decimal(str(config.get('min_profitability', 0.001)))

        # 价差配置
        self.bid_spread = Decimal(str(config.get('bid_spread', 0.001)))
        self.ask_spread = Decimal(str(config.get('ask_spread', 0.001)))

        # 订单刷新
        self.order_refresh_time = config.get('order_refresh_time', 30)
        self.order_refresh_tolerance_pct = Decimal(str(config.get('order_refresh_tolerance_pct', -1)))

        # 对冲配置
        self.auto_hedge_enabled = config.get('auto_hedge_enabled', True)
        self.hedge_ratio = Decimal(str(config.get('hedge_ratio', 1.0)))
        self.hedge_delay = config.get('hedge_delay', 1)  # 秒

        # 费用配置
        self.maker_fee = Decimal(str(config.get('maker_fee', 0.001)))  # 0.1%
        self.taker_fee = Decimal(str(config.get('taker_fee', 0.001)))  # 0.1%

        # 内部状态
        self._maker_orders = {}  # Maker 交易所订单
        self._taker_positions = []  # Taker 交易所仓位
        self._last_order_refresh_time = 0
        self._inventory_imbalance = Decimal(0)

        self.logger.info(f"跨交易所做市策略初始化:")
        self.logger.info(f"  Maker 市场: {self.maker_market}:{self.trading_pair}")
        self.logger.info(f"  Taker 市场: {self.taker_market}:{self.trading_pair}")

    async def on_tick(self, ticker: Dict):
        """价格更新回调"""
        await super().on_tick(ticker)

        current_time = datetime.now().timestamp()

        # 检查订单刷新
        if current_time - self._last_order_refresh_time > self.order_refresh_time:
            await self._refresh_maker_orders(ticker)

    async def _refresh_maker_orders(self, ticker: Dict):
        """刷新 Maker 订单"""
        try:
            # 获取两个市场的价格
            maker_price = Decimal(str(ticker.get('maker_price', ticker.get('last', 0))))
            taker_price = Decimal(str(ticker.get('taker_price', ticker.get('last', 0))))

            if maker_price == 0 or taker_price == 0:
                return

            # 计算价差
            price_diff = abs(maker_price - taker_price) / maker_price

            # 如果价差小于最小利润，不挂单
            if price_diff < self.min_profitability:
                self.logger.debug(f"价差 {price_diff:.4%} 小于最小利润 {self.min_profitability:.4%}")
                return

            mid_price = (maker_price + taker_price) / 2

            # 计算订单价格
            bid_price = mid_price * (Decimal(1) - self.bid_spread)
            ask_price = mid_price * (Decimal(1) + self.ask_spread)

            # 取消现有 Maker 订单
            await self._cancel_maker_orders()

            # 提交新订单
            await self._place_maker_orders(bid_price, ask_price)

            self._last_order_refresh_time = datetime.now().timestamp()

        except Exception as e:
            self.logger.error(f"刷新 Maker 订单失败: {e}")

    async def _place_maker_orders(self, bid_price: Decimal, ask_price: Decimal):
        """下 Maker 订单"""
        try:
            maker_pair = f"{self.maker_market}:{self.trading_pair}"

            # 买单
            if await self.risk_manager.can_create_order(self.order_amount, bid_price):
                buy_order_id = await self.create_order_callback(
                    maker_pair,
                    'buy',
                    float(self.order_amount),
                    float(bid_price),
                    'limit'
                )
                if buy_order_id:
                    self._maker_orders[buy_order_id] = {
                        'side': 'buy',
                        'price': bid_price,
                        'size': self.order_amount,
                        'status': 'open'
                    }
                    self.logger.info(f"Maker 买单: {bid_price} x {self.order_amount}")

            # 卖单
            if await self.risk_manager.can_create_order(self.order_amount, ask_price):
                sell_order_id = await self.create_order_callback(
                    maker_pair,
                    'sell',
                    float(self.order_amount),
                    float(ask_price),
                    'limit'
                )
                if sell_order_id:
                    self._maker_orders[sell_order_id] = {
                        'side': 'sell',
                        'price': ask_price,
                        'size': self.order_amount,
                        'status': 'open'
                    }
                    self.logger.info(f"Maker 卖单: {ask_price} x {self.order_amount}")

        except Exception as e:
            self.logger.error(f"下 Maker 订单失败: {e}")

    async def _cancel_maker_orders(self):
        """取消所有 Maker 订单"""
        try:
            for order_id in list(self._maker_orders.keys()):
                await self.cancel_order_callback(order_id)
                self._maker_orders.pop(order_id, None)
        except Exception as e:
            self.logger.error(f"取消 Maker 订单失败: {e}")

    def on_order_filled(self, event: Dict):
        """订单成交回调"""
        super().on_order_filled(event)

        # 如果是 Maker 订单成交，自动在 Taker 市场对冲
        if self.auto_hedge_enabled:
            asyncio.create_task(self._hedge_position(event))

    async def _hedge_position(self, event: Dict):
        """对冲仓位"""
        try:
            side = event.get('side')
            filled_size = Decimal(str(event.get('size', 0)))

            if filled_size == 0:
                return

            # 等待延迟（可选，避免过度交易）
            if self.hedge_delay > 0:
                await asyncio.sleep(self.hedge_delay)

            # 在 Taker 市场下对冲订单
            taker_pair = f"{self.taker_market}:{self.trading_pair}"
            hedge_side = 'sell' if side == 'buy' else 'buy'
            hedge_size = filled_size * self.hedge_ratio

            # 使用市价单对冲
            order_id = await self.create_order_callback(
                taker_pair,
                hedge_side,
                float(hedge_size),
                0,  # 市价单
                'market'
            )

            if order_id:
                self.logger.info(f"Taker 对冲订单: {hedge_side} {hedge_size}")

                # 记录对冲仓位
                self._taker_positions.append({
                    'order_id': order_id,
                    'side': hedge_side,
                    'size': hedge_size,
                    'created_at': datetime.now().timestamp()
                })

        except Exception as e:
            self.logger.error(f"对冲仓位失败: {e}")

    async def _run_loop(self):
        """策略主循环"""
        while self.is_running:
            try:
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"跨交易所做市策略主循环错误: {e}")

    async def on_order_book(self, order_book: Dict):
        """订单簿更新回调"""
        # 跨交易所做市策略主要使用ticker数据，订单簿回调暂不处理
        # 可以在未来扩展为使用订单簿数据
        pass

    def get_status(self) -> Dict:
        """获取策略状态"""
        return {
            "strategy": "cross_exchange_market_making",
            "maker_market": self.maker_market,
            "taker_market": self.taker_market,
            "trading_pair": self.trading_pair,
            "order_amount": str(self.order_amount),
            "min_profitability": str(self.min_profitability),
            "bid_spread": str(self.bid_spread),
            "ask_spread": str(self.ask_spread),
            "auto_hedge_enabled": self.auto_hedge_enabled,
            "hedge_ratio": str(self.hedge_ratio),
            "maker_orders_count": len(self._maker_orders),
            "taker_positions_count": len(self._taker_positions),
            "is_running": self.is_running
        }
