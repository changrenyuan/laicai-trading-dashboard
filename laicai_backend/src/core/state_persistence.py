"""
状态持久化 - 简单的 JSON 文件持久化
用于在 WebSocket 重连时恢复状态
"""
import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class StatePersistence:
    """
    状态持久化管理器

    将策略、仓位、订单等状态持久化到 JSON 文件
    支持 WebSocket 重连时的状态恢复
    """

    def __init__(self, state_dir: str = "state"):
        """
        初始化状态持久化

        Args:
            state_dir: 状态存储目录
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)

        # 状态文件路径
        self.strategies_file = self.state_dir / "strategies.json"
        self.positions_file = self.state_dir / "positions.json"
        self.orders_file = self.state_dir / "orders.json"
        self.balances_file = self.state_dir / "balances.json"

        logger.info(f"State persistence initialized: {self.state_dir}")

    def save_strategies(self, strategies: Dict):
        """保存策略状态"""
        self._save_json(self.strategies_file, strategies)
        logger.debug(f"Strategies saved: {len(strategies)} strategies")

    def load_strategies(self) -> Dict:
        """加载策略状态"""
        return self._load_json(self.strategies_file, default={})

    def save_positions(self, positions: Dict):
        """保存仓位状态"""
        self._save_json(self.positions_file, positions)
        logger.debug(f"Positions saved: {len(positions)} positions")

    def load_positions(self) -> Dict:
        """加载仓位状态"""
        return self._load_json(self.positions_file, default={})

    def save_orders(self, orders: Dict):
        """保存订单状态"""
        self._save_json(self.orders_file, orders)
        logger.debug(f"Orders saved: {len(orders)} orders")

    def load_orders(self) -> Dict:
        """加载订单状态"""
        return self._load_json(self.orders_file, default={})

    def save_balances(self, balances: Dict):
        """保存余额状态"""
        self._save_json(self.balances_file, balances)
        logger.debug(f"Balances saved: {len(balances)} balances")

    def load_balances(self) -> Dict:
        """加载余额状态"""
        return self._load_json(self.balances_file, default={})

    def save_all(self, strategies: Dict, positions: Dict, orders: Dict, balances: Dict):
        """保存所有状态"""
        self.save_strategies(strategies)
        self.save_positions(positions)
        self.save_orders(orders)
        self.save_balances(balances)
        logger.info("All state saved")

    def load_all(self) -> Dict[str, Dict]:
        """加载所有状态"""
        return {
            "strategies": self.load_strategies(),
            "positions": self.load_positions(),
            "orders": self.load_orders(),
            "balances": self.load_balances()
        }

    def clear_all(self):
        """清空所有状态"""
        for file_path in [self.strategies_file, self.positions_file, self.orders_file, self.balances_file]:
            if file_path.exists():
                file_path.unlink()
        logger.info("All state cleared")

    def _save_json(self, file_path: Path, data: Dict):
        """保存 JSON 数据"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_json(self, file_path: Path, default: Any = None) -> Any:
        """加载 JSON 数据"""
        if not file_path.exists():
            return default

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading state from {file_path}: {e}")
            return default

    def get_state_summary(self) -> Dict:
        """获取状态摘要"""
        return {
            "strategies_count": len(self.load_strategies()),
            "positions_count": len(self.load_positions()),
            "orders_count": len(self.load_orders()),
            "balances_count": len(self.load_balances()),
            "last_updated": datetime.utcnow().isoformat()
        }
