# 可选：自定义镜像部署到 FC（依赖装进镜像，冷启动更快）
FROM python:3.10-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com

COPY app ./app
COPY bootstrap .

ENV PYTHONPATH=/code
ENV FC_SERVER_PORT=9000

EXPOSE 9000
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
