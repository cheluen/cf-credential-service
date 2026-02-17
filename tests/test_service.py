"""
测试用例
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from src.models import BrowserContext, CredentialRequest, CredentialResponse
from src.service import CFCredentialService


class TestBrowserContext:
    """测试 BrowserContext 模型"""
    
    def test_default_values(self):
        """测试默认值"""
        ctx = BrowserContext()
        assert ctx.user_agent is None
        assert ctx.proxy is None
        assert ctx.timeout == 30
        assert ctx.accept_language == "en-US,en;q=0.9"
    
    def test_proxy_validation_valid(self):
        """测试有效的代理格式"""
        valid_proxies = [
            "http://127.0.0.1:8080",
            "https://user:pass@proxy.com:443",
            "socks5://localhost:1080",
            "socks5h://127.0.0.1:9050",
        ]
        for proxy in valid_proxies:
            ctx = BrowserContext(proxy=proxy)
            assert ctx.proxy == proxy
    
    def test_proxy_validation_invalid(self):
        """测试无效的代理格式"""
        with pytest.raises(ValueError):
            BrowserContext(proxy="invalid-proxy")
    
    def test_proxy_validation_empty(self):
        """测试空代理"""
        ctx = BrowserContext(proxy="")
        assert ctx.proxy is None


class TestCredentialRequest:
    """测试 CredentialRequest 模型"""
    
    def test_valid_url(self):
        """测试有效的 URL"""
        req = CredentialRequest(target_url="https://example.com")
        assert req.target_url == "https://example.com"
    
    def test_invalid_url(self):
        """测试无效的 URL"""
        with pytest.raises(ValueError):
            CredentialRequest(target_url="not-a-url")
    
    def test_with_context(self):
        """测试带上下文的请求"""
        ctx = BrowserContext(proxy="http://localhost:8080")
        req = CredentialRequest(
            target_url="https://example.com",
            context=ctx,
        )
        assert req.context is not None
        assert req.context.proxy == "http://localhost:8080"


class TestCredentialResponse:
    """测试 CredentialResponse 模型"""
    
    def test_success_response(self):
        """测试成功响应"""
        resp = CredentialResponse(
            success=True,
            cf_clearance="abc123",
            cookies={"cf_clearance": "abc123", "session": "xyz"},
            cookie_string="cf_clearance=abc123; session=xyz",
            user_agent="Mozilla/5.0...",
        )
        assert resp.success is True
        assert resp.cf_clearance == "abc123"
        assert resp.error is None
    
    def test_failure_response(self):
        """测试失败响应"""
        resp = CredentialResponse(
            success=False,
            error="Browser not found",
        )
        assert resp.success is False
        assert resp.error == "Browser not found"
        assert resp.cf_clearance is None


class TestCFCredentialService:
    """测试 CFCredentialService"""
    
    def test_find_browser_not_found(self):
        """测试找不到浏览器"""
        with patch.object(CFCredentialService, '_find_browser', return_value=None):
            service = CFCredentialService.__new__(CFCredentialService)
            service.browser_path = None
            assert service.is_browser_available is False
    
    def test_merge_context_defaults(self):
        """测试上下文合并默认值"""
        service = CFCredentialService.__new__(CFCredentialService)
        service.chrome_version = "chrome136"
        service.browser_path = "/usr/bin/chromium"
        
        merged = service._merge_context(None)
        assert "user_agent" in merged
        assert "chrome136" in merged["user_agent"].lower()
    
    def test_merge_context_override(self):
        """测试上下文用户覆盖"""
        service = CFCredentialService.__new__(CFCredentialService)
        service.chrome_version = "chrome136"
        service.browser_path = "/usr/bin/chromium"
        
        ctx = BrowserContext(
            user_agent="Custom User Agent",
            proxy="http://custom:8080",
        )
        merged = service._merge_context(ctx)
        
        assert merged["user_agent"] == "Custom User Agent"
        assert merged["proxy"] == "http://custom:8080"
    
    @pytest.mark.asyncio
    async def test_get_credentials_no_browser(self):
        """测试没有浏览器时返回错误"""
        service = CFCredentialService.__new__(CFCredentialService)
        service.browser_path = None
        service._lock = asyncio.Lock()
        service._active_sessions = 0
        
        result = await service.get_credentials("https://example.com")
        
        assert result.success is False
        assert result.error is not None
        assert "No browser found" in result.error
    
    def test_extract_domain(self):
        """测试域名提取"""
        domain = CFCredentialService._extract_domain("https://example.com/path")
        assert domain == "example.com"
        
        domain = CFCredentialService._extract_domain("https://sub.example.com:8080/path")
        assert domain == "sub.example.com:8080"


class TestServiceIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_context_propagation(self):
        """测试上下文正确传递"""
        service = CFCredentialService.__new__(CFCredentialService)
        service.chrome_version = "chrome136"
        service.browser_path = None
        service._lock = asyncio.Lock()
        service._active_sessions = 0
        
        ctx = BrowserContext(
            user_agent="TestAgent/1.0",
            proxy="http://test:8080",
            timeout=20,
        )
        
        merged = service._merge_context(ctx)
        
        assert merged["user_agent"] == "TestAgent/1.0"
        assert merged["proxy"] == "http://test:8080"
        assert merged["timeout"] == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
