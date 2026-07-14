#!/usr/bin/env bash
# 本地启动后端（请先 conda activate 你的 Python 3.10 环境并安装 requirements.txt）
cd "$(dirname "$0")"
export PYTHONPATH=.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
