"""
现货永续套利策略 (Spot-Perpetual Arbitrage)
基于 Hummingbot 的 spot_perpetual_arbitrage 策略
"""
import asyncio
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from ..core.strategy import StrategyBase
from ..core.position import PositionSide
from ..core.event_bus import EventBus


class StrategyState(Enum):
    """策略状态"""
    Closed = 0
    Opening = 1
    Opened = 2
    Closing = 3


@dataclass
class ArbProposal:
    """套利提案"""
    buy_market: str  # 'spot' or 'perp'
    sell_market: str
    buy_price: Decimal
    sell_price: Decimal
    order_amount: Decimal
    expected_profit_pct: Decimal


class SpotPerpetualArbitrageStrategy(StrategyBase):
    """
    现货永续套利策略

    原理：
    - 在现货和永续合约之间寻找价差
    - 低买高卖，同时持有现货和永续合约仓位对冲
    - 当价差缩小到目标水平时平仓

    特性：
    - 支持双向套利（现货买/永续卖，或 现货卖/永续买）
    - 支持滑点缓冲
    - 支持冷却时间
    """

    def __init__(
        self,
        event_bus: EventBus,
        position_manager,
        risk_manager,
        config: Dict
    ):
        super().__init__(event_bus, position_manager, risk_manager, config)

        # 市场配置
        self.spot_market = config.get('spot_market', 'okx')
        self.spot_trading_pair = config.get('spot_trading_pair', 'BTC-USDT')
        self.perp_market = config.get('perp_market', 'okx')
        self.perp_trading_pair = config.get('perp_trading_pair', 'BTC-USDT-SWAP')

        # 订单配置
        self.order_amount = Decimal(str(config.get('order_amount', 0.001)))
        self.perp_leverage = config.get('perp_leverage', 10)

        # 套利阈值
        self.min_opening_arbitrage_pct = Decimal(str(config.get('min_opening_arbitrage_pct', 0.001)))
        self.min_closing_arbitrage_pct = Decimal(str(config.get('min_closing_arbitrage_pct', 0.0005)))

        # 滑点缓冲
        self.spot_market_slippage_buffer = Decimal(str(config.get('spot_market_slippage_buffer', 0.001)))
        self.perp_market_slippage_buffer = Decimal(str(config.get('perp_market_slippage_buffer', 0.001)))

        # 冷却时间
        self.next_arbitrage_opening_delay = config.get('next_arbitrage_opening_delay', 120)

        # 策略状态
        self._strategy_state = StrategyState.Closed
        self._next_arbitrage_opening_ts = 0
        self._opening_order_ids = []
        self._closing_order_ids = []
        self._last_status_report_time = 0

        # 当前套利仓位
        self._current_arb_position = None

        self.logger.info(f"现货永续套利策略初始化:")
        self.logger.info(f"  现货: {self.spot_market}:{self.spot_trading_pair}")
        self.logger.info(f"  永续: {self.perp_market}:{self.perp_trading_pair}")
        self.logger.info(f"  杠杆: {self.perp_leverage}x")

    async def on_tick(self, ticker: Dict):
        """价格更新回调"""
        await super().on_tick(ticker)

        current_time = datetime.now().timestamp()

        # 定期报告状态
        if current_time - self._last_status_report_time > 30:
            await self._report_status()
            self._last_status_report_time = current_time

        # 根据状态执行逻辑
        if self._strategy_state == StrategyState.Closed:
            await self._check_for_arbitrage_opportunity(ticker, current_time)
        elif self._strategy_state == StrategyState.Opened:
            await self._check_for_closing_opportunity(ticker)

    def _get_spot_ticker(self, ticker: Dict) -> Dict:
        """获取现货行情"""
        # 如果 ticker 是 dict，需要区分现货和永续
        # 这里简化处理，实际需要分别获取
        return ticker.get('spot', ticker)

    def _get_perp_ticker(self, ticker: Dict) -> Dict:
        """获取永续行情"""
        return ticker.get('perp', ticker)

    async def _check_for_arbitrage_opportunity(self, ticker: Dict, current_time: float):
        """检查套利机会"""
        # 检查冷却时间
        if current_time < self._next_arbitrage_opening_ts:
            return

        try:
            spot_ticker = self._get_spot_ticker(ticker)
            perp_ticker = self._get_perp_ticker(ticker)

            spot_bid = Decimal(str(spot_ticker.get('bid', 0)))
            spot_ask = Decimal(str(spot_ticker.get('ask', 0)))
            perp_bid = Decimal(str(perp_ticker.get('bid', 0)))
            perp_ask = Decimal(str(perp_ticker.get('ask', 0)))

            if spot_bid == 0 or spot_ask == 0 or perp_bid == 0 or perp_ask == 0:
                return

            # 情况1: 现货买 + 永续卖（现货价格低于永续）
            if spot_ask < perp_bid:
                profit_pct = (perp_bid - spot_ask) / spot_ask
                if profit_pct >= self.min_opening_arbitrage_pct:
                    proposal = ArbProposal(
                        buy_market='spot',
                        sell_market='perp',
                        buy_price=spot_ask * (Decimal(1) + self.spot_market_slippage_buffer),
                        sell_price=perp_bid * (Decimal(1) - self.perp_market_slippage_buffer),
                        order_amount=self.order_amount,
                        expected_profit_pct=profit_pct
                    )
                    await self._open_arbitrage_position(proposal)
                    return

            # 情况2: 现货卖 + 永续买（现货价格高于永续）
            if spot_bid > perp_ask:
                profit_pct = (spot_bid - perp_ask) / perp_ask
                if profit_pct >= self.min_opening_arbitrage_pct:
                    proposal = ArbProposal(
                        buy_market='perp',
                        sell_market='spot',
                        buy_price=perp_ask * (Decimal(1) + self.perp_market_slippage_buffer),
                        sell_price=spot_bid * (Decimal(1) - self.spot_market_slippage_buffer),
                        order_amount=self.order_amount,
                        expected_profit_pct=profit_pct
                    )
                    await self._open_arbitrage_position(proposal)
                    return

        except Exception as e:
            self.logger.error(f"检查套利机会失败: {e}")

    async def _check_for_closing_opportunity(self, ticker: Dict):
        """检查平仓机会"""
        if not self._current_arb_position:
            return

        try:
            spot_ticker = self._get_spot_ticker(ticker)
            perp_ticker = self._get_perp_ticker(ticker)

            spot_bid = Decimal(str(spot_ticker.get('bid', 0)))
            spot_ask = Decimal(str(spot_ticker.get('ask', 0)))
            perp_bid = Decimal(str(perp_ticker.get('bid', 0)))
            perp_ask = Decimal(str(perp_ticker.get('ask', 0)))

            if spot_bid == 0 or spot_ask == 0 or perp_bid == 0 or perp_ask == 0:
                return

            # 检查是否满足平仓条件
            profit_pct = self._calculate_current_profit(spot_bid, spot_ask, perp_bid, perp_ask)

            if profit_pct <= self.min_closing_arbitrage_pct:
                self.logger.info(f"价差缩小，平仓: 当前利润 {profit_pct:.4%} <= 目标 {self.min_closing_arbitrage_pct:.4%}")
                await self._close_arbitrage_position()

        except Exception as e:
            self.logger.error(f"检查平仓机会失败: {e}")

    def _calculate_current_profit(
        self,
        spot_bid: Decimal,
        spot_ask: Decimal,
        perp_bid: Decimal,
        perp_ask: Decimal
    ) -> Decimal:
        """计算当前利润"""
        if not self._current_arb_position:
            return Decimal(0)

        # 根据当前仓位计算利润
        if self._current_arb_position.buy_market == 'spot':
            # 现货买 + 永续卖
            current_profit = (perp_bid - spot_ask) / spot_ask
        else:
            # 现货卖 + 永续买
            current_profit = (spot_bid - perp_ask) / perp_ask

        return current_profit

    async def _open_arbitrage_position(self, proposal: ArbProposal):
        """开仓"""
        self._strategy_state = StrategyState.Opening
        self.logger.info(f"发现套利机会: 预期利润 {proposal.expected_profit_pct:.4%}")
        self.logger.info(f"  买入 {proposal.buy_market}: {proposal.buy_price}")
        self.logger.info(f"  卖出 {proposal.sell_market}: {proposal.sell_price}")

        try:
            # 买入
            buy_order_id = await self.create_order_callback(
                proposal.buy_market + ':' + (self.spot_trading_pair if proposal.buy_market == 'spot' else self.perp_trading_pair),
                'buy',
                float(proposal.order_amount),
                float(proposal.buy_price),
                'limit'
            )
            self._opening_order_ids.append(buy_order_id)

            # 卖出
            sell_order_id = await self.create_order_callback(
                proposal.sell_market + ':' + (self.spot_trading_pair if proposal.sell_market == 'spot' else self.perp_trading_pair),
                'sell',
                float(proposal.order_amount),
                float(proposal.sell_price),
                'limit'
            )
            self._opening_order_ids.append(sell_order_id)

            self._current_arb_position = proposal
            self.logger.info("套利开仓订单已提交")

            # 等待订单成交
            await asyncio.sleep(5)

            # 假设订单都成交了（简化处理）
            self._strategy_state = StrategyState.Opened
            self._opening_order_ids = []

        except Exception as e:
            self.logger.error(f"开仓失败: {e}")
            self._strategy_state = StrategyState.Closed

    async def _close_arbitrage_position(self):
        """平仓"""
        if not self._current_arb_position:
            return

        self._strategy_state = StrategyState.Closing
        self.logger.info("开始平仓...")

        try:
            # 获取当前仓位（这里简化处理）
            order_amount = self._current_arb_position.order_amount

            # 如果是现货买 + 永续卖，现在需要现货卖 + 永续买
            if self._current_arb_position.buy_market == 'spot':
                # 现货卖
                await self.create_order_callback(
                    self.spot_market + ':' + self.spot_trading_pair,
                    'sell',
                    float(order_amount),
                    0,
                    'market'
                )
                # 永续买
                await self.create_order_callback(
                    self.perp_market + ':' + self.perp_trading_pair,
                    'buy',
                    float(order_amount),
                    0,
                    'market'
                )
            else:
                # 现货买
                await self.create_order_callback(
                    self.spot_market + ':' + self.spot_trading_pair,
                    'buy',
                    float(order_amount),
                    0,
                    'market'
                )
                # 永续卖
                await self.create_order_callback(
                    self.perp_market + ':' + self.perp_trading_pair,
                    'sell',
                    float(order_amount),
                    0,
                    'market'
                )

            self._current_arb_position = None
            self._strategy_state = StrategyState.Closed
            self._next_arbitrage_opening_ts = datetime.now().timestamp() + self.next_arbitrage_opening_delay
            self.logger.info("平仓完成")

        except Exception as e:
            self.logger.error(f"平仓失败: {e}")

    async def _report_status(self):
        """报告状态"""
        status = {
            "state": self._strategy_state.name,
            "arbitrage_profit": str(self._current_arb_position.expected_profit_pct) if self._current_arb_position else "0",
            "next_arbitrage_delay": max(0, self._next_arbitrage_opening_ts - datetime.now().timestamp())
        }

        self.logger.info(f"套利策略状态: {status}")

    def get_status(self) -> Dict:
        """获取策略状态"""
        return {
            "strategy": "spot_perpetual_arbitrage",
            "spot_market": self.spot_market,
            "spot_trading_pair": self.spot_trading_pair,
            "perp_market": self.perp_market,
            "perp_trading_pair": self.perp_trading_pair,
            "order_amount": str(self.order_amount),
            "perp_leverage": self.perp_leverage,
            "min_opening_arbitrage_pct": str(self.min_opening_arbitrage_pct),
            "min_closing_arbitrage_pct": str(self.min_closing_arbitrage_pct),
            "state": self._strategy_state.name,
            "current_position": str(self._current_arb_position) if self._current_arb_position else None,
            "is_running": self.is_running
        }
