"""
OKX 常量定义（复制自 Hummingbot）
"""
import sys

CLIENT_ID_PREFIX = "93027a12dac34fBC"
MAX_ID_LEN = 32

# URL mapping based on where account is registered
subdomain_to_api_subdomain = {
    "www": "www",
    "app": "us",
    "my": "eea"
}


def get_okx_base_url(sub_domain: str) -> str:
    """Returns OKX REST base URL based on API subdomain ("www", "us", "eea")"""
    return f"https://{subdomain_to_api_subdomain[sub_domain]}.okx.com/"


def get_ws_url(sub_domain: str) -> str:
    """Returns OKX WebSocket base URL based on API subdomain ("www", "us", "eea")"""
    if sub_domain == "www":
        return "wss://ws.okx.com:8443"
    else:
        return f"wss://ws{subdomain_to_api_subdomain[sub_domain]}.okx.com:8443"


DEFAULT_DOMAIN = get_okx_base_url("www")

# REST API endpoints
OKX_SERVER_TIME_PATH = '/api/v5/public/time'
OKX_INSTRUMENTS_PATH = '/api/v5/public/instruments'
OKX_TICKER_PATH = '/api/v5/market/ticker'
OKX_ORDER_BOOK_PATH = '/api/v5/market/books'

# Auth required
OKX_PLACE_ORDER_PATH = "/api/v5/trade/order"
OKX_ORDER_DETAILS_PATH = '/api/v5/trade/order'
OKX_ORDER_CANCEL_PATH = '/api/v5/trade/cancel-order'
OKX_BALANCE_PATH = '/api/v5/account/balance'
OKX_ASSET_BALANCE_PATH = '/api/v5/asset/balances'  # 资金账户余额（现金账户）

NO_LIMIT = sys.maxsize
