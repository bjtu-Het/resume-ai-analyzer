# AI 赋能的智能简历分析系统

上传 PDF 简历，自动解析文本、提取关键信息，并对照岗位 JD 计算匹配评分。

| 层级 | 技术选型 |
|------|----------|
| 后端 | Python 3.10 · FastAPI · 阿里云函数计算 FC（或自建服务器） |
| 大模型 | 通义千问 **qwen-plus**（DashScope OpenAI 兼容接口） |
| 缓存 | **Docker Redis**（服务器自建；连不上自动降级进程内 LRU） |
| 前端 | Vue 3 · Vite · 可部署 GitHub Pages |

---

## 目录结构

```
docker-compose.yml       # ★ 服务器 Docker 启动 Redis
backend/                 # FastAPI 后端
  .env.example           # 环境变量模板（复制为 .env 后填写）
  .env                   # ★ 本地密钥文件（勿提交 Git）
  app/
    main.py              # 入口 + CORS + /health
    config.py            # 读取 .env
    api/routes.py        # REST 接口
    services/            # PDF / 提取 / 匹配 / Redis / 千问
    prompts/             # 千问 Prompt
frontend/                # Vue3 前端
  .env.example           # 前端环境变量模板
  src/api/resume.js      # 调用后端 API
```

---

## 一、密钥与配置写在哪里？

### 1. 后端（必填项都在这里）

**路径：`backend/.env`**

1. 复制模板：

```bash
cd backend
copy .env.example .env
```

2. 用编辑器打开 `backend/.env`，按下面填写：

```env
# ---------- 通义千问 API（必填，否则只用规则引擎）----------
# 获取：https://dashscope.console.aliyun.com/ → API-KEY 管理
QWEN_API_KEY=sk-你的真实密钥
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus

# ---------- Docker Redis（与根目录 docker-compose.yml 保持一致）----------
# 后端与 Redis 在同一台机器：用 127.0.0.1
# 后端在别的机器：填 Redis 所在服务器的内网/公网 IP
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=resumeai123
REDIS_DB=0
REDIS_SSL=false

# 缓存过期（秒）：解析结果 24h，匹配结果 6h
CACHE_TTL_PARSE=86400
CACHE_TTL_MATCH=21600

# ---------- 其他 ----------
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
MAX_UPLOAD_MB=5
```

| 配置项 | 写哪里 | 说明 |
|--------|--------|------|
| 千问 API Key | `backend/.env` → `QWEN_API_KEY` | **不要写进代码，不要提交 Git** |
| Redis 地址/密码 | `backend/.env` → `REDIS_*` | 对应 Docker Redis；密码需与 compose 一致 |
| 前端跨域白名单 | `backend/.env` → `ALLOWED_ORIGINS` | GitHub Pages 上线后把域名加进来 |

程序启动时由 `app/config.py` 自动加载 `backend/.env`。

### 2. 前端

**路径：`frontend/.env`（可选）**

```bash
cd frontend
copy .env.example .env
```

```env
# 留空 = 开发时走 Vite 代理到本机 8000
# 上线后改成你的后端公网地址，例如：
# VITE_API_BASE_URL=https://your-api.example.com
VITE_API_BASE_URL=
```

### 3. 安全提醒

- `.env` 已在 `.gitignore` 中，**禁止提交真实密钥**
- 仓库里只保留 `.env.example`（占位符，如 `sk-xxxxxxxx`）
- 部署时把同名变量配到服务器环境变量或 FC 控制台，不要把 Key 打进镜像  
- 若 `.env.example` 曾误填真实 Key，请到 DashScope **轮换/作废**该 Key

---

## 二、Docker Redis 怎么用？

本项目**不再使用阿里云 Redis**，改为在服务器（或本机）用 Docker 起一个 Redis。

### 1. 启动 Redis

服务器 / 本机需已安装 [Docker](https://docs.docker.com/get-docker/) 与 Docker Compose。

在项目根目录执行：

```bash
# 进入仓库根目录（含 docker-compose.yml）
docker compose up -d
```

查看状态：

```bash
docker ps
docker compose logs -f redis
```

默认配置：

| 项 | 值 |
|----|-----|
| 容器名 | `resume-ai-redis` |
| 端口 | `6379` |
| 密码 | `resumeai123`（可在 `docker-compose.yml` 与 `.env` 中同时修改） |
| 数据卷 | `resume_ai_redis_data`（重启不丢数据） |

停止：

```bash
docker compose down          # 停容器，保留数据卷
docker compose down -v       # 停容器并删除数据（慎用）
```

### 2. 改密码（可选）

1. 编辑根目录 `docker-compose.yml` 里 `--requirepass` 与 healthcheck 密码  
2. 同步改 `backend/.env` 的 `REDIS_PASSWORD`  
3. `docker compose up -d --force-recreate`

### 3. 后端如何连接

| 场景 | `REDIS_HOST` 怎么填 |
|------|---------------------|
| 后端与 Docker Redis **同一台机器** | `127.0.0.1` |
| 后端在另一台机器 | 填 Redis 服务器 IP（并放行防火墙 6379） |
| 以后后端也进同一 compose 网络 | 可改为服务名 `redis` |

写入 `backend/.env` 后**重启 uvicorn**，然后检查：

```bash
curl http://127.0.0.1:8000/health
```

`data.redis` 含义：

| 值 | 含义 |
|----|------|
| `redis` | 已连上 Docker Redis |
| `memory` | 连不上，已降级本机内存 LRU |
| `redis_error` | 曾连上但当前 ping 失败 |

本机快速测 Redis 是否通：

```bash
docker exec -it resume-ai-redis redis-cli -a resumeai123 ping
# 应返回 PONG
```

### 4. 缓存工作原理

```
请求 parse / analyze / match
        │
        ▼
  生成缓存 Key ──► Redis GET
        │              │
     命中 ◄────────────┘ 返回结果，meta.cache_hit=true
        │
     未命中
        ▼
  执行 PDF解析 / 千问提取 / 打分
        │
        ▼
  Redis SETEX（带 TTL）──► 返回结果，meta.cache_hit=false
```

| 场景 | Key 格式 | TTL 默认 |
|------|----------|----------|
| 简历解析结果 | `parse:v1:{文件SHA256}` | 86400 秒（24h） |
| 匹配评分结果 | `match:v1:{resume_id}:{JD的SHA256}` | 21600 秒（6h） |

响应示例：

```json
{
  "meta": {
    "request_id": "...",
    "cache_hit": true
  }
}
```

### 5. 不想用 Redis 时

不启动 Docker 或配置错误也可以跑：自动降级内存缓存，接口仍可用。

实现代码：`backend/app/services/cache.py`。

---

## 三、本地启动

### 0. 先起 Redis（推荐）

```bash
docker compose up -d
```

### 1. 后端（conda）

```bash
conda activate <你的环境名>          # Python 3.10 推荐
cd backend
pip install -r requirements.txt
copy .env.example .env             # 首次：填入 QWEN_API_KEY；Redis 默认连本机 Docker
# 编辑 .env 后再启动
set PYTHONPATH=.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- 接口文档：http://127.0.0.1:8000/docs  
- 健康检查：http://127.0.0.1:8000/health  

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5173 。开发态由 Vite 把 `/api`、`/health` 代理到 `8000`。

---

## 四、API 说明

统一响应格式：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "meta": { "request_id": "...", "cache_hit": false }
}
```

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查（含模型名、Redis 状态） |
| `POST` | `/api/v1/resumes/parse` | 上传 PDF → 解析 + 关键信息提取 |
| `POST` | `/api/v1/resumes/analyze` | 上传 PDF + JD → 解析 + 匹配评分（前端主用） |
| `POST` | `/api/v1/match` | 已有文本/画像 + JD → 只打分 |

### 调用示例

**parse**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/resumes/parse ^
  -F "file=@resume.pdf"
```

**analyze（推荐）**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/resumes/analyze ^
  -F "file=@resume.pdf" ^
  -F "job_description=招聘 Python 后端，要求 FastAPI / Redis，2 年经验"
```

**match**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/match ^
  -H "Content-Type: application/json" ^
  -d "{\"job_description\":\"招聘 Python 后端\",\"resume_text\":\"熟悉 Python FastAPI\",\"profile\":{\"skills\":[\"Python\",\"FastAPI\"],\"work_years\":3}}"
```

### 降级说明

- 未配置 / 无效 `QWEN_API_KEY`：规则引擎提取邮箱、手机等，并做关键词匹配打分  
- Redis 不可用：内存 LRU，接口仍可用  
- 扫描件 PDF 无文字：返回错误码（暂不支持 OCR）

---

## 五、冒烟脚本

```bash
cd backend
set PYTHONPATH=.
python tests/smoke_parse.py
python tests/smoke_match.py
```

---

## 六、提交与部署清单（题目要求）

- [ ] GitHub **公开仓库** + 完整 README（本文件）
- [ ] 后端部署至阿里云 FC **或自建服务器**；环境变量配置 `QWEN_API_KEY`、`REDIS_*`
- [ ] 服务器上执行 `docker compose up -d` 提供 Redis
- [ ] 前端构建：`cd frontend && npm run build`，产物 `dist/` 部署到 **GitHub Pages**
- [ ] Pages 上线后：把前端域名加入后端 `ALLOWED_ORIGINS`，并设置 `VITE_API_BASE_URL` 后重新构建前端
- [ ] 向面试官发送：仓库地址、演示地址、姓名与联系方式

---

## 七、常见问题

**Q：`/health` 里 `redis` 一直是 `memory`？**  
A：先确认 `docker compose ps` 中 Redis 在跑；`REDIS_PASSWORD` 与 compose 一致；本机用 `127.0.0.1`。再用 `docker exec -it resume-ai-redis redis-cli -a resumeai123 ping` 自测。

**Q：配了 Key 仍像没用上千问？**  
A：确认 `.env` 在 `backend/` 目录、`QWEN_API_KEY` 不是 `sk-xxxxxxxx` 占位符，改完后重启 uvicorn。

**Q：密钥可以写在代码里吗？**  
A：不可以。只写在 `backend/.env` 或云平台 / 服务器环境变量中。

**Q：6379 要不要对公网开放？**  
A：仅本机/内网访问时不必对公网开放。若必须远程连，请改强密码并限制防火墙来源 IP。
