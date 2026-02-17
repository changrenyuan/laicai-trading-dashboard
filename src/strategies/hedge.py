"""
对冲策略 (Hedge)
基于 Hummingbot 的 hedge 策略
对冲仓位风险，保护资产
"""
import asyncio
import logging
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime

from ..core.strategy import StrategyBase
from ..core.position import PositionSide
from ..core.event_bus import EventBus


class HedgeStrategy(StrategyBase):
    """
    对冲策略

    原理：
    - 监控目标资产的价格变动
    - 在衍生品市场建立对冲仓位
    - 平衡风险敞口

    特性：
    - 自动对冲价格风险
    - 支持部分对冲
    - 动态对冲比例调整
    - 止损止盈
    """

    def __init__(
        self,
        event_bus: EventBus,
        position_manager,
        risk_manager,
        config: Dict
    ):
        super().__init__(event_bus, position_manager, risk_manager, config)

        # 资产配置
        self.target_asset = config.get('target_asset', 'BTC')
        self.spot_market = config.get('spot_market', 'okx')
        self.perp_market = config.get('perp_market', 'okx')

        # 交易对
        self.spot_trading_pair = config.get('spot_trading_pair', 'BTC-USDT')
        self.perp_trading_pair = config.get('perp_trading_pair', 'BTC-USDT-SWAP')

        # 对冲配置
        self.hedge_ratio = Decimal(str(config.get('hedge_ratio', 1.0)))  # 100% 对冲
        self.hedge_threshold = Decimal(str(config.get('hedge_threshold', 0.01)))  # 1% 变动触发对冲
        self.rebalance_threshold = Decimal(str(config.get('rebalance_threshold', 0.05)))  # 5% 重新平衡

        # 止损止盈
        self.stop_loss_pct = Decimal(str(config.get('stop_loss_pct', 0.1)))  # 10% 止损
        self.take_profit_pct = Decimal(str(config.get('take_profit_pct', 0.2)))  # 20% 止盈

        # 杠杆配置
        self.perp_leverage = config.get('perp_leverage', 1)

        # 内部状态
        self._spot_position_size = Decimal(0)
        self._perp_position_size = Decimal(0)
        self._last_hedge_time = 0
        self._entry_price = Decimal(0)

        self.logger.info(f"对冲策略初始化:")
        self.logger.info(f"  目标资产: {self.target_asset}")
        self.logger.info(f"  现货: {self.spot_market}:{self.spot_trading_pair}")
        self.logger.info(f"  永续: {self.perp_market}:{self.perp_trading_pair}")
        self.logger.info(f"  对冲比例: {self.hedge_ratio:.2%}")

    async def on_tick(self, ticker: Dict):
        """价格更新回调"""
        await super().on_tick(ticker)

        # 更新持仓信息
        await self._update_positions()

        # 检查是否需要对冲
        await self._check_hedge_conditions(ticker)

        # 检查止损止盈
        await self._check_stop_loss_take_profit(ticker)

    async def _update_positions(self):
        """更新持仓信息"""
        try:
            balance = await self.get_balance_callback() if self.get_balance_callback else {}

            base_asset = self.spot_trading_pair.split('-')[0]
            self._spot_position_size = Decimal(str(balance.get(base_asset, 0)))

            # 简化处理：永续仓位需要从交易所 API 获取
            # 这里假设已经获取
            self._perp_position_size = Decimal(0)  # 需要从交易所 API 获取

        except Exception as e:
            self.logger.error(f"更新持仓信息失败: {e}")

    async def _check_hedge_conditions(self, ticker: Dict):
        """检查对冲条件"""
        try:
            current_time = datetime.now().timestamp()

            # 检查对冲冷却时间
            if current_time - self._last_hedge_time < 60:  # 1分钟冷却
                return

            if self._spot_position_size == 0:
                return

            # 计算目标对冲量
            target_hedge_size = self._spot_position_size * self.hedge_ratio
            current_hedge_size = abs(self._perp_position_size)

            # 计算对冲偏差
            hedge_deviation = abs(current_hedge_size - target_hedge_size) / target_hedge_size if target_hedge_size > 0 else 0

            # 如果偏差超过阈值，调整对冲
            if hedge_deviation > self.rebalance_threshold:
                await self._rebalance_hedge(target_hedge_size)
                self._last_hedge_time = current_time

        except Exception as e:
            self.logger.error(f"检查对冲条件失败: {e}")

    async def _rebalance_hedge(self, target_size: Decimal):
        """重新平衡对冲"""
        try:
            if target_size == 0:
                return

            current_size = abs(self._perp_position_size)
            diff = target_size - current_size

            if abs(diff) < Decimal('0.0001'):  # 差异太小，忽略
                return

            # 确定对冲方向（现货多头对应永续空头）
            hedge_side = 'sell' if diff > 0 else 'buy'

            perp_pair = f"{self.perp_market}:{self.perp_trading_pair}"

            # 下对冲订单
            order_id = await self.create_order_callback(
                perp_pair,
                hedge_side,
                float(abs(diff)),
                0,  # 市价单
                'market'
            )

            if order_id:
                self.logger.info(f"对冲调整: {hedge_side} {abs(diff)} {self.target_asset}")

        except Exception as e:
            self.logger.error(f"重新平衡对冲失败: {e}")

    async def _check_stop_loss_take_profit(self, ticker: Dict):
        """检查止损止盈"""
        try:
            current_price = ticker.get('last', ticker.get('bid', 0))
            if current_price == 0 or self._entry_price == 0:
                return

            price_change = (current_price - self._entry_price) / self._entry_price

            # 检查止损
            if price_change <= -self.stop_loss_pct:
                self.logger.warning(f"触发止损: 价格变化 {price_change:.2%}")
                await self._close_hedge()

            # 检查止盈
            elif price_change >= self.take_profit_pct:
                self.logger.info(f"触发止盈: 价格变化 {price_change:.2%}")
                await self._close_hedge()

        except Exception as e:
            self.logger.error(f"检查止损止盈失败: {e}")

    async def _close_hedge(self):
        """平掉对冲仓位"""
        try:
            if self._perp_position_size == 0:
                return

            perp_pair = f"{self.perp_market}:{self.perp_trading_pair}"
            close_side = 'buy' if self._perp_position_size < 0 else 'sell'

            order_id = await self.create_order_callback(
                perp_pair,
                close_side,
                float(abs(self._perp_position_size)),
                0,
                'market'
            )

            if order_id:
                self.logger.info(f"对冲平仓: {close_side} {abs(self._perp_position_size)}")
                self._perp_position_size = Decimal(0)

        except Exception as e:
            self.logger.error(f"平掉对冲仓位失败: {e}")

    async def _run_loop(self):
        """策略主循环"""
        while self.is_running:
            try:
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"对冲策略主循环错误: {e}")

    async def on_order_book(self, order_book: Dict):
        """订单簿更新回调"""
        # 对冲策略主要使用ticker数据，订单簿回调暂不处理
        # 可以在未来扩展为使用订单簿数据
        pass

    def get_status(self) -> Dict:
        """获取策略状态"""
        return {
            "strategy": "hedge",
            "target_asset": self.target_asset,
            "spot_market": self.spot_market,
            "perp_market": self.perp_market,
            "spot_trading_pair": self.spot_trading_pair,
            "perp_trading_pair": self.perp_trading_pair,
            "hedge_ratio": str(self.hedge_ratio),
            "hedge_threshold": str(self.hedge_threshold),
            "stop_loss_pct": str(self.stop_loss_pct),
            "take_profit_pct": str(self.take_profit_pct),
            "spot_position_size": str(self._spot_position_size),
            "perp_position_size": str(self._perp_position_size),
            "is_running": self.is_running
        }
