"""
Avellaneda 做市策略 (Avellaneda Market Making)
基于 Hummingbot 的 avellaneda_market_making 策略
使用 Avellaneda-Stoikov 模型进行做市
"""
import asyncio
import logging
import numpy as np
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from ..core.strategy import StrategyBase
from ..core.position import PositionSide
from ..core.event_bus import EventBus


@dataclass
class AvellanedaParameters:
    """Avellaneda-Stoikov 模型参数"""
    risk_aversion: float  # 风险厌恶系数 (gamma)
    order_book_depth: float  # 订单簿深度 (kappa)
    inventory_target_base_pct: float  # 目标库存百分比
    min_spread: float  # 最小价差
    volatility: float  # 波动率


class AvellanedaMarketMakingStrategy(StrategyBase):
    """
    Avellaneda 做市策略

    原理：
    - 基于 Avellaneda-Stoikov 模型计算最优买卖价
    - 考虑库存风险、订单簿深度和波动性
    - 动态调整价差以平衡利润和风险

    公式：
    - 保留价 = s + gamma * q * sigma^2
    - 买价 = 保留价 - sigma * sqrt(gamma / kappa) * (1 / sqrt(1 - gamma))
    - 卖价 = 保留价 + sigma * sqrt(gamma / kappa) * (1 / sqrt(1 - gamma))

    其中：
    - s: 当前中间价
    - gamma: 风险厌恶系数
    - q: 当前库存（正数为多头，负数为空头）
    - sigma: 波动率
    - kappa: 订单簿深度参数

    特性：
    - 库存风险控制
    - 动态价差调整
    - 波动率自适应
    - 支持多级订单
    """

    def __init__(
        self,
        event_bus: EventBus,
        position_manager,
        risk_manager,
        config: Dict
    ):
        super().__init__(event_bus, position_manager, risk_manager, config)

        # 基础配置
        self.trading_pair = config.get('trading_pair', 'BTC-USDT')
        self.order_amount = Decimal(str(config.get('order_amount', 0.001)))

        # Avellaneda 参数
        self.risk_aversion = float(config.get('risk_aversion', 0.1))  # gamma
        self.order_book_depth = float(config.get('order_book_depth', 1.5))  # kappa
        self.inventory_target_base_pct = float(config.get('inventory_target_base_pct', 0.5))

        # 价差配置
        self.min_spread = Decimal(str(config.get('min_spread', 0.001)))
        self.max_spread = Decimal(str(config.get('max_spread', 0.01)))

        # 波动率配置
        self.volatility_interval = config.get('volatility_interval', 300)  # 5分钟
        self.volatility_history: List[float] = []
        self.current_volatility = 0.01

        # 订单配置
        self.order_levels = config.get('order_levels', 1)
        self.order_level_spread = Decimal(str(config.get('order_level_spread', 0.0005)))
        self.order_refresh_time = config.get('order_refresh_time', 30)

        # 内部状态
        self._last_order_refresh_time = 0
        self._price_history: List[Decimal] = []

        self.logger.info(f"Avellaneda 做市策略初始化: {self.trading_pair}")
        self.logger.info(f"  风险厌恶系数: {self.risk_aversion}")
        self.logger.info(f"  订单簿深度: {self.order_book_depth}")

    async def on_tick(self, ticker: Dict):
        """价格更新回调"""
        await super().on_tick(ticker)

        current_time = datetime.now().timestamp()

        # 记录价格用于计算波动率
        current_price = ticker.get('last', ticker.get('bid', 0))
        if current_price > 0:
            self._price_history.append(Decimal(str(current_price)))
            # 保留最近 100 个价格点
            if len(self._price_history) > 100:
                self._price_history.pop(0)

        # 计算波动率
        self._calculate_volatility()

        # 检查订单刷新
        if current_time - self._last_order_refresh_time > self.order_refresh_time:
            await self._refresh_orders(ticker)

    def _calculate_volatility(self):
        """计算波动率"""
        if len(self._price_history) < 2:
            return

        # 计算收益率
        returns = []
        for i in range(1, len(self._price_history)):
            ret = float((self._price_history[i] - self._price_history[i-1]) / self._price_history[i-1])
            returns.append(ret)

        # 计算波动率（标准差）
        if len(returns) > 0:
            self.current_volatility = np.std(returns) if returns else 0.01
        else:
            self.current_volatility = 0.01

        # 限制波动率范围
        self.current_volatility = max(0.001, min(self.current_volatility, 0.1))

    def _get_inventory_position(self) -> float:
        """获取库存位置"""
        try:
            # 获取当前库存
            inventory = asyncio.create_task(self.get_balance_callback()).result() if self.get_balance_callback else {}
            base_asset = self.trading_pair.split('-')[0]
            quote_asset = self.trading_pair.split('-')[1]

            base_balance = Decimal(str(inventory.get(base_asset, 0)))
            quote_balance = Decimal(str(inventory.get(quote_asset, 0)))

            if quote_balance == 0:
                return 0.0

            # 计算库存百分比
            inventory_pct = float(base_balance * Decimal(str(self._get_mid_price())) / quote_balance)
            return (inventory_pct - self.inventory_target_base_pct) * 2  # 归一化到 [-1, 1]

        except Exception as e:
            self.logger.error(f"计算库存位置失败: {e}")
            return 0.0

    def _get_mid_price(self) -> float:
        """获取中间价"""
        if not self._price_history:
            return 50000.0
        return float(self._price_history[-1])

    def _calculate_reservation_price(self, mid_price: float, inventory_q: float) -> float:
        """
        计算保留价

        公式: r = s + gamma * q * sigma^2
        """
        return mid_price + self.risk_aversion * inventory_q * (self.current_volatility ** 2)

    def _calculate_optimal_spread(self) -> float:
        """
        计算最优价差

        公式: delta = 2 * sigma * sqrt(gamma / kappa)
        """
        term1 = self.current_volatility ** 2
        term2 = self.risk_aversion / self.order_book_depth

        if term2 <= 0:
            return float(self.min_spread)

        spread = 2 * self.current_volatility * np.sqrt(term2)
        return max(float(self.min_spread), min(spread, float(self.max_spread)))

    def _calculate_order_prices(self, mid_price: float) -> List[Tuple[float, float]]:
        """
        计算订单价格

        返回: [(bid_price, ask_price), ...]
        """
        inventory_q = self._get_inventory_position()
        reservation_price = self._calculate_reservation_price(mid_price, inventory_q)
        optimal_spread = self._calculate_optimal_spread()

        # 计算买价和卖价
        base_spread = optimal_spread / 2

        prices = []

        for level in range(self.order_levels):
            level_adjustment = level * float(self.order_level_spread)

            bid_price = reservation_price - base_spread - level_adjustment
            ask_price = reservation_price + base_spread + level_adjustment

            # 确保价格为正
            bid_price = max(bid_price, mid_price * 0.5)
            ask_price = max(ask_price, mid_price * 1.5)

            prices.append((bid_price, ask_price))

        return prices

    async def _refresh_orders(self, ticker: Dict):
        """刷新订单"""
        try:
            mid_price = ticker.get('last', ticker.get('bid', 0))
            if mid_price == 0:
                return

            prices = self._calculate_order_prices(mid_price)

            # 取消现有订单
            await self._cancel_all_orders()

            # 提交新订单
            for level, (bid_price, ask_price) in enumerate(prices):
                level_size = self.order_amount * (1 + level * 0.1)  # 逐级增加订单量

                # 买单
                if await self.risk_manager.can_create_order(level_size, bid_price):
                    buy_order_id = await self.create_order_callback(
                        self.trading_pair, 'buy',
                        float(level_size),
                        float(bid_price),
                        'limit'
                    )
                    if buy_order_id:
                        self.logger.info(f"买单已提交 [Level {level}]: {bid_price:.2f} x {level_size}")

                # 卖单
                if await self.risk_manager.can_create_order(level_size, ask_price):
                    sell_order_id = await self.create_order_callback(
                        self.trading_pair, 'sell',
                        float(level_size),
                        float(ask_price),
                        'limit'
                    )
                    if sell_order_id:
                        self.logger.info(f"卖单已提交 [Level {level}]: {ask_price:.2f} x {level_size}")

            self._last_order_refresh_time = datetime.now().timestamp()

        except Exception as e:
            self.logger.error(f"刷新订单失败: {e}")

    async def _cancel_all_orders(self):
        """取消所有订单"""
        try:
            cancelled = await self.cancel_all_orders_callback()
            if cancelled > 0:
                self.logger.info(f"取消了 {cancelled} 个订单")
        except Exception as e:
            self.logger.error(f"取消订单失败: {e}")

    async def _run_loop(self):
        """策略主循环"""
        while self.is_running:
            try:
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"Avellaneda做市策略主循环错误: {e}")

    async def on_order_book(self, order_book: Dict):
        """订单簿更新回调"""
        # Avellaneda做市策略主要使用ticker数据，订单簿回调暂不处理
        # 可以在未来扩展为使用订单簿数据计算更精确的价格
        pass

    def get_status(self) -> Dict:
        """获取策略状态"""
        return {
            "strategy": "avellaneda_market_making",
            "trading_pair": self.trading_pair,
            "order_amount": str(self.order_amount),
            "risk_aversion": self.risk_aversion,
            "order_book_depth": self.order_book_depth,
            "current_volatility": f"{self.current_volatility:.4f}",
            "min_spread": str(self.min_spread),
            "max_spread": str(self.max_spread),
            "order_levels": self.order_levels,
            "is_running": self.is_running
        }
