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

        @self.app.get("/", response_class=HTMLResponse)
        async def get_dashboard():
            """获取仪表板页面"""
            html_content = self._get_dashboard_html()
            return HTMLResponse(content=html_content)

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

    def _get_dashboard_html(self) -> str:
        """获取仪表板 HTML"""
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hummingbot Lite - 量化交易机器人</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 20px 30px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header h1 {
            font-size: 24px;
            color: #667eea;
            margin-bottom: 8px;
        }
        .header .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }
        .status.running { background: #4caf50; color: white; }
        .status.stopped { background: #f44336; color: white; }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .card h2 {
            font-size: 16px;
            color: #667eea;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }

        .metric {
            display: flex;
            justify-content: space-between;
            margin-bottom: 12px;
            font-size: 14px;
        }

        .metric .label { color: #999; }
        .metric .value { font-weight: bold; color: #333; }
        .metric .value.positive { color: #4caf50; }
        .metric .value.negative { color: #f44336; }

        .controls {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }

        .btn {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn.start { background: #4caf50; color: white; }
        .btn.stop { background: #f44336; color: white; }
        .btn.cancel { background: #ff9800; color: white; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }

        .log {
            background: #1a1a2e;
            color: #0f0;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            height: 300px;
            overflow-y: auto;
        }

        .log-entry { margin-bottom: 5px; }
        .log-entry .time { color: #888; margin-right: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Hummingbot Lite - 量化交易机器人</h1>
            <span class="status" id="status">stopped</span>
            <span style="margin-left: 15px; color: #999; font-size: 14px;">
                OKX 做市策略
            </span>
        </div>

        <div class="grid">
            <!-- 策略状态 -->
            <div class="card">
                <h2>📊 策略状态</h2>
                <div class="metric">
                    <span class="label">交易对</span>
                    <span class="value" id="trading-pair">-</span>
                </div>
                <div class="metric">
                    <span class="label">当前价格</span>
                    <span class="value" id="current-price">-</span>
                </div>
                <div class="metric">
                    <span class="label">活动订单</span>
                    <span class="value" id="active-orders">-</span>
                </div>
                <div class="metric">
                    <span class="label">总订单数</span>
                    <span class="value" id="total-orders">-</span>
                </div>
                <div class="controls">
                    <button class="btn start" onclick="startStrategy()">▶ 启动</button>
                    <button class="btn stop" onclick="stopStrategy()">⏹ 停止</button>
                    <button class="btn cancel" onclick="cancelOrders()">❌ 取消所有订单</button>
                </div>
            </div>

            <!-- 仓位信息 -->
            <div class="card">
                <h2>💰 仓位信息</h2>
                <div class="metric">
                    <span class="label">开仓数量</span>
                    <span class="value" id="open-positions">-</span>
                </div>
                <div class="metric">
                    <span class="label">已实现盈亏</span>
                    <span class="value" id="realized-pnl">-</span>
                </div>
                <div class="metric">
                    <span class="label">未实现盈亏</span>
                    <span class="value" id="unrealized-pnl">-</span>
                </div>
                <div class="metric">
                    <span class="label">总盈亏</span>
                    <span class="value" id="total-pnl">-</span>
                </div>
            </div>

            <!-- 风控状态 -->
            <div class="card">
                <h2>🛡️ 风控状态</h2>
                <div class="metric">
                    <span class="label">最大仓位限制</span>
                    <span class="value" id="max-position">-</span>
                </div>
                <div class="metric">
                    <span class="label">每日亏损</span>
                    <span class="value" id="daily-loss">-</span>
                </div>
                <div class="metric">
                    <span class="label">止损订单</span>
                    <span class="value" id="stop-orders">-</span>
                </div>
                <div class="metric">
                    <span class="label">止盈订单</span>
                    <span class="value" id="tp-orders">-</span>
                </div>
            </div>

            <!-- 账户余额 -->
            <div class="card">
                <h2>💎 账户余额</h2>
                <div class="metric">
                    <span class="label">USDT</span>
                    <span class="value" id="balance-usdt">-</span>
                </div>
                <div class="metric">
                    <span class="label">BTC</span>
                    <span class="value" id="balance-btc">-</span>
                </div>
            </div>
        </div>

        <!-- 事件日志 -->
        <div class="card">
            <h2>📋 实时日志</h2>
            <div class="log" id="event-log"></div>
        </div>
    </div>

    <script>
        let ws;
        let reconnectTimer;

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

            ws.onopen = () => {
                console.log('WebSocket connected');
                addLog('系统', 'WebSocket 已连接');
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'status_update') {
                    updateDashboard(data.data);
                } else if (data.type === 'event') {
                    addLog(data.event_type, JSON.stringify(data.data));
                }
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected');
                addLog('系统', 'WebSocket 断开连接，尝试重连...');
                reconnectTimer = setTimeout(connectWebSocket, 3000);
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        }

        function updateDashboard(data) {
            // 状态
            const statusEl = document.getElementById('status');
            statusEl.textContent = data.status;
            statusEl.className = 'status ' + data.status;

            // 策略
            if (data.strategy) {
                document.getElementById('trading-pair').textContent = data.strategy.config.trading_pair || '-';
                document.getElementById('current-price').textContent = data.strategy.config.order_amount ? '运行中' : '-';
                document.getElementById('active-orders').textContent = data.strategy.active_orders_count || 0;
                document.getElementById('total-orders').textContent = '-';
            }

            // 仓位
            if (data.positions) {
                const positions = data.positions.open_positions || {};
                document.getElementById('open-positions').textContent = Object.keys(positions).length;

                const realizedPnl = data.positions.total_realized_pnl || 0;
                const unrealizedPnl = data.positions.total_unrealized_pnl || 0;
                const totalPnl = realizedPnl + unrealizedPnl;

                document.getElementById('realized-pnl').textContent = formatPnL(realizedPnl);
                document.getElementById('unrealized-pnl').textContent = formatPnL(unrealizedPnl);
                document.getElementById('total-pnl').textContent = formatPnL(totalPnl);
            }
        }

        function formatPnL(value) {
            const formatted = value.toFixed(4);
            return value >= 0 ? `<span class="positive">+${formatted}</span>` : `<span class="negative">${formatted}</span>`;
        }

        function addLog(type, message) {
            const log = document.getElementById('event-log');
            const time = new Date().toLocaleTimeString('zh-CN');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `<span class="time">[${time}]</span><strong>${type}:</strong> ${message}`;
            log.appendChild(entry);
            log.scrollTop = log.scrollHeight;

            // 限制日志数量
            while (log.children.length > 100) {
                log.removeChild(log.firstChild);
            }
        }

        async function apiCall(endpoint, method = 'GET') {
            try {
                const options = { method };
                const response = await fetch(endpoint, options);
                return await response.json();
            } catch (error) {
                console.error('API call failed:', error);
                addLog('错误', 'API 调用失败: ' + error.message);
                return { error: error.message };
            }
        }

        async function startStrategy() {
            const result = await apiCall('/api/start', 'POST');
            if (result.status === 'started') {
                addLog('策略', '策略已启动');
            } else {
                addLog('错误', result.message || '启动失败');
            }
        }

        async function stopStrategy() {
            const result = await apiCall('/api/stop', 'POST');
            if (result.status === 'stopped') {
                addLog('策略', '策略已停止');
            } else {
                addLog('错误', result.message || '停止失败');
            }
        }

        async function cancelOrders() {
            const result = await apiCall('/api/cancel-all-orders', 'POST');
            if (!result.error) {
                addLog('订单', `已取消 ${result.cancelled} 个订单`);
            } else {
                addLog('错误', result.error);
            }
        }

        // 定期刷新数据
        async function refreshData() {
            const status = await apiCall('/api/status');
            if (!status.error) {
                updateDashboard(status);
            }
        }

        // 初始化
        connectWebSocket();
        setInterval(refreshData, 5000);
        addLog('系统', 'Hummingbot Lite 已启动');
    </script>
</body>
</html>
        """

    def run(self, host: str = "0.0.0.0", port: int = 5000):
        """运行服务器"""
        import uvicorn
        logger.info(f"Starting web server on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)
