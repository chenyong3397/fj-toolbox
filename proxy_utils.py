#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理工具模块 - 通过 Cloudflare Worker 代理访问国内政府网站
使用方法：
  from proxy_utils import ProxySession
  
  # 创建支持代理的 Session
  s = ProxySession()
  
  # 像普通 Session 一样使用
  s.get("https://政府网站.com/api", ...)
"""

import requests
import urllib.parse
from requests import Session

# Cloudflare Worker 代理地址
PROXY_BASE = "https://fj-toolbox-proxy.chenyong94vip.workers.dev/proxy?url="

def encode_url(url):
    """将目标 URL 编码为代理参数"""
    return PROXY_BASE + urllib.parse.quote(url, safe='')

class ProxySession(Session):
    """
    支持代理的 Session 类
    自动将所有请求通过 Cloudflare Worker 代理
    """
    
    def request(self, method, url, **kwargs):
        """重写 request 方法，将 URL 重写为代理 URL"""
        proxy_url = encode_url(url)
        # 移除可能冲突的参数
        kwargs.pop('proxies', None)
        kwargs.pop('verify', None)
        return super().request(method, proxy_url, **kwargs)

def proxy_get(url, **kwargs):
    """通过代理发送 GET 请求（不使用 Session）"""
    proxy_url = encode_url(url)
    kwargs.pop('proxies', None)
    kwargs.pop('verify', None)
    return requests.get(proxy_url, **kwargs)

def proxy_post(url, **kwargs):
    """通过代理发送 POST 请求（不使用 Session）"""
    proxy_url = encode_url(url)
    kwargs.pop('proxies', None)
    kwargs.pop('verify', None)
    return requests.post(proxy_url, **kwargs)

# 测试函数
def test_proxy():
    """测试代理是否工作"""
    test_url = "https://httpbin.org/get"
    try:
        response = proxy_get(test_url, timeout=10)
        if response.status_code == 200:
            print("[OK] 代理测试成功")
            return True
        else:
            print(f"[ERROR] 代理测试失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] 代理测试失败: {e}")
        return False

if __name__ == "__main__":
    test_proxy()
