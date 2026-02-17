"""
数据模型定义
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class BrowserContext(BaseModel):
    """浏览器上下文配置，用于伪装信息统一"""
    
    # ============ 核心匹配参数（必须与请求方一致）============
    
    proxy: Optional[str] = Field(
        default=None,
        description="代理地址，必须与使用凭证的客户端使用相同代理（相同出口IP）"
    )
    
    user_agent: Optional[str] = Field(
        default=None,
        description="User-Agent 字符串，必须与使用凭证的客户端保持一致"
    )
    
    browser: Optional[str] = Field(
        default=None,
        description="浏览器/TLS指纹版本，如 chrome136，必须与客户端 impersonate 参数匹配"
    )
    
    # ============ 其他 Headers ============
    
    accept_language: Optional[str] = Field(
        default="en-US,en;q=0.9",
        description="Accept-Language 头"
    )
    accept_encoding: Optional[str] = Field(
        default="gzip, deflate, br",
        description="Accept-Encoding 头"
    )
    accept: Optional[str] = Field(
        default="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        description="Accept 头"
    )
    sec_ch_ua: Optional[str] = Field(
        default=None,
        description="Sec-CH-UA 头，Chrome 版本信息"
    )
    sec_ch_ua_platform: Optional[str] = Field(
        default='"macOS"',
        description="Sec-CH-UA-Platform 头"
    )
    sec_ch_ua_mobile: Optional[str] = Field(
        default="?0",
        description="Sec-CH-UA-Mobile 头"
    )
    
    # ============ 其他配置 ============
    
    existing_cookies: Optional[Dict[str, str]] = Field(
        default=None,
        description="已有 cookies，会在访问前注入"
    )
    
    timeout: int = Field(
        default=30,
        ge=5,
        le=120,
        description="等待 CF 验证完成的超时时间（秒）"
    )
    
    @field_validator('proxy')
    @classmethod
    def validate_proxy(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        valid_schemes = ('http://', 'https://', 'socks5://', 'socks5h://')
        if not any(v.lower().startswith(s) for s in valid_schemes):
            raise ValueError(f"Proxy must start with one of: {valid_schemes}")
        return v
    
    @field_validator('browser')
    @classmethod
    def validate_browser(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().lower()
        if not v:
            return None
        valid_browsers = ('chrome134', 'chrome135', 'chrome136', 'chrome137')
        if v not in valid_browsers:
            raise ValueError(f"Browser must be one of: {valid_browsers}")
        return v


class CredentialRequest(BaseModel):
    """凭证请求"""
    
    target_url: str = Field(
        description="目标网站 URL"
    )
    context: Optional[BrowserContext] = Field(
        default=None,
        description="浏览器上下文配置"
    )
    
    @field_validator('target_url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError("target_url must start with http:// or https://")
        return v


class CredentialResponse(BaseModel):
    """凭证响应"""
    
    success: bool = Field(description="是否成功获取凭证")
    cf_clearance: Optional[str] = Field(
        default=None,
        description="CF Clearance cookie 值"
    )
    cookies: Optional[Dict[str, str]] = Field(
        default=None,
        description="完整的 cookies 字典"
    )
    cookie_string: Optional[str] = Field(
        default=None,
        description="Cookie 字符串格式，可直接用于 HTTP 请求头"
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="实际使用的 User-Agent"
    )
    browser: Optional[str] = Field(
        default=None,
        description="实际使用的浏览器/TLS指纹版本，如 chrome136"
    )
    expires_at: Optional[float] = Field(
        default=None,
        description="预计过期时间戳（Unix 时间戳）"
    )
    error: Optional[str] = Field(
        default=None,
        description="错误信息"
    )
    challenge_type: Optional[str] = Field(
        default=None,
        description="遇到的挑战类型: js_challenge, turnstile, none"
    )


class ServiceHealth(BaseModel):
    """服务健康状态"""
    
    status: str = Field(default="healthy")
    version: str = Field(default="1.0.0")
    browser_available: bool = Field(default=False)
    active_sessions: int = Field(default=0)
