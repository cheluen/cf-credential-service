"""
简化测试脚本

不依赖 pytest，可直接运行测试核心逻辑
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import BrowserContext, CredentialRequest, CredentialResponse


def test_browser_context_defaults():
    """测试 BrowserContext 默认值"""
    ctx = BrowserContext()
    assert ctx.user_agent is None, "user_agent should be None by default"
    assert ctx.proxy is None, "proxy should be None by default"
    assert ctx.timeout == 30, "timeout should be 30 by default"
    assert ctx.accept_language == "en-US,en;q=0.9", "accept_language mismatch"
    print("✓ test_browser_context_defaults passed")


def test_proxy_validation_valid():
    """测试有效的代理格式"""
    valid_proxies = [
        "http://127.0.0.1:8080",
        "https://user:pass@proxy.com:443",
        "socks5://localhost:1080",
        "socks5h://127.0.0.1:9050",
    ]
    for proxy in valid_proxies:
        ctx = BrowserContext(proxy=proxy)
        assert ctx.proxy == proxy, f"proxy mismatch for {proxy}"
    print("✓ test_proxy_validation_valid passed")


def test_proxy_validation_invalid():
    """测试无效的代理格式"""
    try:
        BrowserContext(proxy="invalid-proxy")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("✓ test_proxy_validation_invalid passed")


def test_proxy_validation_empty():
    """测试空代理"""
    ctx = BrowserContext(proxy="")
    assert ctx.proxy is None, "Empty proxy should be None"
    print("✓ test_proxy_validation_empty passed")


def test_credential_request_valid_url():
    """测试有效的 URL"""
    req = CredentialRequest(target_url="https://example.com")
    assert req.target_url == "https://example.com"
    print("✓ test_credential_request_valid_url passed")


def test_credential_request_invalid_url():
    """测试无效的 URL"""
    try:
        CredentialRequest(target_url="not-a-url")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("✓ test_credential_request_invalid_url passed")


def test_credential_request_with_context():
    """测试带上下文的请求"""
    ctx = BrowserContext(proxy="http://localhost:8080")
    req = CredentialRequest(
        target_url="https://example.com",
        context=ctx,
    )
    assert req.context is not None, "context should not be None"
    assert req.context.proxy == "http://localhost:8080"
    print("✓ test_credential_request_with_context passed")


def test_credential_response_success():
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
    print("✓ test_credential_response_success passed")


def test_credential_response_failure():
    """测试失败响应"""
    resp = CredentialResponse(
        success=False,
        error="Browser not found",
    )
    assert resp.success is False
    assert resp.error == "Browser not found"
    assert resp.cf_clearance is None
    print("✓ test_credential_response_failure passed")


def test_service_extract_domain():
    """测试域名提取"""
    from src.service import CFCredentialService
    
    domain = CFCredentialService._extract_domain("https://example.com/path")
    assert domain == "example.com", f"Expected example.com, got {domain}"
    
    domain = CFCredentialService._extract_domain("https://sub.example.com:8080/path")
    assert domain == "sub.example.com:8080", f"Expected sub.example.com:8080, got {domain}"
    print("✓ test_service_extract_domain passed")


def test_service_merge_context():
    """测试上下文合并"""
    from src.service import CFCredentialService
    
    service = CFCredentialService.__new__(CFCredentialService)
    service.chrome_version = "chrome136"
    service.browser_path = "/usr/bin/chromium"
    
    merged = service._merge_context(None)
    assert "user_agent" in merged
    assert "chrome136" in merged["user_agent"].lower()
    print("✓ test_service_merge_context (defaults) passed")
    
    ctx = BrowserContext(
        user_agent="Custom User Agent",
        proxy="http://custom:8080",
    )
    merged = service._merge_context(ctx)
    assert merged["user_agent"] == "Custom User Agent"
    assert merged["proxy"] == "http://custom:8080"
    print("✓ test_service_merge_context (override) passed")


def run_all_tests():
    """运行所有测试"""
    print("Running tests...\n")
    
    tests = [
        test_browser_context_defaults,
        test_proxy_validation_valid,
        test_proxy_validation_invalid,
        test_proxy_validation_empty,
        test_credential_request_valid_url,
        test_credential_request_invalid_url,
        test_credential_request_with_context,
        test_credential_response_success,
        test_credential_response_failure,
        test_service_extract_domain,
        test_service_merge_context,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
