"""
OKX 交易所连接器（基于 Hummingbot 代码的简化版本）
直接复制 Hummingbot 的 OKX 相关纯 Python 代码
支持代理配置（HTTP/SOCKS5）
"""
import os
import asyncio
import aiohttp
import json
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime

from .okx_constants import (
    get_okx_base_url,
    OKX_SERVER_TIME_PATH,
    OKX_TICKER_PATH,
    OKX_ORDER_BOOK_PATH,
    OKX_PLACE_ORDER_PATH,
    OKX_ORDER_CANCEL_PATH,
    OKX_BALANCE_PATH,
    OKX_ASSET_BALANCE_PATH
)
from .okx_auth import OkxAuth, TimeSynchronizer
from .proxy_manager import ProxyManager


class OKXConnector:
    """
    OKX 交易所连接器（基于 Hummingbot 代码）
    复制自 hummingbot/connector/exchange/okx/okx_exchange.py 的核心逻辑

    支持代理配置：
    - HTTP 代理: http://127.0.0.1:7890
    - SOCKS5 代理: socks5://127.0.0.1:7891
    - Clash: "clash" 或 "clash-http" 或 "clash-socks5"
    - 端口号: "7890"
    """

    def __init__(self, config: Dict):
        """
        初始化 OKX 连接器

        :param config: 配置字典
            - api_key: OKX API Key
            - secret_key: OKX Secret Key
            - passphrase: OKX Passphrase
            - registration_sub_domain: 子域名（www, app, my）
            - sandbox: 是否使用沙盒环境
            - proxy: 代理配置（支持多种格式）
        """
        self.exchange_name = "okx"
        self.okx_api_key = config.get('api_key')
        self.okx_secret_key = config.get('secret_key')
        self.okx_passphrase = config.get('passphrase')
        self.okx_registration_sub_domain = config.get('registration_sub_domain', 'www')
        self.sandbox = config.get('sandbox', False)

        # 代理配置
        self._proxy = config.get('proxy')
        self._proxy_config = ProxyManager.parse_proxy_url(self._proxy) if self._proxy else {}
        self._aiohttp_proxy = ProxyManager.get_aiohttp_proxy(self._proxy_config)

        # 初始化认证
        self._time_synchronizer = TimeSynchronizer()
        self._auth = OkxAuth(
            api_key=self.okx_api_key,
            secret_key=self.okx_secret_key,
            passphrase=self.okx_passphrase,
            time_provider=self._time_synchronizer
        )

        # API 端点
        self._base_url = get_okx_base_url(self.okx_registration_sub_domain)
        if self.sandbox:
            self._base_url = "https://www.okx.com"  # 沙盒环境

        # HTTP 客户端
        self._http_client = None

        # 订单跟踪
        self._orders: Dict[str, Dict] = {}

    async def __aenter__(self):
        """异步上下文管理器入口"""
        # 创建 HTTP 客户端（支持代理）
        connector = None
        if self._aiohttp_proxy and 'socks' in self._aiohttp_proxy:
            # SOCKS5 代理需要特殊处理
            try:
                from aiohttp_socks import ProxyConnector
                connector = ProxyConnector.from_url(self._aiohttp_proxy)
            except ImportError:
                print("警告: SOCKS5 代理需要安装 aiohttp-socks")
                print("运行: pip install aiohttp-socks")
                connector = None

        timeout = aiohttp.ClientTimeout(total=30)
        self._http_client = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )

        await self._sync_time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self._http_client:
            await self._http_client.close()

    def _get_request_kwargs(self) -> dict:
        """获取请求参数（包括代理）"""
        kwargs = {}
        if self._aiohttp_proxy and 'socks' not in self._aiohttp_proxy:
            kwargs['proxy'] = self._aiohttp_proxy
        return kwargs

    async def _sync_time(self):
        """同步服务器时间"""
        try:
            url = f"{self._base_url}{OKX_SERVER_TIME_PATH}"
            kwargs = self._get_request_kwargs()

            async with self._http_client.get(url, **kwargs) as response:
                data = await response.json()
                if data.get('code') == '0' and data.get('data'):
                    server_time = int(data['data'][0]['ts']) / 1000
                    self._time_synchronizer.update_server_time_offset(server_time)
                    print(f"时间同步成功: {datetime.fromtimestamp(server_time)}")
        except Exception as e:
            print(f"时间同步失败: {e}")

    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            await self._sync_time()
            url = f"{self._base_url}{OKX_SERVER_TIME_PATH}"
            kwargs = self._get_request_kwargs()

            async with self._http_client.get(url, **kwargs) as response:
                data = await response.json()
                return data.get('code') == '0'
        except Exception as e:
            print(f"连接测试失败: {e}")
            return False

    async def get_balance(self) -> Dict:
        """
        获取账户余额
        复制自 Hummingbot 的 OKX 实现
        """
        try:
            url = f"{self._base_url}{OKX_BALANCE_PATH}"
            # 传入完整 URL 而不是路径（Hummingbot 官方方式）
            headers = self._auth.authentication_headers("GET", url)

            # 如果是模拟盘，添加模拟盘标记
            if self.sandbox:
                headers["x-simulated-trading"] = "1"

            kwargs = self._get_request_kwargs()

            async with self._http_client.get(url, headers=headers, **kwargs) as response:
                data = await response.json()
                if data.get('code') == '0':
                    balance = {}

                    # 打印原始数据以便调试
                    print(f"📊 交易账户 API 响应: {data}")

                    # Hummingbot 官方逻辑
                    balances = data['data'][0]['details']

                    print(f"📊 详情数量: {len(balances)}")

                    for balance_item in balances:
                        ccy = balance_item["ccy"]
                        equity_text = balance_item.get("eq")
                        available_equity_text = balance_item.get("availEq")

                        if equity_text and available_equity_text:
                            total = Decimal(str(equity_text))
                            available = Decimal(str(available_equity_text))
                        else:
                            available = Decimal(str(balance_item.get("availBal", 0)))
                            total = available + Decimal(str(balance_item.get("frozenBal", 0)))

                        balance[ccy] = {
                            'total': total,
                            'available': available,
                            'frozen': total - available
                        }

                    print(f"✅ 获取余额成功: {len(balance)} 种货币")
                    return balance
                else:
                    # 打印详细的错误信息
                    print(f"❌ OKX API 返回错误:")
                    print(f"   错误代码: {data.get('code')}")
                    print(f"   错误信息: {data.get('msg')}")
                    print(f"   完整响应: {data}")
                    return {}
        except Exception as e:
            print(f"❌ 获取余额失败: {e}")
            import traceback
            print(traceback.format_exc())
            return {}

    async def get_asset_balance(self) -> Dict:
        """
        获取资金账户余额（现金账户）
        OKX V5 API: /api/v5/asset/balances
        """
        try:
            url = f"{self._base_url}{OKX_ASSET_BALANCE_PATH}"
            # 传入完整 URL 而不是路径（Hummingbot 官方方式）
            headers = self._auth.authentication_headers("GET", url)

            # 如果是模拟盘，添加模拟盘标记
            if self.sandbox:
                headers["x-simulated-trading"] = "1"

            kwargs = self._get_request_kwargs()

            async with self._http_client.get(url, headers=headers, **kwargs) as response:
                data = await response.json()
                if data.get('code') == '0':
                    balance = {}

                    # 打印原始数据以便调试
                    print(f"💰 资金账户 API 响应: {data}")

                    # Hummingbot 官方逻辑（与交易账户相同）
                    data_list = data.get('data', [])

                    for item in data_list:
                        ccy = item["ccy"]
                        equity_text = item.get("eq")
                        available_equity_text = item.get("availEq")

                        if equity_text and available_equity_text:
                            total = Decimal(str(equity_text))
                            available = Decimal(str(available_equity_text))
                        else:
                            available = Decimal(str(item.get("availBal", 0)))
                            total = available + Decimal(str(item.get("frozenBal", 0)))

                        balance[ccy] = {
                            'total': total,
                            'available': available,
                            'frozen': total - available
                        }

                    print(f"✅ 获取资金账户余额成功: {len(balance)} 种货币")
                    return balance
                else:
                    # 打印详细的错误信息
                    print(f"❌ OKX API 返回错误（资金账户）:")
                    print(f"   错误代码: {data.get('code')}")
                    print(f"   错误信息: {data.get('msg')}")
                    print(f"   完整响应: {data}")
                    return {}
        except Exception as e:
            print(f"❌ 获取资金账户余额失败: {e}")
            import traceback
            print(traceback.format_exc())
            return {}

    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """
        获取行情
        复制自 Hummingbot 的 OKX 实现
        """
        try:
            url = f"{self._base_url}{OKX_TICKER_PATH}"
            params = {'instId': symbol}
            full_url = f"{url}?instId={symbol}"
            kwargs = self._get_request_kwargs()

            async with self._http_client.get(full_url, **kwargs) as response:
                data = await response.json()
                if data.get('code') == '0' and data.get('data'):
                    ticker = data['data'][0]
                    return {
                        "symbol": symbol,
                        "last": Decimal(ticker.get('last', '0')),
                        "bid": Decimal(ticker.get('bidPx', '0')),
                        "ask": Decimal(ticker.get('askPx', '0')),
                        "high": Decimal(ticker.get('high24h', '0')),
                        "low": Decimal(ticker.get('low24h', '0')),
                        "volume": Decimal(ticker.get('volCcy24h', '0')),
                        "timestamp": int(ticker.get('ts', 0))
                    }
                return None
        except Exception as e:
            print(f"获取行情失败: {e}")
            return None

    async def get_order_book(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """
        获取订单簿
        复制自 Hummingbot 的 OKX 实现
        """
        try:
            url = f"{self._base_url}{OKX_ORDER_BOOK_PATH}"
            params = {'instId': symbol, 'sz': str(limit)}
            full_url = f"{url}?instId={symbol}&sz={limit}"
            kwargs = self._get_request_kwargs()

            async with self._http_client.get(full_url, **kwargs) as response:
                data = await response.json()
                if data.get('code') == '0' and data.get('data'):
                    orderbook = data['data'][0]
                    bids = [[Decimal(b['bids'][0]), Decimal(b['bids'][1])] for b in orderbook.get('bids', [])[:limit]]
                    asks = [[Decimal(a['asks'][0]), Decimal(a['asks'][1])] for a in orderbook.get('asks', [])[:limit]]
                    return {
                        "symbol": symbol,
                        "bids": bids,
                        "asks": asks,
                        "timestamp": int(orderbook.get('ts', 0))
                    }
                return None
        except Exception as e:
            print(f"获取订单簿失败: {e}")
            return None

    async def create_order(self, symbol: str, side: str, size: float,
                          price: float, order_type: str = "limit") -> Optional[str]:
        """
        创建订单
        复制自 Hummingbot 的 _place_order 实现
        """
        try:
            url = f"{self._base_url}{OKX_PLACE_ORDER_PATH}"
            # 传入完整 URL 而不是路径（Hummingbot 官方方式）
            data = {
                "instId": symbol,
                "tdMode": "cash",
                "side": side,
                "ordType": "limit" if order_type == "limit" else "market",
                "sz": str(size),
            }

            if order_type == "limit":
                data["px"] = str(price)

            json_data = json.dumps(data)
            headers = self._auth.authentication_headers("POST", url, data=json_data)
            headers["Content-Type"] = "application/json"

            # 如果是模拟盘，添加模拟盘标记
            if self.sandbox:
                headers["x-simulated-trading"] = "1"

            kwargs = self._get_request_kwargs()

            async with self._http_client.post(url, headers=headers, data=json_data, **kwargs) as response:
                result = await response.json()
                if result.get('code') == '0' and result.get('data'):
                    order_id = result['data'][0].get('ordId')
                    if order_id:
                        self._orders[order_id] = {
                            "id": order_id,
                            "symbol": symbol,
                            "side": side,
                            "size": Decimal(str(size)),
                            "price": Decimal(str(price)),
                            "type": order_type,
                            "status": "open"
                        }
                        print(f"订单创建成功: {order_id}")
                        return order_id
                else:
                    print(f"订单创建失败: {result}")
                return None
        except Exception as e:
            print(f"创建订单失败: {e}")
            return None

    async def cancel_order(self, order_id: str, symbol: str = None) -> bool:
        """
        取消订单
        复制自 Hummingbot 的 _place_cancel 实现
        """
        try:
            url = f"{self._base_url}{OKX_ORDER_CANCEL_PATH}"

            # 获取订单信息
            order = self._orders.get(order_id)
            if not order:
                return False

            data = {
                "instId": order['symbol'],
                "ordId": order_id,
            }

            json_data = json.dumps(data)
            # 传入完整 URL 而不是路径
            headers = self._auth.authentication_headers("POST", url, data=json_data)
            headers["Content-Type"] = "application/json"

            # 如果是模拟盘，添加模拟盘标记
            if self.sandbox:
                headers["x-simulated-trading"] = "1"

            kwargs = self._get_request_kwargs()

            async with self._http_client.post(url, headers=headers, data=json_data, **kwargs) as response:
                result = await response.json()
                if result.get('code') == '0':
                    if order_id in self._orders:
                        self._orders[order_id]["status"] = "canceled"
                    print(f"订单取消成功: {order_id}")
                    return True
                else:
                    print(f"订单取消失败: {result}")
                return False
        except Exception as e:
            print(f"取消订单失败: {e}")
            return False

    async def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """获取开放订单"""
        return [order for order in self._orders.values()
                if order["status"] == "open" and (symbol is None or order["symbol"] == symbol)]

    async def cancel_all_orders(self, symbol: str = None) -> int:
        """取消所有订单"""
        cancelled = 0
        for order in list(self._orders.values()):
            if order["status"] == "open" and (symbol is None or order["symbol"] == symbol):
                if await self.cancel_order(order["id"]):
                    cancelled += 1
        return cancelled

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "exchange": "okx",
            "sandbox": self.sandbox,
            "base_url": self._base_url,
            "proxy": self._proxy,
            "orders_count": len(self._orders)
        }
