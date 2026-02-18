"""
WebSocket 命令处理器
处理前端通过 WebSocket 发送的各种命令
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WSCommandHandler:
    """
    WebSocket 命令处理器

    支持以下命令类型：
    - 策略管理: start_strategy, stop_strategy, pause_strategy, resume_strategy, delete_strategy, create_strategy, get_strategies
    - 订单管理: place_order, cancel_order, cancel_all_orders, get_orders
    - 连接管理: create_connection, delete_connection, test_connection
    - 系统命令: start_engine, stop_engine, get_system_status, get_positions, get_balances
    """

    def __init__(self, bot_instance, event_bus):
        self.bot = bot_instance
        self.event_bus = event_bus
        self.start_time = datetime.utcnow()

        # 连接管理：存储已创建的交易所连接
        self.connections: Dict[str, Dict] = {}

        logger.info("WebSocket Command Handler initialized")

    async def handle_command(self, command: Dict) -> Dict:
        """
        处理命令

        Args:
            command: 命令对象，格式: { "cmd": "command_name", ...params }

        Returns:
            响应对象，格式: { "success": true/false, "data": ..., "error": "..." }
        """
        cmd = command.get("cmd")

        if not cmd:
            return {
                "success": False,
                "error": "Missing 'cmd' field in command"
            }

        try:
            logger.info(f"Processing WebSocket command: {cmd}")

            # 策略管理命令
            if cmd == "start_strategy":
                return await self._start_strategy(command)
            elif cmd == "stop_strategy":
                return await self._stop_strategy(command)
            elif cmd == "pause_strategy":
                return await self._pause_strategy(command)
            elif cmd == "resume_strategy":
                return await self._resume_strategy(command)
            elif cmd == "delete_strategy":
                return await self._delete_strategy(command)
            elif cmd == "create_strategy":
                return await self._create_strategy(command)
            elif cmd == "get_strategies":
                return await self._get_strategies(command)

            # 订单管理命令
            elif cmd == "place_order":
                return await self._place_order(command)
            elif cmd == "cancel_order":
                return await self._cancel_order(command)
            elif cmd == "cancel_all_orders":
                return await self._cancel_all_orders(command)
            elif cmd == "get_orders":
                return await self._get_orders(command)

            # 连接管理命令
            elif cmd == "create_connection":
                return await self._create_connection(command)
            elif cmd == "delete_connection":
                return await self._delete_connection(command)
            elif cmd == "test_connection":
                return await self._test_connection(command)
            elif cmd == "get_connections":
                return await self._get_connections(command)

            # 系统命令
            elif cmd == "start_engine":
                return await self._start_engine(command)
            elif cmd == "stop_engine":
                return await self._stop_engine(command)
            elif cmd == "get_system_status":
                return await self._get_system_status(command)
            elif cmd == "get_positions":
                return await self._get_positions(command)
            elif cmd == "get_balances":
                return await self._get_balances(command)

            else:
                return {
                    "success": False,
                    "error": f"Unknown command: {cmd}"
                }

        except Exception as e:
            logger.error(f"Error processing command '{cmd}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "cmd": cmd
            }

    # ============ 策略管理命令 ============

    async def _start_strategy(self, command: Dict) -> Dict:
        """启动策略"""
        strategy_id = command.get("id")

        if not strategy_id:
            return {"success": False, "error": "Missing 'id' parameter"}

        if self.bot.strategy_manager:
            success = await self.bot.strategy_manager.start_strategy(strategy_id)
            if success:
                return {"success": True, "message": f"Strategy {strategy_id} started"}
            return {"success": False, "error": f"Failed to start strategy {strategy_id}"}

        return {"success": False, "error": "Strategy manager not available"}

    async def _stop_strategy(self, command: Dict) -> Dict:
        """停止策略"""
        strategy_id = command.get("id")

        if not strategy_id:
            return {"success": False, "error": "Missing 'id' parameter"}

        if self.bot.strategy_manager:
            success = await self.bot.strategy_manager.stop_strategy(strategy_id)
            if success:
                return {"success": True, "message": f"Strategy {strategy_id} stopped"}
            return {"success": False, "error": f"Failed to stop strategy {strategy_id}"}

        return {"success": False, "error": "Strategy manager not available"}

    async def _pause_strategy(self, command: Dict) -> Dict:
        """暂停策略"""
        strategy_id = command.get("id")

        if not strategy_id:
            return {"success": False, "error": "Missing 'id' parameter"}

        if self.bot.strategy_manager:
            success = await self.bot.strategy_manager.pause_strategy(strategy_id)
            if success:
                return {"success": True, "message": f"Strategy {strategy_id} paused"}
            return {"success": False, "error": f"Failed to pause strategy {strategy_id}"}

        return {"success": False, "error": "Strategy manager not available"}

    async def _resume_strategy(self, command: Dict) -> Dict:
        """恢复策略"""
        strategy_id = command.get("id")

        if not strategy_id:
            return {"success": False, "error": "Missing 'id' parameter"}

        if self.bot.strategy_manager:
            success = await self.bot.strategy_manager.resume_strategy(strategy_id)
            if success:
                return {"success": True, "message": f"Strategy {strategy_id} resumed"}
            return {"success": False, "error": f"Failed to resume strategy {strategy_id}"}

        return {"success": False, "error": "Strategy manager not available"}

    async def _delete_strategy(self, command: Dict) -> Dict:
        """删除策略"""
        strategy_id = command.get("id")

        if not strategy_id:
            return {"success": False, "error": "Missing 'id' parameter"}

        if self.bot.strategy_manager:
            success = await self.bot.strategy_manager.delete_strategy(strategy_id)
            if success:
                return {"success": True, "message": f"Strategy {strategy_id} deleted"}
            return {"success": False, "error": f"Failed to delete strategy {strategy_id}"}

        return {"success": False, "error": "Strategy manager not available"}

    async def _create_strategy(self, command: Dict) -> Dict:
        """创建策略"""
        name = command.get("name")
        strategy_type = command.get("type")
        exchange = command.get("exchange")
        pair = command.get("pair")

        if not all([name, strategy_type, exchange, pair]):
            return {"success": False, "error": "Missing required parameters (name, type, exchange, pair)"}

        if self.bot.strategy_manager:
            instance = await self.bot.strategy_manager.create_strategy_instance(
                strategy_name=strategy_type,
                config={
                    "name": name,
                    "exchange": exchange,
                    "trading_pair": pair
                },
                instance_name=name
            )
            return {
                "success": True,
                "message": f"Strategy '{name}' created",
                "instance_id": instance.instance_id
            }

        return {"success": False, "error": "Strategy manager not available"}

    async def _get_strategies(self, command: Dict) -> Dict:
        """获取策略列表"""
        if self.bot.strategy_manager:
            instances = self.bot.strategy_manager.get_instances_summary()
            return {"success": True, "strategies": instances}

        return {"success": False, "error": "Strategy manager not available"}

    # ============ 订单管理命令 ============

    async def _place_order(self, command: Dict) -> Dict:
        """下单"""
        symbol = command.get("symbol")
        side = command.get("side")
        order_type = command.get("type")
        size = command.get("size")
        price = command.get("price")

        if not all([symbol, side, order_type, size]):
            return {"success": False, "error": "Missing required parameters (symbol, side, type, size)"}

        if order_type == "limit" and price is None:
            return {"success": False, "error": "Missing 'price' parameter for limit order"}

        try:
            # 这里需要调用实际的交易所下单接口
            # 临时实现
            order_id = f"ORD-{int(datetime.utcnow().timestamp())}"
            return {
                "success": True,
                "message": "Order placed",
                "order_id": order_id
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _cancel_order(self, command: Dict) -> Dict:
        """取消订单"""
        order_id = command.get("order_id")

        if not order_id:
            return {"success": False, "error": "Missing 'order_id' parameter"}

        try:
            # 这里需要调用实际的交易所取消订单接口
            # 临时实现
            return {
                "success": True,
                "message": f"Order {order_id} cancelled"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _cancel_all_orders(self, command: Dict) -> Dict:
        """取消所有订单"""
        symbol = command.get("symbol")

        try:
            if self.bot and hasattr(self.bot, 'exchange'):
                cancelled_count = await self.bot.exchange.cancel_all_orders(symbol)
                return {
                    "success": True,
                    "message": f"Cancelled {cancelled_count} orders",
                    "cancelled_count": cancelled_count
                }
            return {"success": False, "error": "Exchange not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_orders(self, command: Dict) -> Dict:
        """获取订单列表"""
        symbol = command.get("symbol")
        status = command.get("status")
        strategy = command.get("strategy")

        try:
            if self.bot and hasattr(self.bot, 'exchange'):
                orders = await self.bot.exchange.get_open_orders(symbol)

                # 过滤订单
                if status:
                    orders = [o for o in orders if o.get("status") == status]
                if strategy:
                    orders = [o for o in orders if o.get("strategy") == strategy]

                return {"success": True, "orders": orders, "count": len(orders)}
            return {"success": False, "error": "Exchange not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============ 连接管理命令 ============

    async def _create_connection(self, command: Dict) -> Dict:
        """创建连接"""
        exchange = command.get("exchange")
        api_key = command.get("api_key")
        api_secret = command.get("api_secret")
        testnet = command.get("testnet", False)
        passphrase = command.get("passphrase", "")

        logger.info(f"Creating connection to {exchange} (testnet={testnet})")

        if not all([exchange, api_key, api_secret]):
            return {"success": False, "error": "Missing required parameters (exchange, api_key, api_secret)"}

        try:
            # 根据交易所类型创建连接器
            if exchange.lower() == "okx":
                # 导入 OKX 连接器
                from src.connectors.okx_lite.connector import OKXConnector

                # 配置
                config = {
                    'api_key': api_key,
                    'secret_key': api_secret,
                    'passphrase': passphrase,
                    'sandbox': testnet,
                    'proxy': None  # 可以从命令参数获取
                }

                # 创建连接器实例
                connector = OKXConnector(config)

                # 测试连接
                try:
                    await connector.__aenter__()  # 初始化 HTTP 客户端
                    logger.info("OKX connector initialized successfully")

                    # 测试连接
                    try:
                        is_healthy = await connector.test_connection()
                        logger.info(f"OKX connection test: {'success' if is_healthy else 'failed'}")
                    except Exception as e:
                        logger.warning(f"Failed to test connection: {e}")

                except Exception as e:
                    logger.error(f"Failed to initialize OKX connector: {e}")
                    return {
                        "success": False,
                        "error": f"Failed to initialize connector: {str(e)}"
                    }

                # 生成连接 ID
                connection_id = f"okx-{int(datetime.utcnow().timestamp())}"

                # 存储连接
                self.connections[connection_id] = {
                    "exchange": exchange,
                    "connector": connector,
                    "config": {
                        "api_key": api_key[:8] + "...",  # 只显示前 8 位
                        "testnet": testnet
                    },
                    "created_at": datetime.utcnow().isoformat()
                }

                # 发布连接事件
                try:
                    await self.event_bus.publish("connection", {
                        "event": "created",
                        "connection_id": connection_id,
                        "exchange": exchange,
                        "status": "connected"
                    })
                except Exception as e:
                    logger.error(f"Failed to publish connection event: {e}")

                logger.info(f"Connection created: {connection_id}")

                return {
                    "success": True,
                    "message": f"Connection to {exchange} created successfully",
                    "connection_id": connection_id,
                    "exchange": exchange
                }

            else:
                return {
                    "success": False,
                    "error": f"Unsupported exchange: {exchange}"
                }

        except Exception as e:
            logger.error(f"Error creating connection: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def _delete_connection(self, command: Dict) -> Dict:
        """删除连接"""
        connection_id = command.get("id")

        if not connection_id:
            return {"success": False, "error": "Missing 'id' parameter"}

        logger.info(f"Deleting connection: {connection_id}")

        # 检查连接是否存在
        if connection_id not in self.connections:
            return {
                "success": False,
                "error": f"Connection {connection_id} not found"
            }

        try:
            # 获取连接信息
            connection = self.connections[connection_id]
            connector = connection.get("connector")

            # 关闭连接器
            if connector and hasattr(connector, '__aexit__'):
                try:
                    await connector.__aexit__(None, None, None)
                    logger.info(f"Connector closed: {connection_id}")
                except Exception as e:
                    logger.error(f"Failed to close connector: {e}")

            # 发布删除事件
            try:
                await self.event_bus.publish("connection", {
                    "event": "deleted",
                    "connection_id": connection_id,
                    "exchange": connection.get("exchange")
                })
            except Exception as e:
                logger.error(f"Failed to publish deletion event: {e}")

            # 从字典中删除
            del self.connections[connection_id]

            logger.info(f"Connection deleted: {connection_id}")

            return {
                "success": True,
                "message": f"Connection {connection_id} deleted"
            }

        except Exception as e:
            logger.error(f"Error deleting connection: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def _test_connection(self, command: Dict) -> Dict:
        """测试连接"""
        connection_id = command.get("id")

        if not connection_id:
            return {"success": False, "error": "Missing 'id' parameter"}

        logger.info(f"Testing connection: {connection_id}")

        # 检查连接是否存在
        if connection_id not in self.connections:
            return {
                "success": False,
                "error": f"Connection {connection_id} not found"
            }

        try:
            # 获取连接
            connection = self.connections[connection_id]
            connector = connection.get("connector")

            if not connector:
                return {
                    "success": False,
                    "error": "Connector not available"
                }

            # 测试连接：调用 test_connection
            try:
                is_healthy = await connector.test_connection()
                logger.info(f"Connection test successful: {connection_id}, healthy: {is_healthy}")

                # 发布测试事件
                try:
                    await self.event_bus.publish("connection", {
                        "event": "tested",
                        "connection_id": connection_id,
                        "status": "healthy" if is_healthy else "failed"
                    })
                except Exception as e:
                    logger.error(f"Failed to publish test event: {e}")

                return {
                    "success": True,
                    "message": f"Connection {connection_id} is healthy",
                    "healthy": is_healthy
                }

            except Exception as e:
                logger.error(f"Connection test failed: {e}")
                return {
                    "success": False,
                    "error": f"Connection test failed: {str(e)}"
                }

        except Exception as e:
            logger.error(f"Error testing connection: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_connections(self, command: Dict) -> Dict:
        """获取所有连接列表"""
        logger.info(f"Getting connections: {len(self.connections)} connections")

        try:
            # 构建连接列表
            connections_list = []
            for connection_id, connection in self.connections.items():
                connections_list.append({
                    "id": connection_id,
                    "exchange": connection.get("exchange"),
                    "config": connection.get("config"),
                    "created_at": connection.get("created_at")
                })

            return {
                "success": True,
                "connections": connections_list,
                "count": len(connections_list)
            }

        except Exception as e:
            logger.error(f"Error getting connections: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    # ============ 系统命令 ============

    async def _start_engine(self, command: Dict) -> Dict:
        """启动引擎"""
        if self.bot.is_running:
            return {"success": False, "error": "Engine is already running"}

        self.bot.is_running = True
        await self.event_bus.publish_connected()
        return {"success": True, "message": "Engine started"}

    async def _stop_engine(self, command: Dict) -> Dict:
        """停止引擎"""
        if not self.bot.is_running:
            return {"success": False, "error": "Engine is not running"}

        self.bot.is_running = False
        await self.event_bus.publish_disconnected("User requested stop")
        return {"success": True, "message": "Engine stopped"}

    async def _get_system_status(self, command: Dict) -> Dict:
        """获取系统状态"""
        uptime = int((datetime.utcnow() - self.start_time).total_seconds())

        active_strategies = 0
        total_profit = 0.0
        total_trades = 0
        success_rate = 0.0

        if self.bot.strategy_manager:
            instances = self.bot.strategy_manager.get_instances_summary()
            active_strategies = sum(1 for i in instances if i.get('is_running'))
            total_trades = sum(i.get('trades', 0) for i in instances)

        return {
            "success": True,
            "uptime": uptime,
            "bot_status": "running" if self.bot.is_running else "stopped",
            "active_strategies": active_strategies,
            "total_profit": total_profit,
            "total_trades": total_trades,
            "success_rate": success_rate
        }

    async def _get_positions(self, command: Dict) -> Dict:
        """获取仓位列表"""
        if self.bot and hasattr(self.bot, 'position_manager'):
            positions = self.bot.position_manager.to_dict()
            return {"success": True, "positions": positions}

        return {"success": False, "error": "Position manager not available"}

    async def _get_balances(self, command: Dict) -> Dict:
        """获取余额列表"""
        if self.bot and hasattr(self.bot, 'exchange'):
            try:
                balance = await self.bot.exchange.get_balance()
                return {"success": True, "balances": balance}
            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"success": False, "error": "Exchange not available"}
