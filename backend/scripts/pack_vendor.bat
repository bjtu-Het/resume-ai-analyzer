@echo off
REM 打出 Linux(x86_64)+Python3.10 可用的依赖，供上传阿里云 FC（不要用本机 Windows 包）
cd /d %~dp0\..
if exist vendor rmdir /s /q vendor
python -m pip install -r requirements.txt -t vendor ^
  --platform manylinux2014_x86_64 ^
  --implementation cp ^
  --python-version 310 ^
  --only-binary=:all: ^
  -i https://mirrors.aliyun.com/pypi/simple/ ^
  --trusted-host mirrors.aliyun.com
if errorlevel 1 (
  echo.
  echo 若失败：请改用 FC 启动命令 bash /code/bootstrap，让函数在 Linux 环境里自行 pip install
  exit /b 1
)
echo OK: Linux vendor ready. Upload backend to FC. Start command: bash /code/bootstrap
