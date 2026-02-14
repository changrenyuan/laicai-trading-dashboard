"""
日志 WebSocket 处理器
将日志实时推送到前端
"""
import logging
import json
import asyncio
from typing import List
from datetime import datetime


class WebSocketLogHandler(logging.Handler):
    """WebSocket 日志处理器"""

    def __init__(self):
        super().__init__()
        self.websocket_clients: List = []
        self.log_buffer: List[dict] = []
        self.max_buffer_size = 1000  # 最多保存 1000 条日志

    def add_client(self, websocket):
        """添加 WebSocket 客户端"""
        self.websocket_clients.append(websocket)

    def remove_client(self, websocket):
        """移除 WebSocket 客户端"""
        if websocket in self.websocket_clients:
            self.websocket_clients.remove(websocket)

    def emit(self, record):
        """发送日志消息"""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno
            }

            # 添加到缓冲区
            self.log_buffer.append(log_entry)
            if len(self.log_buffer) > self.max_buffer_size:
                self.log_buffer.pop(0)

            # 异步推送到所有客户端
            asyncio.create_task(self._broadcast_log(log_entry))
        except Exception as e:
            pass

    async def _broadcast_log(self, log_entry: dict):
        """广播日志到所有客户端"""
        if not self.websocket_clients:
            return

        message = json.dumps(log_entry)
        disconnected_clients = []

        for client in self.websocket_clients:
            try:
                await client.send_text(message)
            except Exception as e:
                disconnected_clients.append(client)

        # 移除断开的客户端
        for client in disconnected_clients:
            self.remove_client(client)

    def get_recent_logs(self, count: int = 100) -> List[dict]:
        """获取最近的日志"""
        return self.log_buffer[-count:]


# 全局日志处理器
ws_log_handler = WebSocketLogHandler()


def setup_websocket_logging(level: str = "INFO"):
    """设置 WebSocket 日志"""
    ws_log_handler.setLevel(getattr(logging, level.upper()))
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.addHandler(ws_log_handler)
    
    return ws_log_handler
