"""
OKX 交易所连接器
使用 ccxt 库实现 OKX API 集成
"""
import asyncio
import ccxt.async_support as ccxt
from typing import Dict, Optional, List
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class OKXConnector:
    """OKX 交易所连接器"""

    def __init__(self, config: Dict):
        self.config = config
        self.sandbox = config.get("sandbox", False)
        self.exchange = None
        self._init_exchange()

        # 订单跟踪
        self._orders: Dict[str, Dict] = {}

        # WebSocket 连接状态
        self._ws_connected = False
        self._ws_task = None

        # 回调函数
        self.on_order_update = None
        self.on_tick = None
        self.on_order_book = None

    def _init_exchange(self):
        """初始化交易所连接"""
        self.exchange = ccxt.okx({
            'apiKey': self.config.get('api_key'),
            'secret': self.config.get('secret_key'),
            'password': self.config.get('passphrase'),
            'enableRateLimit': True,
            'sandbox': self.sandbox,
        })

        logger.info(f"OKX connector initialized (sandbox={self.sandbox})")

    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            await self.exchange.load_markets()
            logger.info("OKX connection test successful")
            return True
        except Exception as e:
            logger.error(f"OKX connection test failed: {e}")
            return False

    async def get_balance(self) -> Dict:
        """获取账户余额"""
        try:
            balance = await self.exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return {}

    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """获取行情"""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "last": ticker.get("last"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "high": ticker.get("high"),
                "low": ticker.get("low"),
                "volume": ticker.get("baseVolume"),
                "timestamp": ticker.get("timestamp")
            }
        except Exception as e:
            logger.error(f"Error fetching ticker: {e}")
            return None

    async def get_order_book(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """获取订单簿"""
        try:
            orderbook = await self.exchange.fetch_order_book(symbol, limit)
            return {
                "symbol": symbol,
                "bids": orderbook.get("bids", [])[:limit],
                "asks": orderbook.get("asks", [])[:limit],
                "timestamp": datetime.utcnow().timestamp() * 1000
            }
        except Exception as e:
            logger.error(f"Error fetching order book: {e}")
            return None

    async def create_order(self, symbol: str, side: str, size: float,
                          price: float, order_type: str = "limit") -> Optional[str]:
        """创建订单"""
        try:
            # 转换为交易所格式
            ccxt_side = "buy" if side == "buy" else "sell"

            order = await self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=ccxt_side,
                amount=size,
                price=price
            )

            order_id = order.get("id")
            self._orders[order_id] = {
                "id": order_id,
                "symbol": symbol,
                "side": side,
                "size": size,
                "price": price,
                "type": order_type,
                "status": order.get("status"),
                "filled": order.get("filled", 0),
                "remaining": order.get("remaining", size),
                "created_at": datetime.utcnow().isoformat()
            }

            logger.info(f"Order created: {order_id} {side} {size}@{price}")
            return order_id

        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None

    async def cancel_order(self, order_id: str, symbol: str = None) -> bool:
        """取消订单"""
        try:
            if order_id in self._orders:
                symbol = symbol or self._orders[order_id]["symbol"]
                await self.exchange.cancel_order(order_id, symbol)
                self._orders[order_id]["status"] = "canceled"
                logger.info(f"Order cancelled: {order_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False

    async def cancel_all_orders(self, symbol: str = None) -> int:
        """取消所有订单"""
        try:
            if symbol:
                open_orders = await self.exchange.fetch_open_orders(symbol)
            else:
                open_orders = await self.exchange.fetch_open_orders()

            cancelled = 0
            for order in open_orders:
                try:
                    await self.exchange.cancel_order(order["id"], order["symbol"])
                    cancelled += 1
                except Exception as e:
                    logger.error(f"Error cancelling order {order['id']}: {e}")

            logger.info(f"Cancelled {cancelled} orders")
            return cancelled

        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")
            return 0

    async def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """获取开放订单"""
        try:
            orders = await self.exchange.fetch_open_orders(symbol)
            return orders
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []

    async def get_order(self, order_id: str, symbol: str = None) -> Optional[Dict]:
        """获取订单信息"""
        try:
            if order_id in self._orders:
                symbol = symbol or self._orders[order_id]["symbol"]
                order = await self.exchange.fetch_order(order_id, symbol)
                return order
            return None
        except Exception as e:
            logger.error(f"Error fetching order: {e}")
            return None

    async def fetch_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """获取交易历史"""
        try:
            trades = await self.exchange.fetch_trades(symbol, limit=limit)
            return trades
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []

    async def fetch_candles(self, symbol: str, timeframe: str = "1m",
                           limit: int = 100) -> List[Dict]:
        """获取K线数据"""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            candles = []
            for item in ohlcv:
                candles.append({
                    "timestamp": item[0],
                    "open": item[1],
                    "high": item[2],
                    "low": item[3],
                    "close": item[4],
                    "volume": item[5]
                })
            return candles
        except Exception as e:
            logger.error(f"Error fetching candles: {e}")
            return []

    async def close(self):
        """关闭连接"""
        try:
            if self._ws_task:
                self._ws_task.cancel()
            await self.exchange.close()
            logger.info("OKX connector closed")
        except Exception as e:
            logger.error(f"Error closing connector: {e}")

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "exchange": "okx",
            "sandbox": self.sandbox,
            "orders_count": len(self._orders),
            "ws_connected": self._ws_connected
        }
