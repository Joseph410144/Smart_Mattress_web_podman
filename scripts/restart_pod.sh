#!/bin/bash
echo "▶️ 恢復 Podman 前後端容器..."
podman container start frontend-frontend || echo "frontend container not running or timeout"
podman container start backend-pair-backend-ingest || echo "backend container not running or timeout"
podman container start backend-pair-backend-download || echo "backend container not running or timeout"
echo "✅ 已恢復"