"""
Web 服务器
提供 REST API 和 WebSocket 接口
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class WebServer:
    """Web 服务器"""

    def __init__(self, config: Dict, bot_instance):
        self.config = config
        self.bot = bot_instance
        self.app = FastAPI(title="Hummingbot Lite")
        self.websocket_clients = []

        # 设置路由
        self._setup_routes()
        self._setup_websocket()

    def _setup_routes(self):
        """设置 API 路由"""

        @self.app.get("/")
        async def get_root():
            """API 根路径"""
            return {
                "service": "Hummingbot Lite Trading API",
                "version": "1.0.0",
                "endpoints": {
                    "websocket": "/ws",
                    "status": "/api/status",
                    "health": "/api/health"
                }
            }

        @self.app.get("/api/health")
        async def health_check():
            """健康检查"""
            return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

        @self.app.get("/api/status")
        async def get_status():
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
                return {"error": str(e)}

        @self.app.get("/api/orders")
        async def get_orders():
            """获取订单列表"""
            try:
                symbol = self.bot.strategy.trading_pair if self.bot.strategy else None
                orders = await self.bot.exchange.get_open_orders(symbol)
                return {"orders": orders, "count": len(orders)}
            except Exception as e:
                return {"error": str(e)}

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
                return {"error": str(e)}

        @self.app.get("/api/events")
        async def get_events(event_type: str = None, limit: int = 50):
            """获取事件历史"""
            events = self.bot.event_bus.get_event_history(event_type, limit)
            return {"events": events, "count": len(events)}

        @self.app.get("/api/performance")
        async def get_performance():
            """获取策略表现"""
            if self.bot.strategy and hasattr(self.bot.strategy, 'get_performance'):
                perf = self.bot.strategy.get_performance()
                return {"performance": perf}
            return {"performance": {}}

    def _setup_websocket(self):
        """设置 WebSocket"""

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket 端点"""
            await websocket.accept()
            self.websocket_clients.append(websocket)

            try:
                # 发送初始状态
                await self._broadcast_status()

                while True:
                    # 接收客户端消息
                    data = await websocket.receive_text()
                    message = json.loads(data)

                    # 处理消息
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                self.websocket_clients.remove(websocket)
                logger.info("WebSocket client disconnected")
            except Exception as e:
                logger.error(f"WebSocket error: {e}", exc_info=True)

    async def _broadcast_status(self):
        """广播状态到所有 WebSocket 客户端"""
        if not self.websocket_clients:
            return

        status = {
            "type": "status_update",
            "data": {
                "status": "running" if self.bot.is_running else "stopped",
                "strategy": self.bot.strategy.get_status() if self.bot.strategy else None,
                "positions": self.bot.position_manager.to_dict(),
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        # 发送给所有客户端
        disconnected_clients = []
        for client in self.websocket_clients:
            try:
                await client.send_json(status)
            except Exception:
                disconnected_clients.append(client)

        # 移除断开的客户端
        for client in disconnected_clients:
            self.websocket_clients.remove(client)

    async def broadcast_event(self, event_type: str, event_data: Dict):
        """广播事件到所有 WebSocket 客户端"""
        if not self.websocket_clients:
            return

        message = {
            "type": "event",
            "event_type": event_type,
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat()
        }

        disconnected_clients = []
        for client in self.websocket_clients:
            try:
                await client.send_json(message)
            except Exception:
                disconnected_clients.append(client)

        for client in disconnected_clients:
            self.websocket_clients.remove(client)

