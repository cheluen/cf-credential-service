# CF Credential Service

Cloudflare 凭证解析服务 - 使用 DrissionPage 自动通过 CF 人机验证获取凭证。

## 核心原理

CF 凭证（cf_clearance）与以下因素绑定：
1. **出口 IP** - 获取凭证时的代理出口 IP
2. **User-Agent** - 浏览器标识
3. **TLS 指纹** - 浏览器 SSL/TLS 握手特征

**调用者必须确保**：获取凭证时使用的 proxy、browser 参数，与后续请求时完全一致，凭证才能生效。

## 功能特性

- 自动通过 Cloudflare JS Challenge 和 Turnstile 验证
- 支持代理（HTTP/HTTPS/SOCKS5），包括带认证的代理
- TLS 指纹匹配（chrome134/135/136/137）
- X-API-Key 认证保护
- Docker 一键部署，支持 amd64/arm64

## 快速开始

### Docker 部署（推荐）

```bash
docker run -d \
  -p 20001:20001 \
  -e CF_SERVICE_API_KEY=your_api_key \
  -e CF_SERVICE_PROXY=http://user:pass@proxy:8080 \
  ghcr.io/cheluen/cf-credential-service:latest
```

### 本地运行

```bash
pip install -r requirements.txt

# 方式一：使用配置文件
cp config.example.toml config.toml
# 编辑 config.toml
python main.py

# 方式二：使用环境变量
CF_SERVICE_API_KEY=your_api_key \
CF_SERVICE_PROXY=http://user:pass@proxy:8080 \
python main.py
```

## 配置

配置优先级：**环境变量 > 配置文件 > 默认值**

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CF_SERVICE_PORT` | 服务端口 | 20001 |
| `CF_SERVICE_HOST` | 监听地址 | 0.0.0.0 |
| `CF_SERVICE_API_KEY` | API Key | - |
| `CF_SERVICE_PROXY` | 默认代理 | - |
| `CF_BROWSER_PATH` | Chrome/Chromium 路径 | 自动检测 |
| `CF_HEADLESS` | 无头模式 | true |
| `CF_DEFAULT_TIMEOUT` | 默认超时时间（秒） | 90 |

### 配置文件

复制 `config.example.toml` 为 `config.toml`：

```toml
# 服务配置
port = 20001
host = "0.0.0.0"

# API Key（通过 X-API-Key 请求头传递）
api_key = "your_api_key_here"

# 默认代理（调用者未传入时使用）
default_proxy = "http://user:pass@proxy_host:proxy_port"

# 浏览器配置
headless = true
# browser_path = "/usr/bin/chromium"

# 超时配置
default_timeout = 90
```

配置文件搜索路径：
1. `./config.toml` 或 `./config.json`
2. `~/.cf-service/config.toml` 或 `~/.cf-service/config.json`
3. `/etc/cf-service/config.toml` 或 `/etc/cf-service/config.json`

## API 接口

### 健康检查（无需认证）

```http
GET /health
```

响应：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "browser_available": true,
  "active_sessions": 0
}
```

### 获取凭证

```http
POST /api/v1/credentials
Content-Type: application/json
X-API-Key: your_api_key

{
  "target_url": "https://example.com",
  "context": {
    "proxy": "http://proxy_user:proxy_pass@proxy_host:8080",
    "browser": "chrome136"
  }
}
```

**context 参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `proxy` | string | 推荐传入 | 代理地址，必须与后续请求使用相同代理 |
| `browser` | string | 推荐传入 | TLS 指纹版本：`chrome134`/`chrome135`/`chrome136`/`chrome137` |
| `user_agent` | string | 否 | User-Agent，不传则根据 browser 自动设置 |
| `timeout` | int | 否 | 超时时间（秒），默认 90，范围 5-120 |
| `existing_cookies` | object | 否 | 已有 cookies，会在访问前注入 |

**响应：**

```json
{
  "success": true,
  "cf_clearance": "abc123...",
  "cookies": {"cf_clearance": "abc123...", ...},
  "cookie_string": "cf_clearance=abc123...; ...",
  "user_agent": "Mozilla/5.0 ...",
  "browser": "chrome136",
  "expires_at": 1708089600.0,
  "challenge_type": "js_challenge",
  "error": null
}
```

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 是否成功 |
| `cf_clearance` | string | CF Clearance cookie |
| `cookies` | object | 完整 cookies 字典 |
| `cookie_string` | string | Cookie 字符串，可直接用于请求头 |
| `user_agent` | string | 实际使用的 User-Agent |
| `browser` | string | 实际使用的 TLS 指纹版本 |
| `expires_at` | float | 预计过期时间戳 |
| `challenge_type` | string | 挑战类型：`js_challenge`/`turnstile`/`none` |
| `error` | string | 错误信息 |

### 简化接口

```http
POST /api/v1/credentials/simple?target_url=https://example.com&proxy=http://proxy:8080&browser=chrome136
X-API-Key: your_api_key
```

### 浏览器状态

```http
GET /browser/status
```

## 使用示例

### Python (curl_cffi)

```python
import httpx
from curl_cffi import requests

# 调用者的配置（必须与后续请求一致）
PROXY = "http://proxy_user:proxy_pass@proxy_host:8080"
BROWSER = "chrome136"

# 1. 获取 CF 凭证
resp = httpx.post(
    "http://cf-service:20001/api/v1/credentials",
    json={
        "target_url": "https://target-site.com",
        "context": {
            "proxy": PROXY,
            "browser": BROWSER
        }
    },
    headers={"X-API-Key": "your_api_key"}
)
credentials = resp.json()

# 2. 使用凭证请求目标站点（使用相同的代理和 TLS 指纹）
session = requests.Session()
session.proxies = {"http": PROXY, "https": PROXY}

response = session.get(
    "https://target-site.com/api",
    impersonate=BROWSER,  # 必须与获取凭证时的 browser 一致
    headers={
        "User-Agent": credentials["user_agent"],
        "Cookie": credentials["cookie_string"]
    }
)
```

## 关键注意事项

1. **三要素一致**：proxy、browser 必须与后续请求完全一致
2. **browser 参数**：对应 curl_cffi 的 `impersonate` 参数，决定 TLS 指纹
3. **代理认证**：支持 `http://user:pass@host:port` 格式
4. **凭证时效**：cf_clearance 通常有效期 30 分钟

## License

MIT
