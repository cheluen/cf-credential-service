"""
HTTP API 服务

提供 REST API 接口获取 CF 凭证
"""

import logging
import secrets
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    CredentialRequest,
    CredentialResponse,
    BrowserContext,
    ServiceHealth,
)
from .service import get_service, CFCredentialService
from .config import get_config, Config

logger = logging.getLogger(__name__)

service: Optional[CFCredentialService] = None
config: Optional[Config] = None


def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """验证 API Key"""
    if not config or not config.api_key:
        return True
    
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Use X-API-Key header.",
        )
    
    if not secrets.compare_digest(x_api_key, config.api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )
    
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global service, config
    config = get_config()
    service = get_service()
    logger.info(f"CF Credential Service started on {config.host}:{config.port}")
    if config.api_key:
        logger.info("API key authentication enabled")
    yield
    logger.info("CF Credential Service stopped")


app = FastAPI(
    title="CF Credential Service",
    description="Cloudflare 凭证解析服务 - 自动通过 CF 人机验证获取凭证",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=ServiceHealth, tags=["系统"])
async def health_check():
    """健康检查（无需认证）"""
    return ServiceHealth(
        status="healthy",
        version="1.0.0",
        browser_available=service.is_browser_available if service else False,
        active_sessions=service.active_sessions if service else 0,
    )


@app.post("/api/v1/credentials", response_model=CredentialResponse, tags=["凭证"])
async def get_credentials(request: CredentialRequest, auth: bool = Depends(verify_api_key)):
    """
    获取 CF 凭证
    
    - **target_url**: 目标网站 URL
    - **context**: 浏览器上下文配置（可选）
      - **proxy**: 代理地址 (http/https/socks5)
      - **user_agent**: User-Agent 字符串
      - **existing_cookies**: 已有 cookies
      - **timeout**: 超时时间（秒）
    
    返回:
    - **cf_clearance**: CF Clearance cookie
    - **cookies**: 完整 cookies 字典
    - **cookie_string**: Cookie 字符串
    - **user_agent**: 实际使用的 User-Agent
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    if not service.is_browser_available:
        raise HTTPException(
            status_code=503, 
            detail="Browser not available. Please install chromium."
        )
    
    logger.info(f"Received credential request for: {request.target_url}")
    
    # 脱敏：记录代理信息时隐藏认证
    if request.context and request.context.proxy:
        import re
        proxy_display = re.sub(
            r'(https?://|socks5://)([^:]+):([^@]+)@',
            r'\1***:***@',
            request.context.proxy
        )
        logger.info(f"Request proxy: {proxy_display[:40]}...")
    
    response = await service.get_credentials(
        target_url=request.target_url,
        context=request.context,
    )
    
    if not response.success:
        logger.error(f"Failed to get credentials: {response.error}")
    
    return response


@app.post("/api/v1/credentials/simple", response_model=CredentialResponse, tags=["凭证"])
async def get_credentials_simple(
    target_url: str,
    proxy: Optional[str] = None,
    user_agent: Optional[str] = None,
    timeout: int = 30,
    auth: bool = Depends(verify_api_key),
):
    """
    简化的凭证获取接口（GET 参数方式）
    
    - **target_url**: 目标网站 URL
    - **proxy**: 代理地址 (可选)
    - **user_agent**: User-Agent (可选)
    - **timeout**: 超时时间（秒）
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    context = BrowserContext(
        proxy=proxy,
        user_agent=user_agent,
        timeout=timeout,
    )
    
    return await service.get_credentials(
        target_url=target_url,
        context=context,
    )


@app.get("/browser/status", tags=["系统"])
async def browser_status():
    """检查浏览器状态"""
    if not service:
        return {"available": False, "path": None}
    
    return {
        "available": service.is_browser_available,
        "path": service.browser_path,
    }
