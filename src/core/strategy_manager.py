"""
多策略实例管理器
支持同时运行多个策略实例
"""
import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict

from .event_bus import EventBus
from .position import PositionManager
from .risk_manager import RiskManager
from ..strategies.market_maker import MarketMakerStrategy
from ..strategies.pure_market_making import PureMarketMakingStrategy
from ..strategies.perpetual_market_making import PerpetualMarketMakingStrategy
from ..strategies.spot_perpetual_arbitrage import SpotPerpetualArbitrageStrategy


@dataclass
class StrategyInstance:
    """策略实例"""
    instance_id: str
    strategy_name: str
    strategy: object
    config: dict
    created_at: float
    is_running: bool
    last_active: float


class StrategyManager:
    """
    多策略实例管理器

    功能：
    - 创建和管理多个策略实例
    - 支持不同类型的策略同时运行
    - 提供策略生命周期管理
    - 统一的事件分发
    """

    def __init__(self, event_bus: EventBus, position_manager: PositionManager, risk_manager: RiskManager):
        self.logger = logging.getLogger(__name__)
        self.event_bus = event_bus
        self.position_manager = position_manager
        self.risk_manager = risk_manager

        # 策略实例存储
        self._instances: Dict[str, StrategyInstance] = {}

        # 交易所回调（需要从外部注入）
        self._exchange_callbacks = {
            'create_order': None,
            'cancel_order': None,
            'cancel_all_orders': None,
            'get_balance': None,
            'get_ticker': None,
            'get_order_book': None
        }

        # 策略注册表
        self._strategy_registry = {
            'market_maker': MarketMakerStrategy,
            'pure_market_making': PureMarketMakingStrategy,
            'perpetual_market_making': PerpetualMarketMakingStrategy,
            'spot_perpetual_arbitrage': SpotPerpetualArbitrageStrategy
        }

        self.logger.info("策略管理器初始化完成")

    def set_exchange_callbacks(self, callbacks: Dict[str, Callable]):
        """设置交易所回调函数"""
        self._exchange_callbacks.update(callbacks)
        self.logger.info("交易所回调已设置")

    def get_available_strategies(self) -> List[Dict]:
        """获取可用策略列表"""
        strategies = []
        for name, strategy_class in self._strategy_registry.items():
            strategies.append({
                "name": name,
                "display_name": name.replace('_', ' ').title(),
                "description": self._get_strategy_description(name)
            })
        return strategies

    def _get_strategy_description(self, strategy_name: str) -> str:
        """获取策略描述"""
        descriptions = {
            'market_maker': '经典做市策略，在买卖价差之间挂单',
            'pure_market_making': '纯现货做市，支持库存偏差、Ping-Pong 模式',
            'perpetual_market_making': '永续合约做市，支持止盈止损、杠杆交易',
            'spot_perpetual_arbitrage': '现货永续套利，对冲价差获利'
        }
        return descriptions.get(strategy_name, '未知策略')

    async def create_strategy_instance(
        self,
        strategy_name: str,
        config: dict,
        instance_name: Optional[str] = None
    ) -> StrategyInstance:
        """
        创建策略实例

        :param strategy_name: 策略名称
        :param config: 策略配置
        :param instance_name: 实例名称（可选）
        :return: 策略实例
        """
        if strategy_name not in self._strategy_registry:
            raise ValueError(f"未知策略: {strategy_name}")

        instance_id = str(uuid.uuid4())
        created_at = datetime.now().timestamp()

        # 创建策略对象
        strategy_class = self._strategy_registry[strategy_name]
        strategy = strategy_class(
            event_bus=self.event_bus,
            position_manager=self.position_manager,
            risk_manager=self.risk_manager,
            config=config
        )

        # 设置策略回调
        self._setup_strategy_callbacks(strategy)

        # 创建策略实例
        instance = StrategyInstance(
            instance_id=instance_id,
            strategy_name=strategy_name,
            strategy=strategy,
            config=config,
            created_at=created_at,
            is_running=False,
            last_active=created_at
        )

        self._instances[instance_id] = instance

        # 发布事件
        await self.event_bus.publish("strategy_instance_created", {
            "instance_id": instance_id,
            "strategy_name": strategy_name,
            "config": config
        })

        self.logger.info(f"策略实例创建成功: {strategy_name} ({instance_id})")

        return instance

    def _setup_strategy_callbacks(self, strategy):
        """设置策略回调函数"""
        # 创建订单回调
        async def create_order_callback(symbol, side, size, price, order_type='limit'):
            if self._exchange_callbacks['create_order']:
                return await self._exchange_callbacks['create_order'](symbol, side, size, price, order_type)
            raise NotImplementedError("create_order_callback 未设置")

        async def cancel_order_callback(order_id):
            if self._exchange_callbacks['cancel_order']:
                return await self._exchange_callbacks['cancel_order'](order_id)
            raise NotImplementedError("cancel_order_callback 未设置")

        async def cancel_all_orders_callback(symbol=None):
            if self._exchange_callbacks['cancel_all_orders']:
                return await self._exchange_callbacks['cancel_all_orders'](symbol)
            raise NotImplementedError("cancel_all_orders_callback 未设置")

        async def get_balance_callback():
            if self._exchange_callbacks['get_balance']:
                return await self._exchange_callbacks['get_balance']()
            raise NotImplementedError("get_balance_callback 未设置")

        # 设置到策略
        strategy.create_order_callback = create_order_callback
        strategy.cancel_order_callback = cancel_order_callback
        strategy.cancel_all_orders_callback = cancel_all_orders_callback
        strategy.get_balance_callback = get_balance_callback

    async def start_strategy(self, instance_id: str) -> bool:
        """启动策略实例"""
        if instance_id not in self._instances:
            self.logger.error(f"策略实例不存在: {instance_id}")
            return False

        instance = self._instances[instance_id]

        if instance.is_running:
            self.logger.warning(f"策略实例已在运行: {instance_id}")
            return False

        try:
            # 启动策略
            await instance.strategy.start()

            instance.is_running = True
            instance.last_active = datetime.now().timestamp()

            # 发布事件
            await self.event_bus.publish("strategy_instance_started", {
                "instance_id": instance_id,
                "strategy_name": instance.strategy_name
            })

            self.logger.info(f"策略实例启动成功: {instance_id}")
            return True

        except Exception as e:
            self.logger.error(f"启动策略实例失败: {e}")
            return False

    async def stop_strategy(self, instance_id: str) -> bool:
        """停止策略实例"""
        if instance_id not in self._instances:
            self.logger.error(f"策略实例不存在: {instance_id}")
            return False

        instance = self._instances[instance_id]

        if not instance.is_running:
            self.logger.warning(f"策略实例未运行: {instance_id}")
            return False

        try:
            # 停止策略
            await instance.strategy.stop()

            instance.is_running = False
            instance.last_active = datetime.now().timestamp()

            # 发布事件
            await self.event_bus.publish("strategy_instance_stopped", {
                "instance_id": instance_id,
                "strategy_name": instance.strategy_name
            })

            self.logger.info(f"策略实例停止成功: {instance_id}")
            return True

        except Exception as e:
            self.logger.error(f"停止策略实例失败: {e}")
            return False

    async def delete_strategy_instance(self, instance_id: str) -> bool:
        """删除策略实例"""
        if instance_id not in self._instances:
            self.logger.error(f"策略实例不存在: {instance_id}")
            return False

        instance = self._instances[instance_id]

        # 如果策略正在运行，先停止
        if instance.is_running:
            await self.stop_strategy(instance_id)

        # 删除实例
        del self._instances[instance_id]

        # 发布事件
        await self.event_bus.publish("strategy_instance_deleted", {
            "instance_id": instance_id,
            "strategy_name": instance.strategy_name
        })

        self.logger.info(f"策略实例删除成功: {instance_id}")
        return True

    def get_strategy_instance(self, instance_id: str) -> Optional[StrategyInstance]:
        """获取策略实例"""
        return self._instances.get(instance_id)

    def get_all_instances(self) -> List[StrategyInstance]:
        """获取所有策略实例"""
        return list(self._instances.values())

    def get_running_instances(self) -> List[StrategyInstance]:
        """获取运行中的策略实例"""
        return [inst for inst in self._instances.values() if inst.is_running]

    async def update_strategy_config(self, instance_id: str, new_config: dict) -> bool:
        """更新策略配置"""
        if instance_id not in self._instances:
            self.logger.error(f"策略实例不存在: {instance_id}")
            return False

        instance = self._instances[instance_id]

        try:
            # 更新配置
            instance.config.update(new_config)
            instance.last_active = datetime.now().timestamp()

            # 发布事件
            await self.event_bus.publish("strategy_instance_updated", {
                "instance_id": instance_id,
                "config": new_config
            })

            self.logger.info(f"策略实例配置更新成功: {instance_id}")
            return True

        except Exception as e:
            self.logger.error(f"更新策略配置失败: {e}")
            return False

    async def distribute_market_data(self, ticker: dict, order_book: dict):
        """分发市场数据到所有运行中的策略"""
        running_instances = self.get_running_instances()

        for instance in running_instances:
            try:
                # 分发 tick 数据
                await instance.strategy.on_tick(ticker)

                # 分发订单簿数据
                await instance.strategy.on_order_book(order_book)

                instance.last_active = datetime.now().timestamp()

            except Exception as e:
                self.logger.error(f"分发市场数据到策略 {instance.instance_id} 失败: {e}")

    async def handle_order_filled(self, order_id: str, event: dict):
        """处理订单成交事件"""
        running_instances = self.get_running_instances()

        for instance in running_instances:
            try:
                instance.strategy.on_order_filled(event)
                instance.last_active = datetime.now().timestamp()
            except Exception as e:
                self.logger.error(f"策略 {instance.instance_id} 处理订单成交失败: {e}")

    def get_instances_summary(self) -> List[Dict]:
        """获取所有实例摘要"""
        summary = []
        for instance in self._instances.values():
            try:
                status = instance.strategy.get_status() if instance.strategy else {}
            except Exception as e:
                status = {}

            summary.append({
                "instance_id": instance.instance_id,
                "strategy_name": instance.strategy_name,
                "is_running": instance.is_running,
                "created_at": instance.created_at,
                "last_active": instance.last_active,
                "status": status
            })

        return summary
