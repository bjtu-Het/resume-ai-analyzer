#!/usr/bin/env bash
# 在 Linux 上执行最稳；或用 Docker 打 manylinux 包
set -e
cd "$(dirname "$0")/.."
rm -rf vendor
python3 -m pip install -r requirements.txt -t vendor \
  -i https://mirrors.aliyun.com/pypi/simple/ \
  --trusted-host mirrors.aliyun.com
echo "OK: vendor ready. FC start command: bash /code/bootstrap"
