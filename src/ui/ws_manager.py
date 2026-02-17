"""
WebSocket 管理器 - 统一管理 WebSocket 连接和事件推送
所有事件从 EventBus 发往 WebSocket 客户端
支持 snapshot 和多客户端
"""
import json
import logging
from typing import Set, Dict, Any, List
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from ..core.event_bus import EventBus

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    WebSocket 管理器

    功能：
    1. 管理多个 WebSocket 客户端连接
    2. 从 EventBus 订阅事件并推送给所有客户端
    3. 支持客户端重连时发送 snapshot
    4. 支持 client_id 标识不同客户端
    """

    def __init__(self, event_bus, state_provider=None):
        """
        初始化 WebSocket Manager

        Args:
            event_bus: 事件总线实例
            state_provider: 状态提供者函数（用于 snapshot）
        """
        self.event_bus = event_bus
        self.state_provider = state_provider

        # 活跃的 WebSocket 连接: {client_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # 客户端计数器
        self.client_counter = 0

        # 订阅 EventBus 事件
        self._subscribe_to_events()

    def _subscribe_to_events(self):
        """订阅 EventBus 的所有事件"""
        # 订阅所有事件类型
        self.event_bus.subscribe("price", self._broadcast_event)
        self.event_bus.subscribe("order_update", self._broadcast_event)
        self.event_bus.subscribe("position", self._broadcast_event)
        self.event_bus.subscribe("strategy", self._broadcast_event)
        self.event_bus.subscribe("log", self._broadcast_event)
        self.event_bus.subscribe("error", self._broadcast_event)
        self.event_bus.subscribe("snapshot", self._broadcast_event)

        logger.info("WebSocket Manager subscribed to EventBus events")

    async def connect(self, websocket: WebSocket, client_id: str = None) -> str:
        """
        接受新的 WebSocket 连接

        Args:
            websocket: WebSocket 连接对象
            client_id: 客户端 ID（可选，自动生成）

        Returns:
            客户端 ID
        """
        await websocket.accept()

        # 生成或使用提供的 client_id
        if not client_id:
            self.client_counter += 1
            client_id = f"client_{self.client_counter}"

        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")

        # 发送初始 snapshot
        await self._send_snapshot(client_id)

        return client_id

    def disconnect(self, client_id: str):
        """
        断开 WebSocket 连接

        Args:
            client_id: 客户端 ID
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client disconnected: {client_id}")

    async def _broadcast_event(self, event: Dict):
        """
        广播事件到所有客户端

        Args:
            event: 事件对象
        """
        if not self.active_connections:
            return

        message = json.dumps(event)

        # 发送给所有客户端
        disconnected_clients = []
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending to client {client_id}: {e}")
                disconnected_clients.append(client_id)

        # 移除断开的客户端
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    async def _send_snapshot(self, client_id: str):
        """
        发送状态快照给指定客户端

        Args:
            client_id: 客户端 ID
        """
        if client_id not in self.active_connections:
            return

        try:
            # 获取当前状态
            if self.state_provider:
                snapshot_data = await self.state_provider()
            else:
                snapshot_data = {"error": "No state provider configured"}

            # 构建快照事件
            snapshot_event = {
                "type": "snapshot",
                "timestamp": datetime.utcnow().isoformat(),
                **snapshot_data
            }

            # 发送快照
            await self.active_connections[client_id].send_text(json.dumps(snapshot_event))
            logger.info(f"Snapshot sent to client: {client_id}")

        except Exception as e:
            logger.error(f"Error sending snapshot to client {client_id}: {e}")

    async def send_to_client(self, client_id: str, message: Any):
        """
        发送消息给指定客户端

        Args:
            client_id: 客户端 ID
            message: 消息内容
        """
        if client_id not in self.active_connections:
            logger.warning(f"Client {client_id} not found")
            return

        try:
            if isinstance(message, dict):
                message = json.dumps(message)
            elif isinstance(message, (list, dict)):
                message = json.dumps(message)

            await self.active_connections[client_id].send_text(message)
        except Exception as e:
            logger.error(f"Error sending to client {client_id}: {e}")
            self.disconnect(client_id)

    def get_active_clients(self) -> List[str]:
        """获取活跃客户端列表"""
        return list(self.active_connections.keys())

    def get_client_count(self) -> int:
        """获取客户端数量"""
        return len(self.active_connections)

    async def broadcast_log(self, level: str, msg: str, logger_name: str = None):
        """
        广播日志消息（便捷方法）

        Args:
            level: 日志级别
            msg: 日志消息
            logger_name: 日志器名称
        """
        # 通过 EventBus 发布日志事件
        await self.event_bus.publish_log(level, msg, logger_name)
