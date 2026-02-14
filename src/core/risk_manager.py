"""
风险管理模块
实现止损、止盈、仓位限制等风控功能
"""
from typing import Dict, Optional, Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RiskLimit:
    """风险限制"""

    def __init__(self, name: str, limit_value: float,
                 current_value: float = 0.0, action: str = "warn"):
        self.name = name
        self.limit_value = limit_value
        self.current_value = current_value
        self.action = action  # "warn", "stop", "reduce"
        self.is_breached = False

    def check(self) -> bool:
        """检查是否超出限制"""
        self.is_breached = abs(self.current_value) > self.limit_value
        return self.is_breached


class RiskManager:
    """风险管理器"""

    def __init__(self, config: Dict):
        self.config = config
        self.limits: Dict[str, RiskLimit] = {}
        self.stop_orders: Dict = {}  # 止损订单
        self.take_profit_orders: Dict = {}  # 止盈订单
        self.daily_pnl: float = 0.0
        self.daily_loss_limit: float = config.get("max_daily_loss", 0.05)
        self._setup_limits()

    def _setup_limits(self):
        """初始化风险限制"""
        self.limits = {
            "max_position_size": RiskLimit(
                "Max Position Size",
                self.config.get("max_position_size", 0.1),
                action="stop"
            ),
            "max_order_size": RiskLimit(
                "Max Order Size",
                self.config.get("max_order_size", 0.01),
                action="warn"
            ),
            "daily_loss": RiskLimit(
                "Daily Loss Limit",
                self.daily_loss_limit,
                self.daily_pnl,
                action="stop"
            )
        }

    def check_order_size(self, size: float) -> tuple[bool, str]:
        """检查订单大小"""
        limit = self.limits["max_order_size"]
        if size > limit.limit_value:
            msg = f"Order size {size} exceeds limit {limit.limit_value}"
            logger.warning(msg)
            return False, msg
        return True, ""

    def check_position_limit(self, symbol: str, current_size: float,
                           new_size: float) -> tuple[bool, str]:
        """检查仓位限制"""
        limit = self.limits["max_position_size"]
        total_size = abs(current_size + new_size)

        if total_size > limit.limit_value:
            msg = f"Position size {total_size} exceeds limit {limit.limit_value}"
            logger.warning(msg)
            return False, msg
        return True, ""

    def check_daily_loss(self) -> tuple[bool, str]:
        """检查每日亏损"""
        limit = self.limits["daily_loss"]
        limit.current_value = self.daily_pnl

        if limit.check() and self.daily_pnl < 0:
            msg = f"Daily loss {abs(self.daily_pnl):.2%} exceeds limit"
            logger.error(msg)
            return False, msg
        return True, ""

    def set_stop_loss(self, symbol: str, side: str, entry_price: float,
                     percentage: float = None) -> Optional[float]:
        """设置止损价格"""
        if percentage is None:
            percentage = self.config.get("stop_loss_percentage", 0.02)

        if side == "long":
            stop_price = entry_price * (1 - percentage)
        else:
            stop_price = entry_price * (1 + percentage)

        key = f"{symbol}_{side}"
        self.stop_orders[key] = {
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "percentage": percentage,
            "created_at": datetime.utcnow()
        }

        logger.info(f"Stop loss set: {symbol} {side} at {stop_price}")
        return stop_price

    def set_take_profit(self, symbol: str, side: str, entry_price: float,
                       percentage: float = None) -> Optional[float]:
        """设置止盈价格"""
        if percentage is None:
            percentage = self.config.get("take_profit_percentage", 0.03)

        if side == "long":
            tp_price = entry_price * (1 + percentage)
        else:
            tp_price = entry_price * (1 - percentage)

        key = f"{symbol}_{side}"
        self.take_profit_orders[key] = {
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "tp_price": tp_price,
            "percentage": percentage,
            "created_at": datetime.utcnow()
        }

        logger.info(f"Take profit set: {symbol} {side} at {tp_price}")
        return tp_price

    def check_stop_loss(self, symbol: str, side: str, current_price: float
                       ) -> tuple[bool, Optional[Dict]]:
        """检查止损触发"""
        key = f"{symbol}_{side}"
        if key not in self.stop_orders:
            return False, None

        stop_order = self.stop_orders[key]

        if side == "long":
            triggered = current_price <= stop_order["stop_price"]
        else:
            triggered = current_price >= stop_order["stop_price"]

        if triggered:
            logger.warning(f"Stop loss triggered: {symbol} {side} at {current_price}")
            # 清除止损订单
            del self.stop_orders[key]
            return True, stop_order

        return False, None

    def check_take_profit(self, symbol: str, side: str, current_price: float
                         ) -> tuple[bool, Optional[Dict]]:
        """检查止盈触发"""
        key = f"{symbol}_{side}"
        if key not in self.take_profit_orders:
            return False, None

        tp_order = self.take_profit_orders[key]

        if side == "long":
            triggered = current_price >= tp_order["tp_price"]
        else:
            triggered = current_price <= tp_order["tp_price"]

        if triggered:
            logger.info(f"Take profit triggered: {symbol} {side} at {current_price}")
            # 清除止盈订单
            del self.take_profit_orders[key]
            return True, tp_order

        return False, None

    def update_daily_pnl(self, pnl: float):
        """更新每日盈亏"""
        self.daily_pnl += pnl
        logger.info(f"Daily PnL updated: {self.daily_pnl:.4f}")

    def reset_daily_pnl(self):
        """重置每日盈亏"""
        self.daily_pnl = 0.0
        self.limits["daily_loss"].current_value = 0.0
        logger.info("Daily PnL reset")

    def cancel_stop_loss(self, symbol: str, side: str):
        """取消止损"""
        key = f"{symbol}_{side}"
        if key in self.stop_orders:
            del self.stop_orders[key]
            logger.info(f"Stop loss cancelled: {symbol} {side}")

    def cancel_take_profit(self, symbol: str, side: str):
        """取消止盈"""
        key = f"{symbol}_{side}"
        if key in self.take_profit_orders:
            del self.take_profit_orders[key]
            logger.info(f"Take profit cancelled: {symbol} {side}")

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "limits": {k: {
                "name": v.name,
                "limit": v.limit_value,
                "current": v.current_value,
                "is_breached": v.is_breached,
                "action": v.action
            } for k, v in self.limits.items()},
            "stop_orders": self.stop_orders,
            "take_profit_orders": self.take_profit_orders,
            "daily_pnl": self.daily_pnl,
            "daily_loss_limit": self.daily_loss_limit
        }
