"""
Web 服务器 - 支持多策略实例管理
提供 REST API 和 WebSocket 接口
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, List, Optional
import json
import logging
import sys
from datetime import datetime

logger = logging.getLogger(__name__)


class WebServer:
    """Web 服务器"""

    def __init__(self, config: Dict, bot_instance, ws_log_handler=None):
        self.config = config
        self.bot = bot_instance
        self.app = FastAPI(title="Hummingbot Lite")
        self.websocket_clients = []
        self.ws_log_handler = ws_log_handler

        # 添加全局异常处理
        @self.app.exception_handler(Exception)
        async def global_exception_handler(request, exc):
            print(f"Global exception caught: {exc}", file=sys.stderr)
            print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
            import traceback
            return {
                "error": str(exc),
                "traceback": traceback.format_exc()
            }

        # 获取策略管理器（如果有）
        self.strategy_manager = getattr(bot_instance, 'strategy_manager', None)

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

        # ============ 基础接口 ============

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

            try:
                while True:
                    data = await websocket.receive_text()
                    # 可以处理客户端发送的消息
                    logger.info(f"Received WebSocket message: {data}")

            except WebSocketDisconnect:
                self.websocket_clients.remove(websocket)
                logger.info("WebSocket client disconnected")

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

    def _get_dashboard_html(self) -> str:
        """获取仪表板 HTML"""
        # 这里返回 HTML 内容
        # 为了支持多策略，我需要更新 HTML
        html_content = self._get_multi_strategy_dashboard_html()
        return html_content

    def _get_multi_strategy_dashboard_html(self) -> str:
        """获取多策略仪表板 HTML"""
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hummingbot Lite - 多策略管理</title>
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
            max-width: 1600px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .card h2 {
            font-size: 1.2em;
            margin-bottom: 15px;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .status-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .status-running {
            border-left: 4px solid #10b981;
        }
        .status-stopped {
            border-left: 4px solid #ef4444;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
            margin: 2px;
        }
        .btn-primary {
            background: #667eea;
            color: white;
        }
        .btn-success {
            background: #10b981;
            color: white;
        }
        .btn-danger {
            background: #ef4444;
            color: white;
        }
        .btn:hover {
            opacity: 0.9;
            transform: translateY(-1px);
        }
        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        .stat-label {
            color: #666;
        }
        .stat-value {
            font-weight: 600;
            color: #333;
        }
        .create-strategy-section {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
        }
        .form-group select,
        .form-group input,
        .form-group textarea {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }
        .strategy-list {
            max-height: 600px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Hummingbot Lite</h1>
            <p>多策略量化交易管理平台</p>
        </div>

        <div class="create-strategy-section">
            <h2>🎯 创建新策略实例</h2>
            <div class="form-group">
                <label>选择策略类型</label>
                <select id="strategyType">
                    <option value="">-- 请选择 --</option>
                    <option value="market_maker">Market Maker (经典做市)</option>
                    <option value="pure_market_making">Pure Market Making (现货做市)</option>
                    <option value="perpetual_market_making">Perpetual Market Making (永续做市)</option>
                    <option value="spot_perpetual_arbitrage">Spot-Perpetual Arbitrage (套利)</option>
                    <option value="amm_arbitrage">AMM Arbitrage (AMM套利)</option>
                    <option value="avellaneda_market_making">Avellaneda Market Making (Avellaneda做市)</option>
                    <option value="cross_exchange_market_making">Cross-Exchange Market Making (跨所做市)</option>
                    <option value="liquidity_mining">Liquidity Mining (流动性挖矿)</option>
                    <option value="hedge">Hedge (对冲)</option>
                    <option value="cross_exchange_mining">Cross-Exchange Mining (跨所挖矿)</option>
                </select>
            </div>
            <div class="form-group">
                <label>策略配置 (YAML)</label>
                <textarea id="strategyConfig" rows="10" placeholder="输入策略配置..."></textarea>
            </div>
            <button class="btn btn-primary" onclick="createStrategy()">创建策略</button>
        </div>

        <h2 style="color: white; margin-bottom: 20px;">📊 策略实例列表</h2>
        <div class="strategy-list" id="strategyInstances">
            <div style="text-align: center; padding: 40px; color: white;">
                加载中...
            </div>
        </div>

        <div class="card" style="margin-top: 30px;">
            <h2>📋 事件日志</h2>
            <div id="eventLog" style="max-height: 300px; overflow-y: auto; font-family: monospace; font-size: 12px;">
                <div style="color: #666; padding: 10px;">等待事件...</div>
            </div>
        </div>
    </div>

    <script>
        let ws;
        let instances = [];

        function connectWebSocket() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            ws.onopen = () => console.log('WebSocket connected');
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                logEvent(data.type, data.data);
            };
            ws.onclose = () => {
                console.log('WebSocket disconnected, reconnecting...');
                setTimeout(connectWebSocket, 3000);
            };
        }

        function logEvent(type, data) {
            const log = document.getElementById('eventLog');
            const time = new Date().toLocaleTimeString();
            const message = JSON.stringify(data, null, 2);
            log.innerHTML = `<div style="padding: 5px; border-bottom: 1px solid #eee;">
                <span style="color: #667eea;">[${time}]</span>
                <span style="color: #10b981;">${type}</span>
                <pre style="margin: 5px 0;">${message}</pre>
            </div>` + log.innerHTML;
        }

        async function loadInstances() {
            const response = await fetch('/api/strategy-instances');
            const result = await response.json();
            instances = result.instances || [];
            renderInstances();
        }

        function renderInstances() {
            const container = document.getElementById('strategyInstances');

            if (instances.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: white;">
                        <h3>暂无策略实例</h3>
                        <p>点击上方创建您的第一个策略实例</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = `
                <div class="cards-grid">
                    ${instances.map(instance => `
                        <div class="status-card ${instance.is_running ? 'status-running' : 'status-stopped'}">
                            <h2 style="display: flex; justify-content: space-between; align-items: center;">
                                <span>${instance.strategy_name.replace(/_/g, ' ')}</span>
                                <span style="font-size: 12px; padding: 4px 8px; border-radius: 4px; background: ${instance.is_running ? '#10b981' : '#ef4444'}; color: white;">
                                    ${instance.is_running ? '运行中' : '已停止'}
                                </span>
                            </h2>
                            <div class="stat-row">
                                <span class="stat-label">实例 ID</span>
                                <span class="stat-value" style="font-size: 12px;">${instance.instance_id.substring(0, 8)}...</span>
                            </div>
                            ${Object.entries(instance.status || {}).slice(0, 5).map(([key, value]) => `
                                <div class="stat-row">
                                    <span class="stat-label">${key}</span>
                                    <span class="stat-value">${value}</span>
                                </div>
                            `).join('')}
                            <div style="margin-top: 15px; display: flex; flex-wrap: wrap;">
                                ${instance.is_running ? `
                                    <button class="btn btn-danger" onclick="stopInstance('${instance.instance_id}')">停止</button>
                                ` : `
                                    <button class="btn btn-success" onclick="startInstance('${instance.instance_id}')">启动</button>
                                `}
                                <button class="btn btn-primary" onclick="deleteInstance('${instance.instance_id}')">删除</button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        async function createStrategy() {
            const strategyType = document.getElementById('strategyType').value;
            const config = document.getElementById('strategyConfig').value;

            if (!strategyType) {
                alert('请选择策略类型');
                return;
            }

            const response = await fetch('/api/strategy-instances', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    strategy_name: strategyType,
                    config: config ? parseYAML(config) : {}
                })
            });

            const result = await response.json();
            if (result.error) {
                alert('创建失败: ' + result.error);
            } else {
                alert('创建成功: ' + result.instance_id);
                loadInstances();
            }
        }

        async function startInstance(instanceId) {
            const response = await fetch(`/api/strategy-instances/${instanceId}/start`, {
                method: 'POST'
            });
            const result = await response.json();
            if (result.error) {
                alert('启动失败: ' + result.error);
            } else {
                loadInstances();
            }
        }

        async function stopInstance(instanceId) {
            const response = await fetch(`/api/strategy-instances/${instanceId}/stop`, {
                method: 'POST'
            });
            const result = await response.json();
            if (result.error) {
                alert('停止失败: ' + result.error);
            } else {
                loadInstances();
            }
        }

        async function deleteInstance(instanceId) {
            if (!confirm('确定要删除此策略实例吗？')) return;

            const response = await fetch(`/api/strategy-instances/${instanceId}`, {
                method: 'DELETE'
            });
            const result = await response.json();
            if (result.error) {
                alert('删除失败: ' + result.error);
            } else {
                loadInstances();
            }
        }

        function parseYAML(yamlStr) {
            // 简化版本，实际应该使用 js-yaml 库
            try {
                const lines = yamlStr.split('\\n');
                const config = {};
                lines.forEach(line => {
                    const match = line.match(/^\\s*(\\w+)\\s*:\\s*(.+)$/);
                    if (match) {
                        config[match[1]] = match[2].trim();
                    }
                });
                return config;
            } catch (e) {
                return {};
            }
        }

        // 初始化
        connectWebSocket();
        loadInstances();
        setInterval(loadInstances, 5000);
    </script>
</body>
</html>
        """
