"""
CF Credential Service - Cloudflare 凭证解析服务

使用 DrissionPage 自动通过 Cloudflare 人机验证，获取 cf_clearance 等凭证。
支持代理和上下文伪装，确保获取的凭证可直接用于其他 HTTP 客户端。
"""

__version__ = "1.1.0"

from .service import CFCredentialService, get_service
from .models import CredentialRequest, CredentialResponse, BrowserContext
from .client import CFCredentialClient, CachedCredentialClient, CredentialResult
from .config import Config, get_config, load_config

__all__ = [
    "CFCredentialService",
    "get_service",
    "CredentialRequest",
    "CredentialResponse",
    "BrowserContext",
    "CFCredentialClient",
    "CachedCredentialClient",
    "CredentialResult",
    "Config",
    "get_config",
    "load_config",
]
