#!/bin/bash
MODULE=${1:-app}
PORT=${2:-8000}
exec uvicorn "$MODULE:app" --host 0.0.0.0 --port "$PORT"