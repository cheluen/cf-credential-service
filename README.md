# CF Credential Service

Cloudflare 凭证解析服务 - 使用 DrissionPage 自动通过 CF 人机验证获取凭证。

## 功能特性

- 自动通过 Cloudflare JS Challenge 和 Turnstile 验证
- 支持代理（HTTP/HTTPS/SOCKS5），包括带认证的代理
- 上下文伪装统一（UA、Browser/TLS 指纹、Headers 等）
- Basic Auth 认证保护 API
- REST API 接口，易于集成
- Docker 一键部署
- 支持 amd64/arm64 多架构

## 快速开始

### Docker 部署（推荐）

```bash
# 使用 GitHub Container Registry
docker run -d \
  -p 8080:8080 \
  -e CF_SERVICE_PASSWORD=your_password \
  ghcr.io/cheluen/cf-credential-service:latest

# 或构建本地镜像
docker build -t cf-credential-service .
docker run -d -p 8080:8080 -e CF_SERVICE_PASSWORD=your_password cf-credential-service
```

### 本地运行

```bash
pip install -r requirements.txt
python main.py
```

## 配置

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CF_SERVICE_PORT` | 服务端口 | 8080 |
| `CF_SERVICE_HOST` | 监听地址 | 0.0.0.0 |
| `CF_SERVICE_PASSWORD` | API 认证密码（用户名任意） | - |
| `CF_BROWSER_PATH` | Chrome/Chromium 路径 | 自动检测 |
| `CF_HEADLESS` | 无头模式 | true |
| `CF_CHROME_VERSION` | Chrome 版本 | chrome136 |
| `CF_DEFAULT_PROXY` | 默认代理 | - |
| `CF_DEFAULT_USER_AGENT` | 默认 User-Agent | - |
| `CF_DEFAULT_TIMEOUT` | 默认超时时间 | 90 |

> **认证说明**：Basic Auth 只验证密码，用户名可以是任意值。例如：`api:password` 或 `admin:password` 都可以通过认证。

### 配置文件

复制 `config.example.toml` 为 `config.toml`：

```toml
port = 8080
host = "0.0.0.0"
password = "your_password"
headless = true
chrome_version = "chrome136"
default_timeout = 90
```

## API 接口

### 获取凭证

```http
POST /api/v1/credentials
Content-Type: application/json
Authorization: Basic base64(user:password)

{
  "target_url": "https://example.com",
  "context": {
    "proxy": "http://user:pass@proxy:8080",
    "user_agent": "Mozilla/5.0 ...",
    "browser": "chrome136",
    "timeout": 60
  }
}
```

响应：

```json
{
  "success": true,
  "cf_clearance": "abc123...",
  "cookies": {"cf_clearance": "abc123...", ...},
  "cookie_string": "cf_clearance=abc123...; ...",
  "user_agent": "Mozilla/5.0 ...",
  "browser": "chrome136",
  "expires_at": 1708089600.0,
  "challenge_type": "js_challenge"
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

# 1. 获取 CF 凭证
resp = httpx.post(
    "http://cf-service:8080/api/v1/credentials",
    json={
        "target_url": "https://target-site.com",
        "context": {
            "proxy": "http://user:pass@proxy:8080",
            "browser": "chrome136"
        }
    },
    auth=("api", "your_password")
)
credentials = resp.json()

# 2. 使用凭证请求目标站点（必须使用相同代理）
session = requests.Session()
session.proxies = {"http": "http://user:pass@proxy:8080", "https": "http://user:pass@proxy:8080"}

response = session.get(
    "https://target-site.com/api",
    impersonate="chrome136",  # TLS 指纹匹配
    headers={
        "User-Agent": credentials["user_agent"],
        "Cookie": credentials["cookie_string"]
    }
)
```

## 关键注意事项

1. **IP 一致性**：获取凭证和后续请求必须使用相同的代理（同一出口 IP）
2. **UA 一致性**：User-Agent 需要与后续请求保持一致
3. **TLS 指纹**：建议使用 `curl_cffi` 的 `impersonate="chrome136"` 参数匹配 TLS 指纹
4. **Browser 参数**：`browser` 参数（chrome134/135/136/137）会自动设置对应的 UA
5. **凭证时效**：cf_clearance 通常有效期 30 分钟，过期后需重新获取

## 部署到云平台

### Hugging Face Spaces

```Dockerfile
FROM ghcr.io/cheluen/cf-credential-service:latest
ENV DATA_DIR=/data
EXPOSE 7860
```

### Render / Railway

直接连接 GitHub 仓库，选择 Docker 构建即可。

## License

MIT
