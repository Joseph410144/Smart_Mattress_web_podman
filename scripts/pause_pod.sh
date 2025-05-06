#!/bin/bash
echo "🛑 暫停 Podman 前後端容器..."
podman container stop frontend-frontend || echo "frontend container not running or timeout"
podman container stop backend-backend || echo "backend container not running or timeout"
echo "✅ 已暫停"