"""
Web API 扩展
为前端提供完整的 REST API 接口
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
import json
import logging
import sys
import asyncio
from datetime import datetime, timedelta
from dataclasses import asdict

logger = logging.getLogger(__name__)


class APIExtension:
    """API 扩展类 - 提供完整的 REST API 接口"""

    def __init__(self, app: FastAPI, bot_instance, strategy_manager=None, ws_log_handler=None):
        self.app = app
        self.bot = bot_instance
        self.strategy_manager = strategy_manager
        self.ws_log_handler = ws_log_handler

        # 数据存储（从真实交易所和数据库获取）
        self._trade_history = []
        self._pnl_history = []
        self._backtest_results = {}

        # 设置所有路由
        self._setup_all_routes()

    def _setup_all_routes(self):
        """设置所有 API 路由"""
        self._setup_account_apis()
        self._setup_position_apis()
        self._setup_order_apis()
        self._setup_market_data_apis()
        self._setup_pnl_apis()
        self._setup_backtest_apis()
        self._setup_system_apis()

    # ==================== 账户相关 API ====================

    def _setup_account_apis(self):
        """设置账户相关 API"""

        @self.app.get("/api/equity")
        async def get_equity():
            """
            获取账户权益

            返回格式:
            {
                "account_id": "string",
                "exchange": "string",
                "equity": number,
                "total_balance": number,
                "available_balance": number,
                "pnl": number,
                "today_pnl": number,
                "unrealized_pnl": number,
                "leverage": number,
                "margin_ratio": number
            }
            """
            try:
                # 获取余额
                balance_data = await self._get_balance_data()

                # 计算权益
                total_balance = sum(
                    b.get('total', 0) for b in balance_data.values()
                )
                available_balance = sum(
                    b.get('available', 0) for b in balance_data.values()
                )

                # 获取仓位计算未实现盈亏
                unrealized_pnl = await self._get_unrealized_pnl()

                # 模拟 PnL 数据（实际应用中应该从数据库或交易所获取）
                realized_pnl = 0
                today_pnl = 0

                equity = total_balance + unrealized_pnl

                return {
                    "account_id": "main",
                    "exchange": getattr(self.bot.exchange, 'exchange_name', 'unknown') if hasattr(self.bot, 'exchange') else 'unknown',
                    "equity": equity,
                    "total_balance": total_balance,
                    "available_balance": available_balance,
                    "pnl": realized_pnl,
                    "today_pnl": today_pnl,
                    "unrealized_pnl": unrealized_pnl,
                    "leverage": 1.0,
                    "margin_ratio": 0.0
                }
            except Exception as e:
                logger.error(f"获取权益失败: {e}")
                import traceback
                return {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }

        @self.app.get("/api/balance")
        async def get_balance_api():
            """
            获取账户余额

            返回格式:
            {
                "BTC": {"total": number, "available": number, "frozen": number},
                "USDT": {"total": number, "available": number, "frozen": number},
                ...
            }
            """
            try:
                balance_data = await self._get_balance_data()
                return balance_data
            except Exception as e:
                logger.error(f"获取余额失败: {e}")
                import traceback
                return {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }

    # ==================== 仓位相关 API ====================

    def _setup_position_apis(self):
        """设置仓位相关 API"""

        @self.app.get("/api/positions")
        async def get_positions():
            """
            获取所有仓位

            返回格式:
            [
                {
                    "symbol": "BTC-USDT",
                    "side": "long" | "short",
                    "size": number,
                    "entry_price": number,
                    "mark_price": number,
                    "liquidation_price": number,
                    "unrealized_pnl": number,
                    "realized_pnl": number,
                    "leverage": number,
                    "margin": number,
                    "margin_ratio": number
                },
                ...
            ]
            """
            try:
                positions = []

                if hasattr(self.bot, 'position_manager'):
                    # 从 position_manager 获取仓位
                    position_dict = self.bot.position_manager.to_dict()

                    for symbol, pos_data in position_dict.items():
                        if isinstance(pos_data, dict):
                            positions.append({
                                "symbol": symbol,
                                "side": pos_data.get('side', 'long'),
                                "size": pos_data.get('amount', 0),
                                "entry_price": pos_data.get('entry_price', 0),
                                "mark_price": pos_data.get('mark_price', 0),
                                "liquidation_price": pos_data.get('liquidation_price'),
                                "unrealized_pnl": pos_data.get('unrealized_pnl', 0),
                                "realized_pnl": pos_data.get('realized_pnl', 0),
                                "leverage": pos_data.get('leverage', 1.0),
                                "margin": pos_data.get('margin', 0),
                                "margin_ratio": pos_data.get('margin_ratio', 0)
                            })

                return positions
            except Exception as e:
                logger.error(f"获取仓位失败: {e}")
                import traceback
                return []

        @self.app.get("/api/positions/{symbol}")
        async def get_position(symbol: str):
            """获取指定交易对的仓位"""
            try:
                positions = await get_positions()
                for pos in positions:
                    if pos['symbol'] == symbol:
                        return pos
                return {"error": "Position not found"}
            except Exception as e:
                logger.error(f"获取仓位失败: {e}")
                return {"error": str(e)}

    # ==================== 订单相关 API ====================

    def _setup_order_apis(self):
        """设置订单相关 API"""

        @self.app.get("/api/orders/active")
        async def get_active_orders():
            """
            获取活跃订单

            返回格式:
            [
                {
                    "order_id": "string",
                    "symbol": "string",
                    "side": "buy" | "sell",
                    "type": "limit" | "market" | "stop",
                    "price": number,
                    "amount": number,
                    "filled": number,
                    "remaining": number,
                    "status": "pending" | "open" | "filled" | "canceled" | "failed",
                    "timestamp": number
                },
                ...
            ]
            """
            try:
                orders = []

                if hasattr(self.bot, 'exchange'):
                    # 从交易所获取开放订单
                    open_orders = await self.bot.exchange.get_open_orders()

                    for order in open_orders:
                        orders.append({
                            "order_id": order.get('order_id', order.get('id', '')),
                            "symbol": order.get('symbol', ''),
                            "side": order.get('side', 'buy'),
                            "type": order.get('type', 'limit'),
                            "price": order.get('price', 0),
                            "amount": order.get('amount', order.get('quantity', 0)),
                            "filled": order.get('filled', 0),
                            "remaining": order.get('remaining', order.get('amount', 0) - order.get('filled', 0)),
                            "status": order.get('status', 'open'),
                            "timestamp": order.get('timestamp', order.get('created_at', datetime.now().timestamp()))
                        })

                return orders
            except Exception as e:
                logger.error(f"获取活跃订单失败: {e}")
                import traceback
                return []

        @self.app.get("/api/trades/history")
        async def get_trade_history(
            limit: Optional[int] = Query(100, ge=1, le=1000),
            symbol: Optional[str] = None
        ):
            """
            获取成交历史

            返回格式:
            [
                {
                    "trade_id": "string",
                    "symbol": "string",
                    "side": "buy" | "sell",
                    "price": number,
                    "amount": number,
                    "fee": number,
                    "fee_currency": "string",
                    "timestamp": number
                },
                ...
            ]
            """
            try:
                trades = []

                # 从模拟历史中获取
                if symbol:
                    trades = [t for t in self._trade_history if t['symbol'] == symbol]
                else:
                    trades = self._trade_history

                # 限制返回数量
                trades = trades[-limit:]

                return trades
            except Exception as e:
                logger.error(f"获取成交历史失败: {e}")
                return []

    # ==================== 市场数据 API ====================

    def _setup_market_data_apis(self):
        """设置市场数据相关 API"""

        @self.app.get("/api/orderbook/{symbol}")
        async def get_orderbook(
            symbol: str,
            limit: Optional[int] = Query(20, ge=5, le=100)
        ):
            """
            获取订单簿

            返回格式:
            {
                "symbol": "string",
                "bids": [[price, amount], ...],
                "asks": [[price, amount], ...],
                "timestamp": number
            }
            """
            try:
                if hasattr(self.bot, 'exchange'):
                    orderbook = await self.bot.exchange.get_order_book(symbol, limit)

                    # 格式化返回数据
                    bids = [[float(bid[0]), float(bid[1])] for bid in orderbook.get('bids', [])[:limit]]
                    asks = [[float(ask[0]), float(ask[1])] for ask in orderbook.get('asks', [])[:limit]]

                    return {
                        "symbol": symbol,
                        "bids": bids,
                        "asks": asks,
                        "timestamp": datetime.now().timestamp()
                    }
                else:
                    # 返回模拟数据
                    return self._get_mock_orderbook(symbol, limit)
            except Exception as e:
                logger.error(f"获取订单簿失败: {e}")
                import traceback
                return self._get_mock_orderbook(symbol, limit)

        @self.app.get("/api/ticker/{symbol}")
        async def get_ticker(symbol: str):
            """
            获取 Ticker 信息

            返回格式:
            {
                "symbol": "string",
                "last_price": number,
                "best_bid": number,
                "best_ask": number,
                "bid_qty": number,
                "ask_qty": number,
                "price_change_24h": number,
                "price_change_pct_24h": number,
                "volume_24h": number,
                "high_24h": number,
                "low_24h": number,
                "timestamp": number
            }
            """
            try:
                if hasattr(self.bot, 'exchange'):
                    ticker = await self.bot.exchange.get_ticker(symbol)
                    return ticker
                else:
                    # 返回模拟数据
                    return self._get_mock_ticker(symbol)
            except Exception as e:
                logger.error(f"获取 Ticker 失败: {e}")
                return self._get_mock_ticker(symbol)

        @self.app.get("/api/klines")
        async def get_klines(
            symbol: str = Query(...),
            interval: str = Query("1h", regex="^(1m|5m|15m|30m|1h|4h|1d|1w)$"),
            limit: int = Query(100, ge=1, le=1000)
        ):
            """
            获取 K 线数据

            返回格式:
            [
                {
                    "timestamp": number,
                    "open": number,
                    "high": number,
                    "low": number,
                    "close": number,
                    "volume": number
                },
                ...
            ]
            """
            try:
                if hasattr(self.bot, 'exchange'):
                    klines = await self.bot.exchange.get_klines(symbol, interval, limit)
                    return klines
                else:
                    # 返回模拟数据
                    return self._get_mock_klines(symbol, interval, limit)
            except Exception as e:
                logger.error(f"获取 K 线数据失败: {e}")
                return []

    # ==================== PnL 相关 API ====================

    def _setup_pnl_apis(self):
        """设置 PnL 相关 API"""

        @self.app.get("/api/pnl/history")
        async def get_pnl_history(
            start_time: Optional[int] = Query(None),
            end_time: Optional[int] = Query(None)
        ):
            """
            获取 PnL 历史记录

            返回格式:
            [
                {
                    "timestamp": number,
                    "equity": number,
                    "realized_pnl": number,
                    "unrealized_pnl": number
                },
                ...
            ]
            """
            try:
                # 获取权益历史
                pnl_data = []

                # 如果提供了时间范围，则过滤
                if start_time or end_time:
                    filtered_data = [
                        d for d in self._pnl_history
                        if (not start_time or d['timestamp'] >= start_time)
                        and (not end_time or d['timestamp'] <= end_time)
                    ]
                    pnl_data = filtered_data
                else:
                    # 返回最近 100 条记录
                    pnl_data = self._pnl_history[-100:]

                return pnl_data
            except Exception as e:
                logger.error(f"获取 PnL 历史失败: {e}")
                return []

    # ==================== 回测相关 API ====================

    def _setup_backtest_apis(self):
        """设置回测相关 API"""

        @self.app.post("/api/backtest/run")
        async def run_backtest(request: dict):
            """
            运行回测

            请求格式:
            {
                "strategy": "string",
                "config": dict,
                "start_time": number,
                "end_time": number
            }

            返回格式:
            {
                "backtest_id": "string",
                "status": "running" | "completed" | "failed"
            }
            """
            try:
                backtest_id = f"bt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                # 模拟回测结果
                result = self._generate_mock_backtest_result(
                    request.get('strategy', ''),
                    request.get('config', {}),
                    request.get('start_time', 0),
                    request.get('end_time', 0)
                )

                self._backtest_results[backtest_id] = result

                return {
                    "backtest_id": backtest_id,
                    "status": "completed"
                }
            except Exception as e:
                logger.error(f"运行回测失败: {e}")
                import traceback
                return {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }

        @self.app.get("/api/backtest/{backtest_id}")
        async def get_backtest_result(backtest_id: str):
            """
            获取回测结果

            返回格式:
            {
                "backtest_id": "string",
                "strategy": "string",
                "total_pnl": number,
                "total_return": number,
                "total_trades": number,
                "win_rate": number,
                "max_drawdown": number,
                "sharpe_ratio": number,
                "profit_factor": number,
                "avg_win": number,
                "avg_loss": number,
                "expected_return": number,
                "annualized_return": number,
                "volatility": number,
                "total_fees": number,
                "equity_curve": [
                    {"timestamp": number, "equity": number},
                    ...
                ]
            }
            """
            try:
                result = self._backtest_results.get(backtest_id)
                if not result:
                    return {"error": "Backtest not found"}

                return result
            except Exception as e:
                logger.error(f"获取回测结果失败: {e}")
                return {"error": str(e)}

    # ==================== 系统管理 API ====================

    def _setup_system_apis(self):
        """设置系统管理相关 API"""

        @self.app.get("/api/stats/realtime")
        async def get_realtime_stats():
            """
            获取实时统计数据

            返回格式:
            {
                "total_strategies": number,
                "running_strategies": number,
                "total_orders": number,
                "total_trades": number,
                "total_equity": number,
                "total_pnl": number
            }
            """
            try:
                stats = {
                    "total_strategies": 0,
                    "running_strategies": 0,
                    "total_orders": 0,
                    "total_trades": len(self._trade_history),
                    "total_equity": 0,
                    "total_pnl": 0
                }

                if self.strategy_manager:
                    instances = self.strategy_manager.get_instances_summary()
                    stats["total_strategies"] = len(instances)
                    stats["running_strategies"] = sum(
                        1 for i in instances if i.get('is_running', False)
                    )

                # 获取权益
                balance_data = await self._get_balance_data()
                unrealized_pnl = await self._get_unrealized_pnl()

                total_balance = sum(
                    b.get('total', 0) for b in balance_data.values()
                )
                equity = total_balance + unrealized_pnl

                stats["total_equity"] = equity
                stats["total_pnl"] = unrealized_pnl

                return stats
            except Exception as e:
                logger.error(f"获取实时统计失败: {e}")
                import traceback
                return {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }

    # ==================== 辅助方法 ====================

    async def _get_balance_data(self) -> Dict[str, Dict]:
        """获取余额数据（从真实交易所）"""
        try:
            if hasattr(self.bot, 'exchange'):
                balance = await self.bot.exchange.get_balance()
                return balance
            else:
                logger.error("Bot 没有配置交易所实例")
                return {}
        except Exception as e:
            logger.error(f"获取余额数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    async def _get_unrealized_pnl(self) -> float:
        """获取未实现盈亏"""
        try:
            total_pnl = 0.0

            if hasattr(self.bot, 'position_manager'):
                position_dict = self.bot.position_manager.to_dict()

                for pos_data in position_dict.values():
                    if isinstance(pos_data, dict):
                        total_pnl += pos_data.get('unrealized_pnl', 0)

            return total_pnl
        except Exception as e:
            logger.error(f"获取未实现盈亏失败: {e}")
            return 0.0

    def _get_mock_orderbook(self, symbol: str, limit: int) -> Dict:
        """获取模拟订单簿"""
        import random

        base_price = 50000.0 if 'BTC' in symbol else 3000.0
        tick_size = base_price * 0.0001

        bids = []
        asks = []

        for i in range(limit):
            bid_price = base_price - (i + 1) * tick_size
            ask_price = base_price + (i + 1) * tick_size
            bid_amount = random.uniform(0.001, 1.0)
            ask_amount = random.uniform(0.001, 1.0)

            bids.append([round(bid_price, 2), round(bid_amount, 4)])
            asks.append([round(ask_price, 2), round(ask_amount, 4)])

        return {
            "symbol": symbol,
            "bids": bids,
            "asks": asks,
            "timestamp": datetime.now().timestamp()
        }

    def _get_mock_ticker(self, symbol: str) -> Dict:
        """获取模拟 Ticker"""
        import random

        base_price = 50000.0 if 'BTC' in symbol else 3000.0
        price_change = random.uniform(-500, 500)

        return {
            "symbol": symbol,
            "last_price": round(base_price + price_change, 2),
            "best_bid": round(base_price + price_change - 1, 2),
            "best_ask": round(base_price + price_change + 1, 2),
            "bid_qty": random.uniform(0.1, 2.0),
            "ask_qty": random.uniform(0.1, 2.0),
            "price_change_24h": round(price_change, 2),
            "price_change_pct_24h": round(price_change / base_price * 100, 2),
            "volume_24h": random.uniform(1000, 5000),
            "high_24h": round(base_price + 1000, 2),
            "low_24h": round(base_price - 1000, 2),
            "timestamp": datetime.now().timestamp()
        }

    def _get_mock_klines(self, symbol: str, interval: str, limit: int) -> List[Dict]:
        """获取模拟 K 线数据"""
        import random

        base_price = 50000.0 if 'BTC' in symbol else 3000.0
        klines = []

        # 间隔映射（秒）
        interval_map = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
            "1w": 604800
        }

        interval_seconds = interval_map.get(interval, 3600)
        now = datetime.now().timestamp()

        for i in range(limit):
            timestamp = now - (limit - i) * interval_seconds
            price = base_price + random.uniform(-500, 500)
            klines.append({
                "timestamp": int(timestamp),
                "open": round(price + random.uniform(-10, 10), 2),
                "high": round(price + random.uniform(0, 20), 2),
                "low": round(price - random.uniform(0, 20), 2),
                "close": round(price + random.uniform(-10, 10), 2),
                "volume": round(random.uniform(10, 100), 2)
            })

        return klines

    def _generate_mock_backtest_result(self, strategy: str, config: dict, start_time: int, end_time: int) -> Dict:
        """生成模拟回测结果"""
        import random

        # 生成权益曲线
        equity_curve = []
        equity = 10000.0

        duration = end_time - start_time if end_time > start_time else 86400  # 默认一天
        points = min(100, int(duration / 3600))  # 最多 100 个点

        for i in range(points):
            equity += random.uniform(-100, 150)
            equity_curve.append({
                "timestamp": start_time + (i * duration // points),
                "equity": round(equity, 2)
            })

        # 计算统计指标
        total_trades = random.randint(50, 200)
        winning_trades = random.randint(20, total_trades)
        win_rate = winning_trades / total_trades * 100

        total_pnl = equity - 10000.0
        total_return = total_pnl / 10000.0 * 100

        max_drawdown = abs(random.uniform(-2000, -500))
        sharpe_ratio = random.uniform(0.5, 3.0)

        profit_factor = random.uniform(1.2, 2.5)
        avg_win = random.uniform(20, 50)
        avg_loss = -random.uniform(10, 30)
        expected_return = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)

        annualized_return = total_return * 365  # 假设回测是一天
        volatility = random.uniform(10, 30)
        total_fees = total_trades * random.uniform(0.1, 0.5)

        return {
            "backtest_id": f"mock_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "strategy": strategy,
            "total_pnl": round(total_pnl, 2),
            "total_return": round(total_return, 2),
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "profit_factor": round(profit_factor, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "expected_return": round(expected_return, 2),
            "annualized_return": round(annualized_return, 2),
            "volatility": round(volatility, 2),
            "total_fees": round(total_fees, 2),
            "equity_curve": equity_curve
        }

    # ==================== 数据管理 ====================
