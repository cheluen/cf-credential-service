"""
CF Credential Service 配置管理

支持配置文件和环境变量，环境变量优先。
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Config:
    """服务配置"""
    
    # 服务配置
    port: int = 20001
    host: str = "0.0.0.0"
    
    # 认证配置
    password: str = ""
    
    # 浏览器配置
    browser_path: Optional[str] = None
    headless: bool = True
    chrome_version: str = "chrome136"
    
    # 默认代理
    default_proxy: str = ""
    
    # 默认 User-Agent
    default_user_agent: str = ""

    # 超时配置
    default_timeout: int = 90


def _load_config_file() -> dict:
    """从配置文件加载配置"""
    config_paths = [
        Path("config.toml"),
        Path("config.json"),
        Path.home() / ".cf-service" / "config.toml",
        Path.home() / ".cf-service" / "config.json",
        Path("/etc/cf-service/config.toml"),
        Path("/etc/cf-service/config.json"),
    ]
    
    for config_path in config_paths:
        if not config_path.exists():
            continue
        
        try:
            content = config_path.read_text()
            
            if config_path.suffix == ".json":
                import json
                return json.loads(content)
            else:
                # TOML
                try:
                    import tomllib
                except ImportError:
                    import tomli as tomllib
                return tomllib.loads(content)
        except Exception:
            continue
    
    return {}


def _get_env(key: str, default: str = "") -> str:
    """获取环境变量"""
    return os.environ.get(key, default)


def _get_env_int(key: str, default: int) -> int:
    """获取环境变量（整数）"""
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_env_bool(key: str, default: bool) -> bool:
    """获取环境变量（布尔值）"""
    value = os.environ.get(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def load_config() -> Config:
    """
    加载配置
    
    优先级：环境变量 > 配置文件 > 默认值
    """
    # 从文件加载
    file_config = _load_config_file()
    
    # 构建配置
    config = Config()
    
    # 服务配置
    config.port = _get_env_int("PORT", file_config.get("port", config.port))
    config.host = _get_env("HOST", file_config.get("host", config.host))
    
    # 认证配置
    config.password = _get_env("CF_SERVICE_PASSWORD", file_config.get("password", ""))
    
    # 浏览器配置
    config.browser_path = _get_env("CF_BROWSER_PATH", file_config.get("browser_path", "")) or None
    config.headless = _get_env_bool("CF_HEADLESS", file_config.get("headless", True))
    config.chrome_version = _get_env("CF_CHROME_VERSION", file_config.get("chrome_version", "chrome136"))
    
    # 默认代理
    config.default_proxy = _get_env("CF_DEFAULT_PROXY", file_config.get("default_proxy", ""))
    
    # 默认 User-Agent
    config.default_user_agent = _get_env("CF_DEFAULT_USER_AGENT", file_config.get("default_user_agent", ""))
    
    # 超时配置
    config.default_timeout = _get_env_int("CF_DEFAULT_TIMEOUT", file_config.get("default_timeout", 90))
    
    return config


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = load_config()
    return _config
