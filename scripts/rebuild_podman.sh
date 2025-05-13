#!/bin/bash
# chmod +x rebuild_podman.sh
# ./rebuild_podman.sh

echo "🛑 停止舊的 pod..."
podman pod stop frontend backend 2>/dev/null || true
podman pod rm frontend backend 2>/dev/null || true

echo "🔨 建置 frontend image..."
cd /home/joseph/Smart_Mattress_web_podman/frontend
podman build -t localhost/frontend:latest .

echo "🔨 建置 backend image..."
cd ../backend
podman build -t localhost/backend:latest .

echo "🚀 啟動 pods..."
cd ../deploy
podman play kube frontend.yaml
podman play kube backend.yaml

echo "✅ 所有服務已重新啟動完成"