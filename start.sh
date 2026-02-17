#!/bin/bash
# CF Credential Service 启动脚本
# 监听端口 20001，供 grok2api 通过 argo 隧道调用

cd "$(dirname "$0")"

export PORT=20001

echo "Starting CF Credential Service on port $PORT..."
echo "This service will be accessible via: https://cf.cheluen.ggff.net"

python3 main.py
