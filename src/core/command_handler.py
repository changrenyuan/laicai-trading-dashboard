"""
命令处理器 - 统一的命令入口
前端通过 POST /api/command 发送所有操作命令
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CommandHandler:
    """
    命令处理器

    支持的命令类型：
    - start_strategy: 启动策略
    - stop_strategy: 停止策略
    - place_order: 下单
    - cancel_order: 取消订单
    - cancel_all_orders: 取消所有订单
    - kill_switch: 紧急停止
    - get_state: 获取状态
    """

    def __init__(self, bot_instance, event_bus, strategy_manager=None):
        """
        初始化命令处理器

        Args:
            bot_instance: 机器人实例
            event_bus: 事件总线
            strategy_manager: 策略管理器（可选）
        """
        self.bot = bot_instance
        self.event_bus = event_bus
        self.strategy_manager = strategy_manager

        # 命令注册表
        self._command_handlers = {
            "start_strategy": self._handle_start_strategy,
            "stop_strategy": self._handle_stop_strategy,
            "place_order": self._handle_place_order,
            "cancel_order": self._handle_cancel_order,
            "cancel_all_orders": self._handle_cancel_all_orders,
            "kill_switch": self._handle_kill_switch,
            "get_state": self._handle_get_state,
        }

    async def handle_command(self, cmd: str, params: Dict = None) -> Dict:
        """
        处理命令

        Args:
            cmd: 命令类型
            params: 命令参数

        Returns:
            命令执行结果
        """
        params = params or {}
        logger.info(f"Received command: {cmd} with params: {params}")

        if cmd not in self._command_handlers:
            return {
                "success": False,
                "error": f"Unknown command: {cmd}",
                "available_commands": list(self._command_handlers.keys())
            }

        try:
            handler = self._command_handlers[cmd]
            result = await handler(params)

            # 发送日志事件
            await self.event_bus.publish_log(
                level="INFO",
                msg=f"Command executed: {cmd}",
                logger_name="command_handler"
            )

            return {
                "success": True,
                "cmd": cmd,
                "timestamp": datetime.utcnow().isoformat(),
                **result
            }

        except Exception as e:
            logger.error(f"Error executing command {cmd}: {e}", exc_info=True)

            # 发送错误事件
            await self.event_bus.publish_error(
                error_type=f"command_failed:{cmd}",
                message=str(e),
                details={"cmd": cmd, "params": params}
            )

            return {
                "success": False,
                "cmd": cmd,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    # ============ 命令处理函数 ============

    async def _handle_start_strategy(self, params: Dict) -> Dict:
        """启动策略"""
        strategy_id = params.get("strategy_id")

        if self.strategy_manager:
            # 多策略模式
            if strategy_id:
                # 启动指定的策略实例
                instance_id = params.get("instance_id")
                success = await self.strategy_manager.start_strategy(instance_id or strategy_id)

                if success:
                    await self.event_bus.publish_strategy(
                        strategy_id=strategy_id,
                        status="running"
                    )
                    return {"status": "started", "strategy_id": strategy_id}
                else:
                    raise Exception(f"Failed to start strategy: {strategy_id}")
            else:
                raise Exception("strategy_id is required")
        else:
            # 单策略模式
            if self.bot.strategy and not self.bot.strategy.is_running:
                await self.bot.strategy.start()
                await self.event_bus.publish_strategy(
                    strategy_id=self.bot.strategy.__class__.__name__,
                    status="running"
                )
                return {"status": "started"}
            else:
                raise Exception("Strategy not initialized or already running")

    async def _handle_stop_strategy(self, params: Dict) -> Dict:
        """停止策略"""
        strategy_id = params.get("strategy_id")

        if self.strategy_manager:
            # 多策略模式
            instance_id = params.get("instance_id")
            success = await self.strategy_manager.stop_strategy(instance_id or strategy_id)

            if success:
                await self.event_bus.publish_strategy(
                    strategy_id=strategy_id,
                    status="stopped"
                )
                return {"status": "stopped", "strategy_id": strategy_id}
            else:
                raise Exception(f"Failed to stop strategy: {strategy_id}")
        else:
            # 单策略模式
            if self.bot.strategy and self.bot.strategy.is_running:
                await self.bot.strategy.stop()
                await self.event_bus.publish_strategy(
                    strategy_id=self.bot.strategy.__class__.__name__,
                    status="stopped"
                )
                return {"status": "stopped"}
            else:
                raise Exception("Strategy not running")

    async def _handle_place_order(self, params: Dict) -> Dict:
        """下单"""
        symbol = params.get("symbol")
        side = params.get("side")
        size = params.get("size")
        order_type = params.get("type", "limit")
        price = params.get("price")

        if not all([symbol, side, size]):
            raise Exception("Missing required parameters: symbol, side, size")

        if order_type == "limit" and price is None:
            raise Exception("Price is required for limit orders")

        # 调用交易所下单
        order_id = await self.bot.exchange.create_order(
            symbol=symbol,
            side=side,
            size=size,
            price=price or 0,
            order_type=order_type
        )

        if order_id:
            await self.event_bus.publish_order_update(
                order_id=order_id,
                status="open",
                symbol=symbol,
                filled=0,
                price=price
            )
            return {"order_id": order_id, "status": "open"}
        else:
            raise Exception("Failed to place order")

    async def _handle_cancel_order(self, params: Dict) -> Dict:
        """取消订单"""
        order_id = params.get("order_id")
        symbol = params.get("symbol")

        if not order_id:
            raise Exception("Missing required parameter: order_id")

        success = await self.bot.exchange.cancel_order(order_id, symbol)

        if success:
            await self.event_bus.publish_order_update(
                order_id=order_id,
                status="canceled",
                symbol=symbol
            )
            return {"order_id": order_id, "status": "canceled"}
        else:
            raise Exception(f"Failed to cancel order: {order_id}")

    async def _handle_cancel_all_orders(self, params: Dict) -> Dict:
        """取消所有订单"""
        symbol = params.get("symbol")

        cancelled = await self.bot.exchange.cancel_all_orders(symbol)

        await self.event_bus.publish_log(
            level="INFO",
            msg=f"Cancelled {cancelled} orders",
            logger_name="command_handler"
        )

        return {"cancelled": cancelled}

    async def _handle_kill_switch(self, params: Dict) -> Dict:
        """紧急停止"""
        logger.warning("Kill Switch triggered!")

        stopped_strategies = 0
        cancelled_orders = 0

        # 停止所有策略
        if self.strategy_manager:
            instances = self.strategy_manager.get_instances_summary()
            for instance in instances:
                if instance.get('is_running'):
                    await self.strategy_manager.stop_strategy(instance['instance_id'])
                    stopped_strategies += 1
        elif self.bot.strategy and self.bot.strategy.is_running:
            await self.bot.strategy.stop()
            stopped_strategies = 1

        # 取消所有订单
        if hasattr(self.bot, 'exchange'):
            cancelled_orders = await self.bot.exchange.cancel_all_orders()

        # 发送事件
        await self.event_bus.publish_log(
            level="WARNING",
            msg=f"Kill Switch activated: stopped {stopped_strategies} strategies, cancelled {cancelled_orders} orders",
            logger_name="kill_switch"
        )

        return {
            "stopped_strategies": stopped_strategies,
            "cancelled_orders": cancelled_orders
        }

    async def _handle_get_state(self, params: Dict) -> Dict:
        """获取状态（内部调用）"""
        # 这个命令不直接返回状态，状态通过 /api/state 接口获取
        return {"message": "Use /api/state endpoint to get current state"}
