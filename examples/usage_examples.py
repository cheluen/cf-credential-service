"""
使用示例

演示如何调用 CF Credential Service 获取凭证
"""

from src import CFCredentialClient, CachedCredentialClient


def example_basic():
    """基本用法示例"""
    client = CFCredentialClient("http://localhost:8080")
    
    result = client.get_credentials(
        target_url="https://example.com",
        proxy="http://user:pass@proxy:8080",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    )
    
    if result.success:
        print(f"cf_clearance: {result.cf_clearance}")
        print(f"cookies: {result.cookies}")
        print(f"cookie_string: {result.cookie_string}")
    else:
        print(f"Error: {result.error}")
    
    client.close()


def example_with_cache():
    """带缓存的用法示例"""
    client = CachedCredentialClient(
        service_url="http://localhost:8080",
        refresh_before_expire=300.0,
    )
    
    result = client.get_credentials(
        target_url="https://example.com",
        proxy="http://proxy:8080",
    )
    
    if result.success:
        print(f"Got cached credential: {result.cf_clearance[:20]}...")
    
    client.close()


def example_with_curl_cffi():
    """
    配合 curl_cffi 使用示例
    
    关键点：
    1. 使用相同的代理
    2. 使用相同的 User-Agent
    3. 使用 impersonate 参数匹配 Chrome 版本
    """
    from curl_cffi import requests
    
    client = CFCredentialClient("http://localhost:8080")
    
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    proxy = "http://your-proxy:8080"
    
    result = client.get_credentials(
        target_url="https://target-site.com",
        proxy=proxy,
        user_agent=user_agent,
    )
    
    if not result.success:
        print(f"Failed to get credentials: {result.error}")
        client.close()
        return
    
    session = requests.Session()
    session.cookies.set("cf_clearance", result.cf_clearance)
    session.proxies = {"http": proxy, "https": proxy}
    
    response = session.get(
        "https://target-site.com/api/data",
        impersonate="chrome136",
        headers={"User-Agent": user_agent},
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text[:200]}...")
    
    client.close()


def example_context_manager():
    """使用上下文管理器"""
    with CFCredentialClient("http://localhost:8080") as client:
        result = client.get_credentials_simple(
            target_url="https://example.com",
            proxy="http://proxy:8080",
        )
        print(f"Success: {result.success}")


if __name__ == "__main__":
    print("Example 1: Basic usage")
    example_basic()
    
    print("\nExample 2: With cache")
    example_with_cache()
    
    print("\nExample 3: With curl_cffi")
    example_with_curl_cffi()
    
    print("\nExample 4: Context manager")
    example_context_manager()
