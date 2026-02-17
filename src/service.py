"""
CF 凭证服务核心实现

使用 DrissionPage 自动通过 Cloudflare 人机���证
"""

import asyncio
import time
import tempfile
import os
from typing import Optional, Dict, Any
from pathlib import Path
import logging

from .models import BrowserContext, CredentialResponse
from .config import get_config

logger = logging.getLogger(__name__)

_BROWSER_PATHS = [
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "chrome",
    "chromium",
]

_DEFAULT_USER_AGENTS = {
    "chrome136": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "chrome135": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "chrome134": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
}

_DEFAULT_SEC_CH_UA = {
    "chrome136": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    "chrome135": '"Chromium";v="135", "Google Chrome";v="135", "Not.A/Brand";v="99"',
    "chrome134": '"Chromium";v="134", "Google Chrome";v="134", "Not.A/Brand";v="99"',
}


class CFCredentialService:
    """Cloudflare 凭证解析服务"""
    
    def __init__(
        self,
        browser_path: Optional[str] = None,
        headless: bool = True,
        chrome_version: str = "chrome136",
    ):
        config = get_config()
        
        self.browser_path = browser_path or config.browser_path or self._find_browser()
        self.headless = headless if headless != True else config.headless
        self.chrome_version = chrome_version if chrome_version != "chrome136" else config.chrome_version
        self.default_proxy = config.default_proxy
        self.default_user_agent = config.default_user_agent
        self.default_timeout = config.default_timeout
        
        self._page = None
        self._lock = asyncio.Lock()
        self._active_sessions = 0
        
    @staticmethod
    def _find_browser() -> Optional[str]:
        """查找可用的浏览器路径"""
        for path in _BROWSER_PATHS:
            if Path(path).exists():
                logger.info(f"Found browser at: {path}")
                return path
        logger.warning("No browser found in standard paths")
        return None
    
    def _get_default_context(self) -> Dict[str, Any]:
        """获取默认上下文配置"""
        return {
            "user_agent": _DEFAULT_USER_AGENTS.get(self.chrome_version, _DEFAULT_USER_AGENTS["chrome136"]),
            "sec_ch_ua": _DEFAULT_SEC_CH_UA.get(self.chrome_version, _DEFAULT_SEC_CH_UA["chrome136"]),
            "accept_language": "en-US,en;q=0.9",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "browser": self.chrome_version,
        }
    
    def _merge_context(self, context: Optional[BrowserContext]) -> Dict[str, Any]:
        """合并用户上下文和默认上下文"""
        defaults = self._get_default_context()
        
        # 应用配置文件的默认值（仅当请求方未传入时）
        if self.default_proxy:
            defaults["proxy"] = self.default_proxy
        if self.default_user_agent:
            defaults["user_agent"] = self.default_user_agent
        if self.default_timeout:
            defaults["timeout"] = self.default_timeout
        
        if context is None:
            return defaults
        
        merged = defaults.copy()
        
        # 核心匹配参数（必须由请求方传入）
        if context.proxy:
            merged["proxy"] = context.proxy
        if context.user_agent:
            merged["user_agent"] = context.user_agent
        if context.browser:
            merged["browser"] = context.browser
            # 同步更新 UA 和 sec_ch_ua 以匹配 browser 版本
            if context.browser in _DEFAULT_USER_AGENTS:
                merged["user_agent"] = _DEFAULT_USER_AGENTS[context.browser]
            if context.browser in _DEFAULT_SEC_CH_UA:
                merged["sec_ch_ua"] = _DEFAULT_SEC_CH_UA[context.browser]
        
        # 其他 headers
        if context.accept_language:
            merged["accept_language"] = context.accept_language
        if context.accept:
            merged["accept"] = context.accept
        if context.existing_cookies:
            merged["existing_cookies"] = context.existing_cookies
        if context.timeout:
            merged["timeout"] = context.timeout
            
        return merged
    
    async def get_credentials(
        self,
        target_url: str,
        context: Optional[BrowserContext] = None,
    ) -> CredentialResponse:
        """
        获取 CF 凭证
        
        Args:
            target_url: 目标网站 URL
            context: 浏览器上下文配置
            
        Returns:
            CredentialResponse: 包含 cf_clearance 等凭证
        """
        async with self._lock:
            self._active_sessions += 1
            try:
                return await self._resolve_credentials(target_url, context)
            finally:
                self._active_sessions -= 1
    
    async def _resolve_credentials(
        self,
        target_url: str,
        context: Optional[BrowserContext] = None,
    ) -> CredentialResponse:
        """实际解析凭证的逻辑"""
        ctx = self._merge_context(context)
        
        try:
            from DrissionPage import ChromiumPage, ChromiumOptions
        except ImportError:
            return CredentialResponse(
                success=False,
                error="DrissionPage not installed. Run: pip install DrissionPage"
            )
        
        if not self.browser_path:
            return CredentialResponse(
                success=False,
                error="No browser found. Please install chromium or set browser_path."
            )
        
        try:
            co = ChromiumOptions()
            co.set_browser_path(self.browser_path)
            
            if self.headless:
                co.headless(True)
            
            extension_path = None
            if ctx.get("proxy"):
                proxy_url = ctx["proxy"]
                if "@" in proxy_url:
                    extension_path = self._create_proxy_auth_extension(proxy_url)
                    if extension_path:
                        co.set_argument(f"--load-extension={extension_path}")
                        proxy_without_auth = self._strip_proxy_auth(proxy_url)
                        co.set_proxy(proxy_without_auth)
                        logger.info("Using proxy with auth extension")
                else:
                    co.set_proxy(proxy_url)
                
                proxy_display = proxy_url
                if "@" in proxy_display:
                    import re
                    proxy_display = re.sub(r'(https?://|socks5://)([^:]+):([^@]+)@', r'\1***:***@', proxy_display)
                logger.info(f"Using proxy: {proxy_display[:30]}...")
            
            if ctx.get("user_agent"):
                co.set_user_agent(ctx["user_agent"])
            
            co.set_argument("--no-sandbox")
            co.set_argument("--disable-dev-shm-usage")
            co.set_argument("--disable-gpu")
            co.set_argument("--disable-blink-features=AutomationControlled")
            co.set_argument("--window-size=1920,1080")
            
            if ctx.get("accept_language"):
                co.set_argument(f"--lang={ctx['accept_language'].split(',')[0]}")
            
            logger.info(f"Starting browser for: {target_url}")
            page = ChromiumPage(co)
            
            try:
                if ctx.get("existing_cookies"):
                    domain = self._extract_domain(target_url)
                    for name, value in ctx["existing_cookies"].items():
                        cookie_dict = {
                            "name": name,
                            "value": value,
                            "domain": domain,
                        }
                        page.set.cookies(cookie_dict)
                    logger.info("Injected existing cookies")
                
                page.get(target_url)
                
                challenge_type = await self._wait_for_cf_challenge(page, ctx.get("timeout", 30))
                
                cookies = page.cookies(all_domains=True, all_info=True)
                
                cookie_dict = {}
                cf_clearance = None
                for cookie in cookies:
                    name = cookie.get("name", "")
                    value = cookie.get("value", "")
                    if name and value:
                        cookie_dict[name] = value
                        if name == "cf_clearance":
                            cf_clearance = value
                
                if not cf_clearance:
                    if challenge_type == "none":
                        logger.warning("No CF challenge detected and no cf_clearance found")
                    else:
                        logger.warning(f"CF challenge ({challenge_type}) passed but no cf_clearance found")
                
                cookie_string = "; ".join(f"{k}={v}" for k, v in cookie_dict.items() if v)
                
                expires_at = time.time() + 3600 * 0.5
                
                logger.info(f"Successfully obtained cf_clearance: {cf_clearance[:20] if cf_clearance else 'N/A'}...")
                
                return CredentialResponse(
                    success=True,
                    cf_clearance=cf_clearance,
                    cookies=cookie_dict,
                    cookie_string=cookie_string,
                    user_agent=ctx.get("user_agent"),
                    browser=ctx.get("browser"),
                    expires_at=expires_at,
                    challenge_type=challenge_type,
                )
                
            finally:
                page.quit()
                if extension_path and os.path.exists(extension_path):
                    import shutil
                    try:
                        shutil.rmtree(extension_path)
                    except Exception:
                        pass
                
        except Exception as e:
            error_msg = self._sanitize_error(str(e))
            logger.error(f"Failed to get credentials: {error_msg}")
            return CredentialResponse(
                success=False,
                error=error_msg,
            )
    
    async def _wait_for_cf_challenge(self, page, timeout: int = 30) -> str:
        """
        等待 CF 验证完成
        
        Returns:
            str: 挑战类型 (js_challenge, turnstile, none)
        """
        challenge_type = "none"
        start_time = time.time()
        last_url = ""
        
        while time.time() - start_time < timeout:
            try:
                current_url = page.url
                page_html = page.html.lower()
                
                if "challenge-running" in page_html or "cf-challenge-running" in page_html:
                    challenge_type = "js_challenge"
                    if time.time() - start_time > 5:
                        logger.info("Detected CF JS challenge, waiting...")
                elif "turnstile" in page_html or "challenges.cloudflare.com" in page_html:
                    challenge_type = "turnstile"
                    if time.time() - start_time > 5:
                        logger.info("Detected CF Turnstile, waiting...")
                
                cookies = page.cookies(all_domains=True, all_info=True)
                has_cf_clearance = any(c.get("name") == "cf_clearance" for c in cookies)
                
                no_challenge = (
                    "challenge" not in page_html and
                    "turnstile" not in page_html and
                    "challenges.cloudflare.com" not in page_html
                )
                
                url_changed = last_url and current_url != last_url and "challenge" not in current_url.lower()
                last_url = current_url
                
                if has_cf_clearance or (no_challenge and challenge_type != "none"):
                    logger.info(f"CF challenge ({challenge_type}) passed, cf_clearance: {has_cf_clearance}")
                    return challenge_type
                
                if no_challenge and challenge_type == "none":
                    logger.info("No CF challenge detected")
                    return "none"
                    
            except Exception as e:
                logger.debug(f"Error checking CF challenge: {e}")
            
            await asyncio.sleep(0.5)
        
        if challenge_type != "none":
            logger.warning(f"CF challenge ({challenge_type}) may not have completed within timeout")
        
        return challenge_type
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """从 URL 提取域名"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc
    
    @staticmethod
    def _strip_proxy_auth(proxy_url: str) -> str:
        """移除代理 URL 中的认证信息"""
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(proxy_url)
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        scheme = parsed.scheme or "http"
        return f"{scheme}://{netloc}"
    
    @staticmethod
    def _sanitize_error(error_msg: str) -> str:
        """清理错误消息中的敏感信息"""
        import re
        result = error_msg
        # 隐藏代理 URL 中的认证信息
        result = re.sub(
            r'(https?://|socks5://)([^:]+):([^@]+)@',
            r'\1***:***@',
            result
        )
        # 隐藏 cf_clearance 值
        result = re.sub(
            r'cf_clearance[=:\s]+[^\s;]+',
            'cf_clearance=***',
            result
        )
        # 隐藏密码
        result = re.sub(
            r'(password|passwd|pwd)[=:]\s*\S+',
            r'\1=***',
            result,
            flags=re.IGNORECASE
        )
        return result
    
    @staticmethod
    def _create_proxy_auth_extension(proxy_url: str) -> Optional[str]:
        """
        创建 Chrome 扩展程序处理代理认证
        
        Args:
            proxy_url: 代理 URL，格式如 http://user:pass@host:port
            
        Returns:
            扩展程序目录路径
        """
        from urllib.parse import urlparse
        
        parsed = urlparse(proxy_url)
        if not parsed.username or not parsed.password:
            return None
        
        host = parsed.hostname or ""
        port = parsed.port or 80
        username = parsed.username
        password = parsed.password
        
        tmp_dir = tempfile.mkdtemp(prefix="proxy_ext_")
        
        manifest = '''{
  "version": "1.0.0",
  "manifest_version": 3,
  "name": "Proxy Auth",
  "permissions": ["webRequest", "webRequestAuthProvider"],
  "background": {
    "service_worker": "background.js"
  }
}'''
        
        background = f'''chrome.webRequest.onAuthRequired.addListener(
  function(details, callbackFn) {{
    callbackFn({{
      authCredentials: {{
        username: "{username}",
        password: "{password}"
      }}
    }});
  }},
  {{urls: ["<all_urls>"]}},
  ["asyncBlocking"]
);'''
        
        with open(os.path.join(tmp_dir, "manifest.json"), "w") as f:
            f.write(manifest)
        with open(os.path.join(tmp_dir, "background.js"), "w") as f:
            f.write(background)
        
        logger.debug(f"Created proxy auth extension at {tmp_dir}")
        return tmp_dir
    
    @property
    def is_browser_available(self) -> bool:
        """检查浏览器是否可用"""
        return self.browser_path is not None
    
    @property
    def active_sessions(self) -> int:
        """当前活跃会话数"""
        return self._active_sessions


_service_instance: Optional[CFCredentialService] = None


def get_service() -> CFCredentialService:
    """获取全局服务实例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = CFCredentialService()
    return _service_instance
