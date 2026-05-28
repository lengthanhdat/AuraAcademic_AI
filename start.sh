#!/bin/bash
# ─── Script khởi chạy LiteLLM Proxy ───────────────────────────────────────────
# Usage:
#   1. Cài đặt (lần đầu): pip install litellm
#   2. Sao chép .env.example thành .env và điền API Keys của bạn vào
#   3. Chạy: bash start.sh

# Nạp biến môi trường từ .env
set -a
source .env
set +a

echo "🚀 Khởi động LiteLLM Proxy..."
echo "📡 Proxy sẽ chạy tại: http://localhost:4000"
echo "🔑 Master Key: $LITELLM_MASTER_KEY"
echo ""

litellm --config litellm_config.yaml --port 4000
