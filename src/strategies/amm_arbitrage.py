"""
AMM 套利策略 (AMM Arbitrage)
基于 Hummingbot 的 amm_arb 策略
在两个市场之间进行套利交易
"""
import asyncio
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from ..core.strategy import StrategyBase
from ..core.position import PositionSide
from ..core.event_bus import EventBus


@dataclass
class ArbitrageOpportunity:
    """套利机会"""
    buy_market: str
    sell_market: str
    buy_price: Decimal
    sell_price: Decimal
    order_amount: Decimal
    expected_profit_pct: Decimal
    profit_amount: Decimal


class AMMArbitrageStrategy(StrategyBase):
    """
    AMM 套利策略

    原理：
    - 在两个市场（通常是 CEX 和 AMM DEX）之间寻找价差
    - 在价格低的市场买入，在价格高的市场卖出
    - 考虑滑点、Gas 费用等因素

    特性：
    - 支持并发提交订单
    - 支持滑点缓冲
    - 支持最小利润目标
    - 支持 Gas 费用计算
    """

    def __init__(
        self,
        event_bus: EventBus,
        position_manager,
        risk_manager,
        config: Dict
    ):
        super().__init__(event_bus, position_manager, risk_manager, config)

        # 调试日志
        self.logger.info("AMMArbitrageStrategy __init__ called (updated version)")

        # 市场配置
        self.market_1 = config.get('market_1', 'okx')
        self.market_2 = config.get('market_2', 'uniswap')
        self.trading_pair_1 = config.get('trading_pair_1', 'BTC-USDT')
        self.trading_pair_2 = config.get('trading_pair_2', 'BTC-ETH')

        # 订单配置
        self.order_amount = Decimal(str(config.get('order_amount', 0.001)))

        # 套利阈值
        self.min_profitability = Decimal(str(config.get('min_profitability', 0.001)))  # 最小利润百分比

        # 滑点缓冲
        self.market_1_slippage_buffer = Decimal(str(config.get('market_1_slippage_buffer', 0.001)))
        self.market_2_slippage_buffer = Decimal(str(config.get('market_2_slippage_buffer', 0.001)))

        # 并发提交订单
        self.concurrent_orders_submission = config.get('concurrent_orders_submission', True)

        # 汇率配置
        self.rate_oracle_enabled = config.get('rate_oracle_enabled', True)
        self.quote_conversion_rate = Decimal(str(config.get('quote_conversion_rate', 1.0)))

        # Gas 费用配置（用于区块链交易）
        self.gas_token = config.get('gas_token', 'ETH')
        self.gas_price = Decimal(str(config.get('gas_price', 2000)))

        # 策略状态
        self._is_opening_position = False
        self._is_closing_position = False
        self._opening_order_ids = []
        self._last_arbitrage_time = 0
        self._arbitrage_cooldown = config.get('arbitrage_cooldown', 60)

        self.logger.info(f"AMM 套利策略初始化:")
        self.logger.info(f"  市场1: {self.market_1}:{self.trading_pair_1}")
        self.logger.info(f"  市场2: {self.market_2}:{self.trading_pair_2}")
        self.logger.info(f"  最小利润: {self.min_profitability:.2%}")

    async def on_tick(self, ticker: Dict):
        """价格更新回调"""
        await super().on_tick(ticker)

        current_time = datetime.now().timestamp()

        # 如果正在开仓或平仓，跳过
        if self._is_opening_position or self._is_closing_position:
            return

        # 冷却时间
        if current_time - self._last_arbitrage_time < self._arbitrage_cooldown:
            return

        # 检查套利机会
        opportunity = await self._check_arbitrage_opportunity(ticker)
        if opportunity:
            await self._execute_arbitrage(opportunity)

    async def _check_arbitrage_opportunity(self, ticker: Dict) -> Optional[ArbitrageOpportunity]:
        """检查套利机会"""
        try:
            # 获取两个市场的价格（这里简化处理）
            price_1 = Decimal(str(ticker.get('price_1', ticker.get('last', 0))))
            price_2 = Decimal(str(ticker.get('price_2', ticker.get('last', 0))))

            if price_1 == 0 or price_2 == 0:
                return None

            # 情况1: 市场1买 + 市场2卖
            if price_1 < price_2:
                profit_pct = (price_2 - price_1) / price_1
                if profit_pct >= self.min_profitability:
                    # 计算实际利润（考虑滑点和费用）
                    adjusted_buy_price = price_1 * (Decimal(1) + self.market_1_slippage_buffer)
                    adjusted_sell_price = price_2 * (Decimal(1) - self.market_2_slippage_buffer)
                    actual_profit_pct = (adjusted_sell_price - adjusted_buy_price) / adjusted_buy_price

                    # 考虑 Gas 费用（如果是区块链交易）
                    gas_cost = self._calculate_gas_cost()
                    profit_amount = (adjusted_sell_price - adjusted_buy_price) * self.order_amount - gas_cost

                    if actual_profit_pct >= self.min_profitability:
                        return ArbitrageOpportunity(
                            buy_market=self.market_1,
                            sell_market=self.market_2,
                            buy_price=adjusted_buy_price,
                            sell_price=adjusted_sell_price,
                            order_amount=self.order_amount,
                            expected_profit_pct=actual_profit_pct,
                            profit_amount=profit_amount
                        )

            # 情况2: 市场2买 + 市场1卖
            elif price_2 < price_1:
                profit_pct = (price_1 - price_2) / price_2
                if profit_pct >= self.min_profitability:
                    adjusted_buy_price = price_2 * (Decimal(1) + self.market_2_slippage_buffer)
                    adjusted_sell_price = price_1 * (Decimal(1) - self.market_1_slippage_buffer)
                    actual_profit_pct = (adjusted_sell_price - adjusted_buy_price) / adjusted_buy_price

                    gas_cost = self._calculate_gas_cost()
                    profit_amount = (adjusted_sell_price - adjusted_buy_price) * self.order_amount - gas_cost

                    if actual_profit_pct >= self.min_profitability:
                        return ArbitrageOpportunity(
                            buy_market=self.market_2,
                            sell_market=self.market_1,
                            buy_price=adjusted_buy_price,
                            sell_price=adjusted_sell_price,
                            order_amount=self.order_amount,
                            expected_profit_pct=actual_profit_pct,
                            profit_amount=profit_amount
                        )

        except Exception as e:
            self.logger.error(f"检查套利机会失败: {e}")

        return None

    def _calculate_gas_cost(self) -> Decimal:
        """计算 Gas 成本"""
        # 简化处理，实际需要根据链上 Gas 价格计算
        if self.gas_token == 'ETH':
            # 假设 Gas 价格为 2000 USDC
            return self.gas_price
        return Decimal(0)

    async def _execute_arbitrage(self, opportunity: ArbitrageOpportunity):
        """执行套利"""
        self._is_opening_position = True
        self._last_arbitrage_time = datetime.now().timestamp()

        self.logger.info(f"发现套利机会:")
        self.logger.info(f"  买入 {opportunity.buy_market}: {opportunity.buy_price}")
        self.logger.info(f"  卖出 {opportunity.sell_market}: {opportunity.sell_price}")
        self.logger.info(f"  预期利润: {opportunity.expected_profit_pct:.4%}")

        try:
            if self.concurrent_orders_submission:
                # 并发提交订单
                buy_order_id = await self._create_buy_order(opportunity)
                sell_order_id = await self._create_sell_order(opportunity)

                self._opening_order_ids = [buy_order_id, sell_order_id]
            else:
                # 串行提交订单（先买后卖）
                buy_order_id = await self._create_buy_order(opportunity)
                self._opening_order_ids = [buy_order_id]

                # 等待买单成交
                await asyncio.sleep(2)

                # 提交卖单
                sell_order_id = await self._create_sell_order(opportunity)
                self._opening_order_ids.append(sell_order_id)

            # 发布套利事件
            await self.event_bus.publish("arbitrage_executed", {
                "buy_market": opportunity.buy_market,
                "sell_market": opportunity.sell_market,
                "profit_amount": str(opportunity.profit_amount),
                "profit_pct": str(opportunity.expected_profit_pct)
            })

        except Exception as e:
            self.logger.error(f"执行套利失败: {e}")
        finally:
            self._is_opening_position = False

    async def _create_buy_order(self, opportunity: ArbitrageOpportunity) -> str:
        """创建买单"""
        market_pair = f"{opportunity.buy_market}:{self.trading_pair_1 if opportunity.buy_market == self.market_1 else self.trading_pair_2}"

        order_id = await self.create_order_callback(
            market_pair,
            'buy',
            float(opportunity.order_amount),
            float(opportunity.buy_price),
            'limit'
        )

        if order_id:
            self.logger.info(f"买单已提交: {opportunity.buy_market} @ {opportunity.buy_price}")

        return order_id or ""

    async def _create_sell_order(self, opportunity: ArbitrageOpportunity) -> str:
        """创建卖单"""
        market_pair = f"{opportunity.sell_market}:{self.trading_pair_1 if opportunity.sell_market == self.market_1 else self.trading_pair_2}"

        order_id = await self.create_order_callback(
            market_pair,
            'sell',
            float(opportunity.order_amount),
            float(opportunity.sell_price),
            'limit'
        )

        if order_id:
            self.logger.info(f"卖单已提交: {opportunity.sell_market} @ {opportunity.sell_price}")

        return order_id or ""

    async def _run_loop(self):
        """策略主循环"""
        while self.is_running:
            try:
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"AMM套利策略主循环错误: {e}")

    async def on_order_book(self, order_book: Dict):
        """订单簿更新回调"""
        # AMM套利策略主要使用ticker数据，订单簿回调暂不处理
        # 可以在未来扩展为使用订单簿数据
        pass

    def get_status(self) -> Dict:
        """获取策略状态"""
        return {
            "strategy": "amm_arbitrage",
            "market_1": self.market_1,
            "market_2": self.market_2,
            "trading_pair_1": self.trading_pair_1,
            "trading_pair_2": self.trading_pair_2,
            "order_amount": str(self.order_amount),
            "min_profitability": str(self.min_profitability),
            "concurrent_orders_submission": self.concurrent_orders_submission,
            "is_opening_position": self._is_opening_position,
            "is_running": self.is_running
        }
