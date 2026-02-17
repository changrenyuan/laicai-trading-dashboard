"""
Web 服务器 - 支持多策略实例管理
提供 REST API 和 WebSocket 接口
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import json
import logging
import sys
from datetime import datetime

logger = logging.getLogger(__name__)

# 导入 API 扩展
from .api_extension import APIExtension
# 导入命令处理器
from ..core.ws_command_handler import WSCommandHandler


class WebServer:
    """Web 服务器"""

    def __init__(self, config: Dict, bot_instance, ws_log_handler=None):
        self.config = config
        self.bot = bot_instance
        self.app = FastAPI(title="Hummingbot Lite")
        self.websocket_clients = []
        self.ws_log_handler = ws_log_handler

        # ✅ 添加 CORS 中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 允许所有来源（开发环境）
            allow_credentials=True,
            allow_methods=["*"],  # 允许所有方法
            allow_headers=["*"],  # 允许所有请求头
        )

        # 添加全局异常处理
        @self.app.exception_handler(Exception)
        async def global_exception_handler(request, exc):
            import traceback
            logger.error(f"Global exception caught: {exc}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "error": str(exc),
                "traceback": traceback.format_exc()
            }

        # 获取策略管理器（如果有）
        self.strategy_manager = getattr(bot_instance, 'strategy_manager', None)

        # 获取事件总线（如果有）
        self.event_bus = getattr(bot_instance, 'event_bus', None)

        # 初始化命令处理器
        self.command_handler = None
        if self.event_bus:
            self.command_handler = WSCommandHandler(bot_instance, self.event_bus)
            logger.info("WebSocket 命令处理器初始化完成")

        # 设置路由
        self._setup_routes()
        self._setup_websocket()

        # 初始化 API 扩展
        self.api_extension = APIExtension(
            self.app,
            bot_instance,
            self.strategy_manager,
            ws_log_handler
        )

        logger.info("Web 服务器初始化完成，API 扩展已加载")

    def _setup_routes(self):
        """设置 API 路由"""

        @self.app.get("/")
        async def get_root():
            """API 根路径"""
            return {
                "service": "Hummingbot Lite Trading API",
                "version": "2.0.0",
                "endpoints": {
                    "websocket": "/ws",
                    "api_stream": "/api/stream",
                    "logs_websocket": "/ws/logs",
                    "command": "/api/command",
                    "state": "/api/state",
                    "health": "/api/health"
                }
            }

        # ============ 基础接口 ============

        @self.app.get("/api/health")
        async def health_check():
            """健康检查"""
            return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
            """获取机器人状态"""
            return {
                "status": "running" if self.bot.is_running else "stopped",
                "strategy": self.bot.strategy.get_status() if self.bot.strategy else None,
                "positions": self.bot.position_manager.to_dict(),
                "risk": self.bot.risk_manager.to_dict(),
                "exchange": self.bot.exchange.to_dict(),
                "timestamp": datetime.utcnow().isoformat()
            }

        @self.app.get("/api/balance")
        async def get_balance():
            """获取账户余额"""
            try:
                balance = await self.bot.exchange.get_balance()
                return {"balance": balance, "timestamp": datetime.utcnow().isoformat()}
            except Exception as e:
                import traceback
                print(f"Exception caught: {e}", file=sys.stderr)
                print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
                error_details = {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
                return error_details

        @self.app.get("/api/orders")
        async def get_orders():
            """获取订单列表"""
            try:
                symbol = self.bot.strategy.trading_pair if self.bot.strategy else None
                orders = await self.bot.exchange.get_open_orders(symbol)
                return {"orders": orders, "count": len(orders)}
            except Exception as e:
                import traceback
                print(f"Exception caught: {e}", file=sys.stderr)
                print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
                error_details = {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
                return error_details

        @self.app.post("/api/start")
        async def start_strategy():
            """启动策略"""
            try:
                if self.bot.strategy and not self.bot.strategy.is_running:
                    await self.bot.strategy.start()
                    return {"status": "started", "message": "Strategy started"}
                return {"status": "error", "message": "Strategy already running or not initialized"}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        @self.app.post("/api/stop")
        async def stop_strategy():
            """停止策略"""
            try:
                if self.bot.strategy and self.bot.strategy.is_running:
                    await self.bot.strategy.stop()
                    return {"status": "stopped", "message": "Strategy stopped"}
                return {"status": "error", "message": "Strategy not running"}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        @self.app.post("/api/cancel-all-orders")
        async def cancel_all_orders():
            """取消所有订单"""
            try:
                symbol = self.bot.strategy.trading_pair if self.bot.strategy else None
                cancelled = await self.bot.exchange.cancel_all_orders(symbol)
                return {"cancelled": cancelled, "message": f"Cancelled {cancelled} orders"}
            except Exception as e:
                import traceback
                print(f"Exception caught: {e}", file=sys.stderr)
                print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
                error_details = {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
                return error_details

        # ============ 多策略管理接口 ============

        @self.app.get("/api/strategies")
        async def get_available_strategies():
            """获取可用策略列表"""
            if not self.strategy_manager:
                return {"strategies": []}

            strategies = self.strategy_manager.get_available_strategies()
            return {"strategies": strategies}

        @self.app.get("/api/strategy-instances")
        async def get_strategy_instances():
            """获取所有策略实例"""
            if not self.strategy_manager:
                return {"instances": []}

            instances = self.strategy_manager.get_instances_summary()
            return {"instances": instances}

        @self.app.get("/api/strategy-instances/{instance_id}")
        async def get_strategy_instance(instance_id: str):
            """获取指定策略实例详情"""
            if not self.strategy_manager:
                return {"error": "Strategy manager not available"}

            instance = self.strategy_manager.get_strategy_instance(instance_id)
            if not instance:
                return {"error": "Instance not found"}

            return {
                "instance_id": instance.instance_id,
                "strategy_name": instance.strategy_name,
                "config": instance.config,
                "is_running": instance.is_running,
                "created_at": instance.created_at,
                "last_active": instance.last_active,
                "status": instance.strategy.get_status() if instance.strategy else {}
            }

        @self.app.post("/api/strategy-instances")
        async def create_strategy_instance(request: dict):
            """创建策略实例"""
            print(f"create_strategy_instance called", file=sys.stderr)
            logger.info(f"create_strategy_instance called: {request}")
            if not self.strategy_manager:
                print(f"Strategy manager not available", file=sys.stderr)
                return {"error": "Strategy manager not available"}

            print(f"About to enter try block", file=sys.stderr)
            try:
                print(f"In try block, getting strategy_name", file=sys.stderr)
                strategy_name = request.get('strategy_name')
                config = request.get('config', {})
                instance_name = request.get('instance_name')

                print(f"strategy_name: {strategy_name}", file=sys.stderr)
                if not strategy_name:
                    return {"error": "strategy_name is required"}

                print(f"About to call create_strategy_instance", file=sys.stderr)
                instance = await self.strategy_manager.create_strategy_instance(
                    strategy_name=strategy_name,
                    config=config,
                    instance_name=instance_name
                )
                print(f"Strategy instance created successfully", file=sys.stderr)

                return {
                    "instance_id": instance.instance_id,
                    "strategy_name": instance.strategy_name,
                    "message": "Strategy instance created"
                }

            except Exception as e:
                import traceback
                print(f"Exception caught: {e}", file=sys.stderr)
                print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
                error_details = {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
                return error_details

        @self.app.post("/api/strategy-instances/{instance_id}/start")
        async def start_strategy_instance(instance_id: str):
            """启动策略实例"""
            if not self.strategy_manager:
                return {"error": "Strategy manager not available"}

            success = await self.strategy_manager.start_strategy(instance_id)
            if success:
                return {"status": "started", "instance_id": instance_id}
            return {"error": "Failed to start strategy instance"}

        @self.app.post("/api/strategy-instances/{instance_id}/stop")
        async def stop_strategy_instance(instance_id: str):
            """停止策略实例"""
            if not self.strategy_manager:
                return {"error": "Strategy manager not available"}

            success = await self.strategy_manager.stop_strategy(instance_id)
            if success:
                return {"status": "stopped", "instance_id": instance_id}
            return {"error": "Failed to stop strategy instance"}

        @self.app.delete("/api/strategy-instances/{instance_id}")
        async def delete_strategy_instance(instance_id: str):
            """删除策略实例"""
            if not self.strategy_manager:
                return {"error": "Strategy manager not available"}

            success = await self.strategy_manager.delete_strategy_instance(instance_id)
            if success:
                return {"status": "deleted", "instance_id": instance_id}
            return {"error": "Failed to delete strategy instance"}

        @self.app.put("/api/strategy-instances/{instance_id}/config")
        async def update_strategy_instance_config(instance_id: str, request: dict):
            """更新策略实例配置"""
            if not self.strategy_manager:
                return {"error": "Strategy manager not available"}

            success = await self.strategy_manager.update_strategy_config(
                instance_id,
                request.get('config', {})
            )

            if success:
                return {"status": "updated", "instance_id": instance_id}
            return {"error": "Failed to update strategy config"}

        # ============ Kill Switch 端点 ============
        @self.app.post("/api/kill-switch")
        async def kill_switch():
            """紧急停止所有策略并撤销所有订单"""
            logger.warning("Kill Switch triggered!")
            if not self.strategy_manager:
                return {"error": "Strategy manager not available"}

            try:
                # 1. 停止所有运行中的策略
                instances = self.strategy_manager.get_instances_summary()
                stopped_count = 0
                cancelled_count = 0

                for instance in instances:
                    if instance.get('is_running'):
                        await self.strategy_manager.stop_strategy(instance['instance_id'])
                        stopped_count += 1

                # 2. 撤销所有订单
                if self.bot and hasattr(self.bot, 'exchange'):
                    cancelled_count = await self.bot.exchange.cancel_all_orders()

                logger.error(f"Kill Switch executed: stopped {stopped_count} strategies, cancelled {cancelled_count} orders")

                return {
                    "status": "kill_switch_activated",
                    "stopped_strategies": stopped_count,
                    "cancelled_orders": cancelled_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Kill Switch failed: {e}")
                return {"error": f"Kill Switch failed: {str(e)}"}

    def _setup_websocket(self):
        """设置 WebSocket"""

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """通用 WebSocket 端点 - 用于事件广播"""
            await websocket.accept()
            self.websocket_clients.append(websocket)
            logger.info("WebSocket client connected to /ws")

            # 如果有事件总线，订阅所有事件并推送给客户端
            if self.event_bus:
                # 先发送连接成功事件
                try:
                    await self.event_bus.publish_connected()
                except Exception as e:
                    logger.error(f"Failed to publish connected event: {e}", exc_info=True)

                # 订阅事件总线并推送给客户端
                async def event_forwarder(event):
                    try:
                        # 检查连接是否还活着
                        if websocket.client_state.name != 'CONNECTED':
                            logger.debug(f"WebSocket is not connected (state: {websocket.client_state.name}), skipping event")
                            return

                        message = json.dumps(event, ensure_ascii=False)
                        await websocket.send_text(message)
                        logger.debug(f"Event sent to client: {event.get('type')}")
                    except Exception as e:
                        logger.error(f"Failed to send event to client: {e}", exc_info=True)

                # 订阅所有事件类型
                event_types = [
                    "connected", "disconnected", "system_status",
                    "price", "order_update", "trade", "position", "balance",
                    "strategy", "log", "connection", "error", "snapshot"
                ]
                for event_type in event_types:
                    self.event_bus.subscribe(event_type, event_forwarder)
                    logger.debug(f"Subscribed to event type: {event_type}")

                # 发送连接成功事件
                try:
                    await self.event_bus.publish_connected()
                except Exception as e:
                    logger.error(f"Failed to publish connected event: {e}", exc_info=True)

            try:
                while True:
                    data = await websocket.receive_text()
                    logger.debug(f"Received message from client: {data}")

                    # 处理客户端发送的消息
                    try:
                        message = json.loads(data)
                        logger.debug(f"Parsed message: {message}")

                        # 处理心跳消息
                        if message.get("type") == "ping":
                            logger.debug("Received ping, sending pong")
                            await websocket.send_text(json.dumps({"type": "pong"}))
                            continue

                        # 处理命令
                        command = message
                        if self.command_handler:
                            response = await self.command_handler.handle_command(command)
                            await websocket.send_text(json.dumps(response))
                            logger.debug(f"Command response sent: {response.get('success')}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON received: {data}, error: {e}")
                    except Exception as e:
                        logger.error(f"Error handling WebSocket message: {e}", exc_info=True)

            except WebSocketDisconnect as e:
                self.websocket_clients.remove(websocket)
                logger.info(f"WebSocket client disconnected from /ws (code: {e.code}, reason: {e.reason})")
            except Exception as e:
                logger.error(f"WebSocket error: {e}", exc_info=True)
                if websocket in self.websocket_clients:
                    self.websocket_clients.remove(websocket)

        @self.app.websocket("/api/stream")
        async def api_stream_endpoint(websocket: WebSocket):
            """API Stream WebSocket 端点 - 用于事件广播（兼容客户端）"""
            await websocket.accept()
            self.websocket_clients.append(websocket)
            logger.info("WebSocket client connected to /api/stream")

            # 如果有事件总线，订阅所有事件并推送给客户端
            if self.event_bus:
                # 先发送连接成功事件
                try:
                    await self.event_bus.publish_connected()
                except Exception as e:
                    logger.error(f"Failed to publish connected event: {e}", exc_info=True)

                # 订阅事件总线并推送给客户端
                async def event_forwarder(event):
                    try:
                        # 检查连接是否还活着
                        if websocket.client_state.name != 'CONNECTED':
                            logger.debug(f"WebSocket is not connected (state: {websocket.client_state.name}), skipping event")
                            return

                        message = json.dumps(event, ensure_ascii=False)
                        await websocket.send_text(message)
                        logger.debug(f"Event sent to client: {event.get('type')}")
                    except Exception as e:
                        logger.error(f"Failed to send event to client: {e}", exc_info=True)

                # 订阅所有事件类型
                event_types = [
                    "connected", "disconnected", "system_status",
                    "price", "order_update", "trade", "position", "balance",
                    "strategy", "log", "connection", "error", "snapshot"
                ]
                for event_type in event_types:
                    self.event_bus.subscribe(event_type, event_forwarder)
                    logger.debug(f"Subscribed to event type: {event_type}")

                # 发送连接成功事件
                try:
                    await self.event_bus.publish_connected()
                except Exception as e:
                    logger.error(f"Failed to publish connected event: {e}", exc_info=True)

            try:
                while True:
                    data = await websocket.receive_text()
                    logger.debug(f"Received message from client: {data}")

                    # 处理客户端发送的消息
                    try:
                        message = json.loads(data)
                        logger.debug(f"Parsed message: {message}")

                        # 处理心跳消息
                        if message.get("type") == "ping":
                            logger.debug("Received ping, sending pong")
                            await websocket.send_text(json.dumps({"type": "pong"}))
                            continue

                        # 处理命令
                        command = message
                        if self.command_handler:
                            response = await self.command_handler.handle_command(command)
                            await websocket.send_text(json.dumps(response))
                            logger.debug(f"Command response sent: {response.get('success')}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON received: {data}, error: {e}")
                    except Exception as e:
                        logger.error(f"Error handling WebSocket message: {e}", exc_info=True)

            except WebSocketDisconnect as e:
                self.websocket_clients.remove(websocket)
                logger.info(f"WebSocket client disconnected from /api/stream (code: {e.code}, reason: {e.reason})")
            except Exception as e:
                logger.error(f"WebSocket error: {e}", exc_info=True)
                if websocket in self.websocket_clients:
                    self.websocket_clients.remove(websocket)

        @self.app.websocket("/ws/logs")
        async def logs_websocket_endpoint(websocket: WebSocket):
            """日志 WebSocket 端点 - 用于实时日志推送"""
            await websocket.accept()
            
            # 将客户端添加到日志处理器
            if self.ws_log_handler:
                self.ws_log_handler.add_client(websocket)
            
            try:
                # 发送最近的日志给新连接的客户端
                if self.ws_log_handler:
                    recent_logs = self.ws_log_handler.get_recent_logs(100)
                    for log_entry in recent_logs:
                        await websocket.send_text(json.dumps(log_entry))
                
                # 保持连接并处理客户端消息
                while True:
                    data = await websocket.receive_text()
                    # 可以处理客户端发送的消息（例如过滤日志级别）
                    logger.info(f"Received logs WebSocket message: {data}")
            except WebSocketDisconnect:
                if self.ws_log_handler:
                    self.ws_log_handler.remove_client(websocket)
                logger.info("Logs WebSocket client disconnected")

    async def broadcast_event(self, event_type: str, data: dict):
        """广播事件到所有 WebSocket 客户端"""
        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        })

        for client in self.websocket_clients[:]:
            try:
                await client.send_text(message)
            except Exception as e:
                self.websocket_clients.remove(client)
                logger.error(f"Failed to send message to client: {e}")

    async def run_async(self, host: str = "0.0.0.0", port: int = 5000):
        """异步运行服务器"""
        import uvicorn

        config = uvicorn.Config(self.app, host=host, port=port)
        server = uvicorn.Server(config)
        await server.serve()

    def run(self, host: str = "0.0.0.0", port: int = 5000):
        """运行服务器"""
        import uvicorn

        logger.info(f"Starting web server on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)

