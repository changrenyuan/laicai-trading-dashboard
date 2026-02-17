"""
流动性挖矿策略 (Liquidity Mining)
基于 Hummingbot 的 liquidity_mining 策略
为多个市场提供流动性以赚取挖矿奖励
"""
import asyncio
import logging
import numpy as np
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime

from ..core.strategy import StrategyBase
from ..core.position import PositionSide
from ..core.event_bus import EventBus
from typing import Tuple


class LiquidityMiningStrategy(StrategyBase):
    """
    流动性挖矿策略

    原理：
    - 在多个市场提供流动性
    - 根据市场波动率动态调整价差
    - 维持目标库存比例
    - 赚取流动性挖矿奖励

    特性：
    - 多市场同时做市
    - 波动率自适应价差
    - 库存偏差管理
    - 最大价差限制
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
        self.exchange = config.get('exchange', 'okx')
        self.markets = config.get('markets', ['BTC-USDT', 'ETH-USDT'])  # 支持多市场

        # 代币配置
        self.token = config.get('token', 'BTC')  # 提供流动性的代币

        # 订单配置
        self.order_amount = Decimal(str(config.get('order_amount', 0.001)))
        self.spread = Decimal(str(config.get('spread', 0.001)))

        # 订单刷新
        self.order_refresh_time = config.get('order_refresh_time', 30)
        self.order_refresh_tolerance_pct = Decimal(str(config.get('order_refresh_tolerance_pct', -1)))
        self.max_order_age = config.get('max_order_age', 1800)

        # 库存管理
        self.inventory_skew_enabled = config.get('inventory_skew_enabled', True)
        self.target_base_pct = Decimal(str(config.get('target_base_pct', 0.5)))
        self.inventory_range_multiplier = Decimal(str(config.get('inventory_range_multiplier', 0.1)))

        # 波动率配置
        self.volatility_interval = config.get('volatility_interval', 300)  # 5分钟
        self.avg_volatility_period = config.get('avg_volatility_period', 10)
        self.volatility_to_spread_multiplier = Decimal(str(config.get('volatility_to_spread_multiplier', 10)))
        self.max_spread = Decimal(str(config.get('max_spread', 0.01)))

        # 内部状态
        self._market_orders = {market: {} for market in self.markets}
        self._market_volatility = {market: 0.01 for market in self.markets}
        self._price_history = {market: [] for market in self.markets}
        self._last_order_refresh_time = {market: 0 for market in self.markets}

        self.logger.info(f"流动性挖矿策略初始化:")
        self.logger.info(f"  交易所: {self.exchange}")
        self.logger.info(f"  市场: {', '.join(self.markets)}")
        self.logger.info(f"  代币: {self.token}")

    async def on_tick(self, ticker: Dict):
        """价格更新回调"""
        await super().on_tick(ticker)

        current_time = datetime.now().timestamp()

        # 遍历所有市场
        for market in self.markets:
            market_ticker = ticker.get(market, ticker)

            # 更新价格历史
            current_price = market_ticker.get('last', market_ticker.get('bid', 0))
            if current_price > 0:
                self._price_history[market].append(Decimal(str(current_price)))
                if len(self._price_history[market]) > 100:
                    self._price_history[market].pop(0)

            # 计算波动率
            self._calculate_market_volatility(market)

            # 检查订单刷新
            if current_time - self._last_order_refresh_time[market] > self.order_refresh_time:
                await self._refresh_market_orders(market, market_ticker)

    def _calculate_market_volatility(self, market: str):
        """计算市场波动率"""
        history = self._price_history.get(market, [])
        if len(history) < 2:
            return

        # 计算收益率
        returns = []
        for i in range(1, len(history)):
            ret = float((history[i] - history[i-1]) / history[i-1])
            returns.append(ret)

        # 计算波动率
        if len(returns) > 0:
            volatility = np.std(returns[-self.avg_volatility_period:]) if len(returns) >= self.avg_volatility_period else np.std(returns)
            self._market_volatility[market] = max(0.001, min(volatility, 0.1))
        else:
            self._market_volatility[market] = 0.01

    def _calculate_market_spread(self, market: str) -> Decimal:
        """根据波动率计算价差"""
        base_spread = self.spread
        volatility_adjustment = Decimal(str(self._market_volatility[market])) * self.volatility_to_spread_multiplier

        market_spread = base_spread + volatility_adjustment

        # 限制最大价差
        if self.max_spread > 0:
            market_spread = min(market_spread, self.max_spread)

        return market_spread

    def _calculate_inventory_adjustment(self, market: str) -> Tuple[Decimal, Decimal]:
        """计算库存调整"""
        if not self.inventory_skew_enabled:
            return Decimal(0), Decimal(0)

        try:
            # 获取当前库存
            balance = asyncio.create_task(self.get_balance_callback()).result() if self.get_balance_callback else {}
            base_asset = market.split('-')[0]
            quote_asset = market.split('-')[1]

            base_balance = Decimal(str(balance.get(base_asset, 0)))
            quote_balance = Decimal(str(balance.get(quote_asset, 0)))

            if quote_balance == 0:
                return Decimal(0), Decimal(0)

            current_base_pct = base_balance / quote_balance
            deviation = (current_base_pct - self.target_base_pct) / self.inventory_range_multiplier

            bid_adjustment = max(Decimal(0), deviation)
            ask_adjustment = max(Decimal(0), -deviation)

            return bid_adjustment, ask_adjustment

        except Exception as e:
            self.logger.error(f"计算库存调整失败 [{market}]: {e}")
            return Decimal(0), Decimal(0)

    async def _refresh_market_orders(self, market: str, ticker: Dict):
        """刷新指定市场的订单"""
        try:
            mid_price = ticker.get('last', ticker.get('bid', 0))
            if mid_price == 0:
                return

            # 计算价差
            market_spread = self._calculate_market_spread(market)
            bid_adjustment, ask_adjustment = self._calculate_inventory_adjustment(market)

            # 计算订单价格
            bid_spread = market_spread + bid_adjustment
            ask_spread = market_spread + ask_adjustment

            bid_price = mid_price * (Decimal(1) - bid_spread)
            ask_price = mid_price * (Decimal(1) + ask_spread)

            # 取消现有订单
            await self._cancel_market_orders(market)

            # 提交新订单
            await self._place_market_orders(market, bid_price, ask_price)

            self._last_order_refresh_time[market] = datetime.now().timestamp()

        except Exception as e:
            self.logger.error(f"刷新市场订单失败 [{market}]: {e}")

    async def _place_market_orders(self, market: str, bid_price: Decimal, ask_price: Decimal):
        """下指定市场的订单"""
        try:
            market_pair = f"{self.exchange}:{market}"

            # 买单
            if await self.risk_manager.can_create_order(self.order_amount, bid_price):
                buy_order_id = await self.create_order_callback(
                    market_pair,
                    'buy',
                    float(self.order_amount),
                    float(bid_price),
                    'limit'
                )
                if buy_order_id:
                    self._market_orders[market][buy_order_id] = {
                        'side': 'buy',
                        'price': bid_price,
                        'size': self.order_amount,
                        'status': 'open',
                        'created_at': datetime.now().timestamp()
                    }
                    self.logger.info(f"买单 [{market}]: {bid_price} x {self.order_amount}")

            # 卖单
            if await self.risk_manager.can_create_order(self.order_amount, ask_price):
                sell_order_id = await self.create_order_callback(
                    market_pair,
                    'sell',
                    float(self.order_amount),
                    float(ask_price),
                    'limit'
                )
                if sell_order_id:
                    self._market_orders[market][sell_order_id] = {
                        'side': 'sell',
                        'price': ask_price,
                        'size': self.order_amount,
                        'status': 'open',
                        'created_at': datetime.now().timestamp()
                    }
                    self.logger.info(f"卖单 [{market}]: {ask_price} x {self.order_amount}")

        except Exception as e:
            self.logger.error(f"下市场订单失败 [{market}]: {e}")

    async def _cancel_market_orders(self, market: str):
        """取消指定市场的订单"""
        try:
            for order_id in list(self._market_orders.get(market, {}).keys()):
                await self.cancel_order_callback(order_id)
                self._market_orders[market].pop(order_id, None)
        except Exception as e:
            self.logger.error(f"取消市场订单失败 [{market}]: {e}")

    async def _run_loop(self):
        """策略主循环"""
        while self.is_running:
            try:
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"流动性挖矿策略主循环错误: {e}")

    async def on_order_book(self, order_book: Dict):
        """订单簿更新回调"""
        # 流动性挖矿策略主要使用ticker数据，订单簿回调暂不处理
        # 可以在未来扩展为使用订单簿数据
        pass

    def get_status(self) -> Dict:
        """获取策略状态"""
        return {
            "strategy": "liquidity_mining",
            "exchange": self.exchange,
            "markets": self.markets,
            "token": self.token,
            "order_amount": str(self.order_amount),
            "spread": str(self.spread),
            "inventory_skew_enabled": self.inventory_skew_enabled,
            "target_base_pct": str(self.target_base_pct),
            "max_spread": str(self.max_spread),
            "market_volatility": {market: f"{vol:.4f}" for market, vol in self._market_volatility.items()},
            "total_orders": sum(len(orders) for orders in self._market_orders.values()),
            "is_running": self.is_running
        }
