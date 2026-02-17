"""
CF Credential Service 客户端

方便其他服务调用凭证服务
"""

import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
import httpx


@dataclass
class CredentialResult:
    """凭证结果"""
    success: bool
    cf_clearance: Optional[str] = None
    cookies: Optional[Dict[str, str]] = None
    cookie_string: Optional[str] = None
    user_agent: Optional[str] = None
    expires_at: Optional[float] = None
    error: Optional[str] = None


class CFCredentialClient:
    """
    CF 凭证服务客户端
    
    使用示例:
        client = CFCredentialClient("http://localhost:8080")
        
        # 简单获取
        result = client.get_credentials("https://example.com")
        
        # 带代理
        result = client.get_credentials(
            "https://example.com",
            proxy="http://user:pass@proxy:8080",
            user_agent="Mozilla/5.0 ..."
        )
        
        if result.success:
            print(f"cf_clearance: {result.cf_clearance}")
    """
    
    def __init__(
        self,
        service_url: str = "http://localhost:8080",
        timeout: float = 60.0,
    ):
        self.service_url = service_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None
    
    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client
    
    def get_credentials(
        self,
        target_url: str,
        proxy: Optional[str] = None,
        user_agent: Optional[str] = None,
        existing_cookies: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> CredentialResult:
        """
        获取 CF 凭证
        
        Args:
            target_url: 目标网站 URL
            proxy: 代理地址
            user_agent: User-Agent
            existing_cookies: 已有 cookies
            timeout: 超时时间
            
        Returns:
            CredentialResult: 凭证结果
        """
        client = self._get_client()
        
        payload = {
            "target_url": target_url,
            "context": {}
        }
        
        if proxy:
            payload["context"]["proxy"] = proxy
        if user_agent:
            payload["context"]["user_agent"] = user_agent
        if existing_cookies:
            payload["context"]["existing_cookies"] = existing_cookies
        if timeout:
            payload["context"]["timeout"] = timeout
        
        if not payload["context"]:
            payload["context"] = None
        
        try:
            resp = client.post(
                f"{self.service_url}/api/v1/credentials",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            
            return CredentialResult(
                success=data.get("success", False),
                cf_clearance=data.get("cf_clearance"),
                cookies=data.get("cookies"),
                cookie_string=data.get("cookie_string"),
                user_agent=data.get("user_agent"),
                expires_at=data.get("expires_at"),
                error=data.get("error"),
            )
        except Exception as e:
            return CredentialResult(
                success=False,
                error=str(e),
            )
    
    def get_credentials_simple(
        self,
        target_url: str,
        proxy: Optional[str] = None,
        user_agent: Optional[str] = None,
        timeout: int = 30,
    ) -> CredentialResult:
        """
        简化接口获取凭证
        """
        client = self._get_client()
        
        params = {"target_url": target_url, "timeout": timeout}
        if proxy:
            params["proxy"] = proxy
        if user_agent:
            params["user_agent"] = user_agent
        
        try:
            resp = client.post(
                f"{self.service_url}/api/v1/credentials/simple",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            
            return CredentialResult(
                success=data.get("success", False),
                cf_clearance=data.get("cf_clearance"),
                cookies=data.get("cookies"),
                cookie_string=data.get("cookie_string"),
                user_agent=data.get("user_agent"),
                expires_at=data.get("expires_at"),
                error=data.get("error"),
            )
        except Exception as e:
            return CredentialResult(
                success=False,
                error=str(e),
            )
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        client = self._get_client()
        resp = client.get(f"{self.service_url}/health")
        return resp.json()
    
    def close(self):
        """关闭客户端"""
        if self._client:
            self._client.close()
            self._client = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


class CachedCredentialClient:
    """
    带缓存的凭证客户端
    
    自动缓存凭证，过期前自动刷新
    """
    
    def __init__(
        self,
        service_url: str = "http://localhost:8080",
        refresh_before_expire: float = 300.0,
    ):
        self.client = CFCredentialClient(service_url)
        self.refresh_before_expire = refresh_before_expire
        self._cache: Dict[str, CredentialResult] = {}
    
    def get_credentials(
        self,
        target_url: str,
        proxy: Optional[str] = None,
        user_agent: Optional[str] = None,
        force_refresh: bool = False,
    ) -> CredentialResult:
        """
        获取凭证（带缓存）
        """
        cache_key = f"{target_url}|{proxy}|{user_agent}"
        
        cached = self._cache.get(cache_key)
        if cached and not force_refresh:
            if cached.expires_at and cached.expires_at > time.time() + self.refresh_before_expire:
                return cached
        
        result = self.client.get_credentials(
            target_url=target_url,
            proxy=proxy,
            user_agent=user_agent,
        )
        
        if result.success:
            self._cache[cache_key] = result
        
        return result
    
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
    
    def close(self):
        """关闭客户端"""
        self.client.close()
