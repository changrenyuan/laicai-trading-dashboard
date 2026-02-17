"""
仓位管理模块
跟踪和管理交易仓位
"""
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PositionSide(Enum):
    """仓位方向"""
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class Position:
    """单个仓位"""

    def __init__(self, symbol: str, side: PositionSide, size: float,
                 entry_price: float, timestamp: datetime = None):
        self.symbol = symbol
        self.side = side
        self.size = size
        self.entry_price = entry_price
        self.entry_time = timestamp or datetime.utcnow()
        self.exit_price: Optional[float] = None
        self.exit_time: Optional[datetime] = None
        self.realized_pnl: float = 0.0
        self.unrealized_pnl: float = 0.0

    @property
    def is_open(self) -> bool:
        """仓位是否开仓"""
        return self.exit_time is None

    @property
    def notional_value(self) -> float:
        """仓位名义价值"""
        return abs(self.size * self.entry_price)

    def update_unrealized_pnl(self, current_price: float):
        """更新未实现盈亏"""
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (current_price - self.entry_price) * self.size
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.size

    def close(self, exit_price: float, timestamp: datetime = None):
        """平仓"""
        self.exit_price = exit_price
        self.exit_time = timestamp or datetime.utcnow()

        if self.side == PositionSide.LONG:
            self.realized_pnl = (exit_price - self.entry_price) * self.size
        else:
            self.realized_pnl = (self.entry_price - exit_price) * self.size

        logger.info(f"Position closed: {self.symbol} {self.side} "
                   f"PnL: {self.realized_pnl:.2f}")

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "size": self.size,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "is_open": self.is_open,
            "notional_value": self.notional_value
        }


class PositionManager:
    """仓位管理器"""

    def __init__(self):
        self._positions: Dict[str, Position] = {}
        self._closed_positions: List[Position] = []

    def open_position(self, symbol: str, side: PositionSide, size: float,
                     entry_price: float) -> Position:
        """开仓"""
        # 检查是否已有同方向仓位
        key = f"{symbol}_{side.value}"
        if key in self._positions:
            # 累加仓位
            existing_pos = self._positions[key]
            total_size = existing_pos.size + size
            avg_price = (existing_pos.entry_price * existing_pos.size +
                        entry_price * size) / total_size
            existing_pos.size = total_size
            existing_pos.entry_price = avg_price
            logger.info(f"Position accumulated: {symbol} {side.value} "
                       f"New size: {total_size}")
            return existing_pos

        # 创建新仓位
        position = Position(symbol, side, size, entry_price)
        self._positions[key] = position
        logger.info(f"Position opened: {symbol} {side.value} Size: {size}")
        return position

    def close_position(self, symbol: str, side: PositionSide,
                      exit_price: float) -> Optional[Position]:
        """平仓"""
        key = f"{symbol}_{side.value}"
        if key not in self._positions:
            logger.warning(f"No position to close: {symbol} {side.value}")
            return None

        position = self._positions.pop(key)
        position.close(exit_price)
        self._closed_positions.append(position)
        return position

    def get_position(self, symbol: str, side: PositionSide) -> Optional[Position]:
        """获取仓位"""
        key = f"{symbol}_{side.value}"
        return self._positions.get(key)

    def get_all_positions(self) -> Dict[str, Position]:
        """获取所有开仓"""
        return self._positions.copy()

    def get_closed_positions(self, limit: int = 100) -> List[Position]:
        """获取已平仓历史"""
        return self._closed_positions[-limit:]

    def update_unrealized_pnl(self, symbol: str, current_price: float):
        """更新所有相关仓位的未实现盈亏"""
        for position in self._positions.values():
            if position.symbol == symbol:
                position.update_unrealized_pnl(current_price)

    def get_total_unrealized_pnl(self) -> float:
        """获取总未实现盈亏"""
        return sum(pos.unrealized_pnl for pos in self._positions.values())

    def get_total_realized_pnl(self) -> float:
        """获取总已实现盈亏"""
        return sum(pos.realized_pnl for pos in self._closed_positions)

    def get_position_size(self, symbol: str) -> Dict[str, float]:
        """获取特定交易对的仓位大小"""
        sizes = {"long": 0.0, "short": 0.0}
        for key, position in self._positions.items():
            if position.symbol == symbol:
                sizes[position.side.value] = position.size
        return sizes

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "open_positions": {k: v.to_dict() for k, v in self._positions.items()},
            "closed_positions_count": len(self._closed_positions),
            "total_unrealized_pnl": self.get_total_unrealized_pnl(),
            "total_realized_pnl": self.get_total_realized_pnl()
        }
