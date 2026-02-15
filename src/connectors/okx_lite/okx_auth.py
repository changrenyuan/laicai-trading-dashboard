"""
OKX 认证类（复制自 Hummingbot）
"""
import base64
import datetime
import hashlib
import hmac
from collections import OrderedDict
from typing import Any, Dict, Optional
from urllib.parse import urlencode


class TimeSynchronizer:
    """简化的时间同步器"""
    def __init__(self):
        self._time_offset = 0.0

    def time(self) -> float:
        return datetime.datetime.now(datetime.UTC).timestamp() + self._time_offset

    def update_server_time_offset(self, server_time: float):
        self._time_offset = server_time - datetime.datetime.now(datetime.UTC).timestamp()


class OkxAuth:
    """OKX 认证类（复制自 Hummingbot）"""

    def __init__(self, api_key: str, secret_key: str, passphrase: str, time_provider: TimeSynchronizer):
        self.api_key: str = api_key
        self.secret_key: str = secret_key
        self.passphrase: str = passphrase
        self.time_provider: TimeSynchronizer = time_provider

    @staticmethod
    def keysort(dictionary: Dict[str, str]) -> Dict[str, str]:
        return OrderedDict(sorted(dictionary.items(), key=lambda t: t[0]))

    def _generate_signature(self, timestamp: str, method: str, path_url: str, body: Optional[str] = None) -> str:
        unsigned_signature = timestamp + method + path_url
        if body is not None:
            unsigned_signature += body

        signature = base64.b64encode(
            hmac.new(
                self.secret_key.encode("utf-8"),
                unsigned_signature.encode("utf-8"),
                hashlib.sha256).digest()).decode()
        return signature

    def authentication_headers(self, method: str, full_url: str, params: Optional[Dict] = None, data: Optional[str] = None) -> Dict[str, Any]:
        # Hummingbot 官方时间戳生成方式
        timestamp = datetime.datetime.fromtimestamp(self.time_provider.time(), datetime.UTC).isoformat(timespec="milliseconds")
        timestamp = timestamp.replace("+00:00", "Z")

        # 从完整 URL 提取路径（Hummingbot 官方逻辑）
        path_url = f"/api{full_url.split('/api')[-1]}"
        if params:
            query_string_components = urlencode(params)
            path_url = f"{path_url}?{query_string_components}"

        header = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": self._generate_signature(timestamp, method.upper(), path_url, data),
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
        }

        return header
