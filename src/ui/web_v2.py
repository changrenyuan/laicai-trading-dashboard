"""
Web 服务器 v2 - 事件驱动架构
提供统一的 Command API 和 WebSocket 接口
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 导入新组件
from ..core.event_bus import EventBus
from ..core.command_handler import CommandHandler
from ..core.state_persistence import StatePersistence
from .ws_manager import WebSocketManager


class WebServerV2:
    """
    Web 服务器 v2 - 事件驱动架构

    特点：
    1. 统一的 Command API (/api/command)
    2. WebSocket 推送所有事件
    3. 支持状态快照
    4. 前后端分离
    """

    def __init__(self, config: Dict, bot_instance, strategy_manager=None):
        """
        初始化 WebServer v2

        Args:
            config: 配置字典
            bot_instance: 机器人实例
            strategy_manager: 策略管理器（可选）
        """
        self.config = config
        self.bot = bot_instance
        self.strategy_manager = strategy_manager

        # 创建 FastAPI 应用
        self.app = FastAPI(title="Hummingbot Lite API v2")

        # 添加 CORS 中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 初始化核心组件
        self.event_bus = EventBus()
        self.state_persistence = StatePersistence()
        self.ws_manager = WebSocketManager(
            event_bus=self.event_bus,
            state_provider=self._get_state_snapshot
        )
        self.command_handler = CommandHandler(
            bot_instance=bot_instance,
            event_bus=self.event_bus,
            strategy_manager=strategy_manager
        )

        # 设置路由
        self._setup_routes()
        self._setup_websocket()

        logger.info("WebServer v2 初始化完成")

    def _setup_routes(self):
        """设置 API 路由"""

        @self.app.get("/")
        async def get_root():
            """API 根路径"""
            return {
                "service": "Hummingbot Lite Trading API",
                "version": "2.0.0",
                "architecture": "Event-Driven",
                "endpoints": {
                    "websocket": "/ws",
                    "command": "/api/command",
                    "state": "/api/state",
                    "health": "/api/health"
                },
                "supported_commands": [
                    "start_strategy",
                    "stop_strategy",
                    "place_order",
                    "cancel_order",
                    "cancel_all_orders",
                    "kill_switch",
                    "get_state"
                ]
            }

        @self.app.get("/api/health")
        async def health_check():
            """健康检查"""
            return {
                "status": "ok",
                "timestamp": datetime.utcnow().isoformat(),
                "active_clients": self.ws_manager.get_client_count()
            }

        @self.app.post("/api/command")
        async def handle_command(request: Request):
            """
            统一命令接口

            请求格式:
            {
                "cmd": "start_strategy",
                "params": {...}
            }
            """
            try:
                body = await request.json()
                cmd = body.get("cmd")
                params = body.get("params", {})

                if not cmd:
                    return JSONResponse(
                        {"error": "Missing 'cmd' field"},
                        status_code=400
                    )

                result = await self.command_handler.handle_command(cmd, params)
                return result

            except Exception as e:
                logger.error(f"Error handling command: {e}", exc_info=True)
                return JSONResponse(
                    {"error": str(e)},
                    status_code=500
                )

        @self.app.get("/api/state")
        async def get_state():
            """
            获取当前状态快照

            返回:
            {
                "strategies": [...],
                "orders": [...],
                "positions": [...],
                "balances": [...],
                "timestamp": "ISO 8601"
            }
            """
            try:
                state = await self._get_state_snapshot()
                return state
            except Exception as e:
                logger.error(f"Error getting state: {e}", exc_info=True)
                return JSONResponse(
                    {"error": str(e)},
                    status_code=500
                )

    def _setup_websocket(self):
        """设置 WebSocket"""

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """
            WebSocket 端点 - 用于接收实时事件

            连接流程：
            1. 客户端连接
            2. 发送当前状态快照
            3. 推送实时事件
            """
            client_id = await self.ws_manager.connect(websocket)

            try:
                # 保持连接并处理客户端消息
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)

                    # 处理客户端发送的消息
                    logger.info(f"Received WebSocket message from {client_id}: {message}")

                    # 可以在这里处理客户端的 ping/pong 等
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected: {client_id}")
            except Exception as e:
                logger.error(f"WebSocket error for client {client_id}: {e}", exc_info=True)
            finally:
                self.ws_manager.disconnect(client_id)

    async def _get_state_snapshot(self) -> Dict:
        """
        获取当前状态快照

        Returns:
            {
                "strategies": [...],
                "orders": [...],
                "positions": [...],
                "balances": [...],
                "timestamp": "ISO 8601"
            }
        """
        state = {
            "timestamp": datetime.utcnow().isoformat()
        }

        # 获取策略状态
        if self.strategy_manager:
            state["strategies"] = self.strategy_manager.get_instances_summary()
        elif self.bot.strategy:
            state["strategies"] = [{
                "id": self.bot.strategy.__class__.__name__,
                "status": "running" if self.bot.strategy.is_running else "stopped"
            }]
        else:
            state["strategies"] = []

        # 获取订单状态
        if hasattr(self.bot, 'exchange'):
            orders = await self.bot.exchange.get_open_orders()
            state["orders"] = [
                {
                    "orderId": order.get('order_id', order.get('id', '')),
                    "symbol": order.get('symbol', ''),
                    "side": order.get('side', ''),
                    "status": order.get('status', ''),
                    "filled": order.get('filled', 0),
                    "price": order.get('price', 0)
                }
                for order in orders
            ]
        else:
            state["orders"] = []

        # 获取仓位状态
        if hasattr(self.bot, 'position_manager'):
            positions_data = self.bot.position_manager.to_dict()
            open_positions = positions_data.get("open_positions", {})
            state["positions"] = [
                {
                    "symbol": pos.get('symbol', ''),
                    "size": pos.get('size', 0),
                    "pnl": pos.get('unrealized_pnl', 0),
                    "side": pos.get('side', 'long'),
                    "entry_price": pos.get('entry_price', 0)
                }
                for pos in open_positions.values()
            ]
        else:
            state["positions"] = []

        # 获取余额状态
        if hasattr(self.bot, 'exchange'):
            balance = await self.bot.exchange.get_balance()
            state["balances"] = [
                {
                    "currency": ccy,
                    "total": bal.get('total', 0),
                    "available": bal.get('available', 0)
                }
                for ccy, bal in balance.items()
            ]
        else:
            state["balances"] = []

        return state

    def run(self, host: str = "0.0.0.0", port: int = 5000):
        """运行服务器"""
        import uvicorn
        logger.info(f"Starting WebServer v2 on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)

    async def run_async(self, host: str = "0.0.0.0", port: int = 5000):
        """异步运行服务器"""
        import uvicorn
        config = uvicorn.Config(self.app, host=host, port=port)
        server = uvicorn.Server(config)
        await server.serve()
