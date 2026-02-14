"""
跨交易所挖矿策略 (Cross-Exchange Mining)
基于 Hummingbot 的 cross_exchange_mining 策略
在多个交易所提供流动性以赚取挖矿奖励
"""
import asyncio
import logging
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime

from ..core.strategy import StrategyBase
from ..core.position import PositionSide
from ..core.event_bus import EventBus


class CrossExchangeMiningStrategy(StrategyBase):
    """
    跨交易所挖矿策略

    原理：
    - 在多个交易所同时提供流动性
    - 利用每个交易所的挖矿奖励机制
    - 自动调整资金分配

    特性：
    - 多交易所同时挖矿
    - 资金分配优化
    - 风险分散
    - 收益追踪
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
        self.exchanges_config = config.get('exchanges', [
            {
                'name': 'binance',
                'trading_pair': 'BTC-USDT',
                'weight': 0.5,
                'maker_fee': 0.001
            },
            {
                'name': 'okx',
                'trading_pair': 'BTC-USDT',
                'weight': 0.5,
                'maker_fee': 0.001
            }
        ])

        # 代币配置
        self.base_asset = config.get('base_asset', 'BTC')
        self.quote_asset = config.get('quote_asset', 'USDT')

        # 订单配置
        self.total_order_amount = Decimal(str(config.get('total_order_amount', 0.002)))

        # 价差配置
        self.spread = Decimal(str(config.get('spread', 0.001)))

        # 订单刷新
        self.order_refresh_time = config.get('order_refresh_time', 30)
        self.max_order_age = config.get('max_order_age', 1800)

        # 挖矿奖励配置
        self.mining_rewards = {}  # 每个交易所的挖矿奖励

        # 内部状态
        self._exchange_orders = {exc['name']: {} for exc in self.exchanges_config}
        self._last_order_refresh_time = {exc['name']: 0 for exc in self.exchanges_config}
        self._exchange_balances = {}

        self.logger.info(f"跨交易所挖矿策略初始化:")
        for exc in self.exchanges_config:
            self.logger.info(f"  {exc['name']}: {exc['trading_pair']} (权重: {exc['weight']:.2%})")

    async def on_tick(self, ticker: Dict):
        """价格更新回调"""
        await super().on_tick(ticker)

        current_time = datetime.now().timestamp()

        # 更新各交易所余额
        await self._update_balances()

        # 遍历所有交易所
        for exc_config in self.exchanges_config:
            exchange_name = exc_config['name']
            trading_pair = exc_config['trading_pair']

            # 获取该交易所的价格
            exchange_ticker = ticker.get(exchange_name, ticker)

            # 检查订单刷新
            if current_time - self._last_order_refresh_time[exchange_name] > self.order_refresh_time:
                await self._refresh_exchange_orders(exchange_name, trading_pair, exchange_ticker)

    async def _update_balances(self):
        """更新各交易所余额"""
        try:
            balance = await self.get_balance_callback() if self.get_balance_callback else {}
            self._exchange_balances = balance

        except Exception as e:
            self.logger.error(f"更新余额失败: {e}")

    def _calculate_exchange_order_amount(self, exchange_name: str) -> Decimal:
        """计算该交易所的订单金额"""
        exc_config = next((exc for exc in self.exchanges_config if exc['name'] == exchange_name), None)
        if not exc_config:
            return Decimal(0)

        weight = Decimal(str(exc_config['weight']))
        return self.total_order_amount * weight

    async def _refresh_exchange_orders(self, exchange_name: str, trading_pair: str, ticker: Dict):
        """刷新指定交易所的订单"""
        try:
            mid_price = ticker.get('last', ticker.get('bid', 0))
            if mid_price == 0:
                return

            # 计算订单价格
            bid_price = mid_price * (Decimal(1) - self.spread)
            ask_price = mid_price * (Decimal(1) + self.spread)

            # 计算订单金额
            order_amount = self._calculate_exchange_order_amount(exchange_name)

            # 取消现有订单
            await self._cancel_exchange_orders(exchange_name)

            # 提交新订单
            await self._place_exchange_orders(exchange_name, trading_pair, bid_price, ask_price, order_amount)

            self._last_order_refresh_time[exchange_name] = datetime.now().timestamp()

        except Exception as e:
            self.logger.error(f"刷新交易所订单失败 [{exchange_name}]: {e}")

    async def _place_exchange_orders(self, exchange_name: str, trading_pair: str,
                                    bid_price: Decimal, ask_price: Decimal, order_amount: Decimal):
        """下指定交易所的订单"""
        try:
            exchange_pair = f"{exchange_name}:{trading_pair}"

            # 买单
            if await self.risk_manager.can_create_order(order_amount, bid_price):
                buy_order_id = await self.create_order_callback(
                    exchange_pair,
                    'buy',
                    float(order_amount),
                    float(bid_price),
                    'limit'
                )
                if buy_order_id:
                    self._exchange_orders[exchange_name][buy_order_id] = {
                        'side': 'buy',
                        'price': bid_price,
                        'size': order_amount,
                        'status': 'open',
                        'created_at': datetime.now().timestamp()
                    }
                    self.logger.info(f"买单 [{exchange_name}]: {bid_price} x {order_amount}")

            # 卖单
            if await self.risk_manager.can_create_order(order_amount, ask_price):
                sell_order_id = await self.create_order_callback(
                    exchange_pair,
                    'sell',
                    float(order_amount),
                    float(ask_price),
                    'limit'
                )
                if sell_order_id:
                    self._exchange_orders[exchange_name][sell_order_id] = {
                        'side': 'sell',
                        'price': ask_price,
                        'size': order_amount,
                        'status': 'open',
                        'created_at': datetime.now().timestamp()
                    }
                    self.logger.info(f"卖单 [{exchange_name}]: {ask_price} x {order_amount}")

        except Exception as e:
            self.logger.error(f"下交易所订单失败 [{exchange_name}]: {e}")

    async def _cancel_exchange_orders(self, exchange_name: str):
        """取消指定交易所的订单"""
        try:
            for order_id in list(self._exchange_orders.get(exchange_name, {}).keys()):
                await self.cancel_order_callback(order_id)
                self._exchange_orders[exchange_name].pop(order_id, None)
        except Exception as e:
            self.logger.error(f"取消交易所订单失败 [{exchange_name}]: {e}")

    async def _run_loop(self):
        """策略主循环"""
        while self.is_running:
            try:
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"跨交易所挖矿策略主循环错误: {e}")

    async def on_order_book(self, order_book: Dict):
        """订单簿更新回调"""
        # 跨交易所挖矿策略主要使用ticker数据，订单簿回调暂不处理
        # 可以在未来扩展为使用订单簿数据
        pass

    def get_status(self) -> Dict:
        """获取策略状态"""
        exchange_status = {}
        for exc in self.exchanges_config:
            exchange_name = exc['name']
            exchange_status[exchange_name] = {
                'trading_pair': exc['trading_pair'],
                'weight': exc['weight'],
                'orders_count': len(self._exchange_orders.get(exchange_name, {})),
                'order_amount': str(self._calculate_exchange_order_amount(exchange_name))
            }

        return {
            "strategy": "cross_exchange_mining",
            "base_asset": self.base_asset,
            "quote_asset": self.quote_asset,
            "total_order_amount": str(self.total_order_amount),
            "spread": str(self.spread),
            "exchanges": exchange_status,
            "total_orders": sum(len(orders) for orders in self._exchange_orders.values()),
            "is_running": self.is_running
        }
