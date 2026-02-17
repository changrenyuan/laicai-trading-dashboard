"""
代理管理器 - 支持 HTTP/SOCKS5 代理
"""
import aiohttp
from typing import Optional, Union
import os


class ProxyManager:
    """代理管理器"""

    @staticmethod
    def get_proxy_from_config(config: dict) -> Optional[str]:
        """从配置获取代理"""
        proxy = config.get('proxy')
        if proxy:
            return proxy

        # 支持环境变量
        if 'HTTP_PROXY' in os.environ:
            return os.environ['HTTP_PROXY']
        if 'http_proxy' in os.environ:
            return os.environ['http_proxy']

        return None

    @staticmethod
    def parse_proxy_url(proxy_url: str) -> dict:
        """
        解析代理 URL

        支持的格式：
        - http://127.0.0.1:7890
        - socks5://127.0.0.1:7891
        - socks5h://127.0.0.1:7891
        """
        if not proxy_url:
            return {}

        # Clash 常用端口
        clash_proxies = {
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890',
            'socks5': 'socks5://127.0.0.1:7891',
        }

        # 检查是否是 Clash 简化配置
        if proxy_url.lower() in ['clash', 'clash-http', 'clash-socks5']:
            if proxy_url.lower() == 'clash' or proxy_url.lower() == 'clash-http':
                return {'http': clash_proxies['http'], 'https': clash_proxies['https']}
            else:
                return {'all': clash_proxies['socks5']}

        # 检查是否是端口号
        try:
            port = int(proxy_url)
            return {'http': f'http://127.0.0.1:{port}', 'https': f'http://127.0.0.1:{port}'}
        except ValueError:
            pass

        # 标准代理 URL
        return {'all': proxy_url}

    @staticmethod
    def get_aiohttp_proxy(proxy_config: dict) -> Optional[str]:
        """
        获取 aiohttp 使用的代理配置

        aiohttp 支持：
        - http://...
        - https://...
        - socks5://... (需要 aiohttp-socks)
        """
        if not proxy_config:
            return None

        # 如果有单独的 http/https 配置
        if 'http' in proxy_config:
            return proxy_config.get('http')

        # 如果有统一的代理
        if 'all' in proxy_config:
            proxy_url = proxy_config['all']

            # 检查是否需要安装 aiohttp-socks
            if proxy_url.startswith('socks5'):
                try:
                    import aiohttp_socks
                    return proxy_url
                except ImportError:
                    print("警告: SOCKS5 代理需要安装 aiohttp-socks")
                    print("运行: pip install aiohttp-socks")
                    return None

            return proxy_url

        return None

    @staticmethod
    def check_proxy(proxy_url: str) -> bool:
        """测试代理是否可用"""
        import requests

        try:
            proxies = {
                'http': proxy_url,
                'https': proxy_url,
            }

            response = requests.get(
                'https://www.okx.com/api/v5/public/time',
                proxies=proxies,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"代理测试失败: {e}")
            return False


# Clash 代理配置示例
CLASH_HTTP_PROXY = "http://127.0.0.1:7890"
CLASH_SOCKS5_PROXY = "socks5://127.0.0.1:7891"
