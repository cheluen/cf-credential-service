# CF Credential Service

Cloudflare 凭证解析服务 - 使用 DrissionPage 自动通过 CF 人机验证获取凭证。

## 核心原理

CF 凭证（cf_clearance）与以下因素绑定：
1. **出口 IP** - 获取凭证时的代理出口 IP
2. **User-Agent** - 浏览器标识
3. **TLS 指纹** - 浏览器 SSL/TLS 握手特征

**调用者必须确保**：获取凭证时使用的 proxy、user_agent、browser 参数，与后续请求时完全一致，凭证才能生效。

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
  -p 8080:8080 \
  -e CF_SERVICE_API_KEY=your_api_key \
  ghcr.io/cheluen/cf-credential-service:latest
```

### 本地运行

```bash
pip install -r requirements.txt
CF_SERVICE_API_KEY=your_api_key python main.py
```

## 配置

### 环境变量

| 变量 | 说明 | ���认值 |
|------|------|--------|
| `CF_SERVICE_PORT` | 服务端口 | 8080 |
| `CF_SERVICE_HOST` | 监听地址 | 0.0.0.0 |
| `CF_SERVICE_API_KEY` | API Key（请求时通过 X-API-Key 头传递） | - |
| `CF_BROWSER_PATH` | Chrome/Chromium 路径 | 自动检测 |
| `CF_HEADLESS` | 无头模式 | true |

> **注意**：不要在服务端配置 proxy、user_agent、browser。这些参数必须由调用者传入，确保与调用者后续请求一致。

## API 接口

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

**context 参数说明：**

| 参数 | 必填 | 说明 |
|------|------|------|
| `proxy` | **是** | 代理地址，调用者后续请求必须使用相同代理 |
| `browser` | **是** | TLS 指纹版本：chrome134/135/136/137，调用者后续请求必须使用相同的 impersonate 参数 |
| `user_agent` | 否 | User-Agent，不传则根据 browser 自动设置 |
| `timeout` | 否 | 超时时间（秒），默认 90 |

**响应：**

```json
{
  "success": true,
  "cf_clearance": "abc123...",
  "cookies": {"cf_clearance": "abc123...", ...},
  "cookie_string": "cf_clearance=abc123...; ...",
  "user_agent": "Mozilla/5.0 ...",
  "browser": "chrome136",
  "expires_at": 1708089600.0
}
```

### 健康检查

```http
GET /health
```

## 使用示例

### Python (curl_cffi)

```python
import httpx
from curl_cffi import requests

# 调用者的配置
PROXY = "http://proxy_user:proxy_pass@proxy_host:8080"
BROWSER = "chrome136"

# 1. 获取 CF 凭证
resp = httpx.post(
    "http://cf-service:8080/api/v1/credentials",
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

1. **三要素一致**：proxy、browser、user_agent 必须与后续请求完全一致
2. **browser 参数**：对应 curl_cffi 的 `impersonate` 参数，决定 TLS 指纹
3. **代理认证**：支持 `http://user:pass@host:port` 格式的代理
4. **凭证时效**：cf_clearance 通常有效期 30 分钟

## 部署

### Hugging Face Spaces

```Dockerfile
FROM ghcr.io/cheluen/cf-credential-service:latest
ENV CF_SERVICE_API_KEY=your_api_key
EXPOSE 7860
```

### Render / Railway

直接连接 GitHub 仓库，选择 Docker 构建，设置环境变量 `CF_SERVICE_API_KEY`。

## License

MIT
