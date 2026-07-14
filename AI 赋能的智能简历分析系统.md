### AI 赋能的智能简历分析系统

#### 背景

在招聘流程中，快速筛选和分析大量简历是一项耗时的工作。你的任务是构建一个后端服务，能够自动解析上传的简历（PDF 格式），提取关键信息，并利用 AI 模型对简历进行评分和关键词匹配，帮助招聘者快速筛选候选人。

#### 技术要求

- **运行环境**：阿里云 Serverless（如函数计算 FC）
- **开发语言**：Python
- **API 规范**：RESTful
- **完成时限**：收到题目后 **24 小时内** 提交

------

### 功能模块

#### 模块一：简历上传与解析 `必选`

- 提供接口，支持上传 **单个 PDF 格式** 的简历文件
- 解析 PDF 内容，提取文本信息（需兼容多页简历）
- 对提取文本进行清洗和结构化处理（去除冗余字符、合理分段等）

#### 模块二：关键信息提取 `必选`

利用 AI 模型从简历文本中提取以下关键信息：

| 类别         | 字段                         | 是否必须 |
| ------------ | ---------------------------- | -------- |
| **基本信息** | 姓名、电话、邮箱、地址       | ✅ 必选   |
| **求职信息** | 求职意向、期望薪资           | ⭐ 加分项 |
| **背景信息** | 工作年限、学历背景、项目经历 | ⭐ 加分项 |

#### 模块三：简历评分与匹配 `必选`

- 提供接口，接收招聘岗位的需求描述（文本）
- 对岗位需求进行关键词提取和分析
- 将解析后的简历信息与岗位需求进行匹配，计算匹配度评分（技能匹配率、工作经验相关性等）
- **加分项**：利用 AI 模型对匹配度进行更精准的评分

#### 模块四：结果返回与缓存 `必选`

- 以 **JSON 格式** 结构化返回解析结果、关键信息和匹配度评分
- **加分项**：实现缓存机制（如 Redis），对已解析和评分的简历进行缓存，避免重复计算

#### 模块五：前端页面 `必选`

- 使用任意前端技术栈完成一个简洁可用的交互页面
- 允许借助 AI 工具辅助完成前端开发
- **必须部署** 至 GitHub Pages 或其他可公开访问的云服务，供评审团队线上验收

------
------

### 提交方式

1. 在 **GitHub** 上创建公开仓库
2. 仓库中须包含完整的 `README.md`，说明项目架构、技术选型、部署方式及使用说明
3. 前端页面须部署至 **GitHub Pages** 或其他可公开访问的平台
4. 将以下信息发送至Boss直聘的面试官：

- GitHub 仓库地址
- 线上演示地址
- 你的姓名与联系方式

------
------

## 工程实现计划（逐步落地）

> **目标**：在 24h 内交付可线上验收的最小完备系统（后端 FC + 前端 Pages），必选全覆盖，加分项尽量做满。  
> **原则**：先跑通主链路，再补缓存/加分提取；接口契约先行，前后端可并行。

### 0. 范围与验收标准

| 验收项 | 标准 |
| ------ | ---- |
| PDF 上传解析 | 单文件 PDF、多页可读；清洗后结构化文本可返回 |
| 关键信息提取 | 姓名/电话/邮箱/地址必有；意向/薪资/年限/学历/项目尽量有 |
| 岗位匹配评分 | 输入 JD 文本 → 关键词 + 匹配分（技能/经验等维度）+ AI 综合分 |
| 结果 JSON | 固定 schema，字段稳定，错误有明确 `code/message` |
| 缓存（加分） | 同简历哈希 + 同 JD 哈希可命中，避免重复 LLM/解析 |
| 前端部署 | GitHub Pages 可打开，能上传简历、填 JD、展示结果 |
| 文档 | README 含架构、选型、部署、调用说明 |

### 1. 技术选型（建议定稿）

| 层级 | 选型 | 理由 |
| ---- | ---- | ---- |
| 运行时 | 阿里云函数计算 FC3 + HTTP 触发器（或 FC + API 网关） | 符合题面 Serverless |
| 语言 | **Python 3.10** | 题面要求 + 本项目定稿 |
| Web 框架 | FastAPI + Mangum | REST 清晰，适合 FC 适配 ASGI |
| PDF | `pdfplumber`（主）+ `pypdf`（兜底） | 多页文本提取稳 |
| LLM | **通义千问 qwen-plus**（DashScope OpenAI 兼容接口） | 关键信息提取 + 智能打分 |
| 缓存 | **Docker Redis**（服务器自建；不可用时进程内 LRU 降级） | 加分项；见根目录 `docker-compose.yml` |
| 对象存储 | OSS（可选） | 存原始 PDF；无 OSS 则内容哈希去重 |
| 前端 | **Vite + Vue 3** | 题面前端定稿 |
| 前端托管 | GitHub Pages | 题面强制可公开访问 |
| 工程 | 单仓 monorepo：`backend/` + `frontend/` | 评审一眼看清 |

**降级策略（必须写进设计）**

- LLM 不可用 → 规则提取（正则：邮箱/手机/姓名启发式）+ 关键词 overlap 打分，保证接口不挂。
- Redis 不可用 → 进程内 LRU（容量有限，文档声明）。
- PDF 空文本（扫描件）→ 返回明确错误码 `PDF_TEXT_EMPTY`，提示暂不支持纯图片 OCR（OCR 作为时间允许的加分）。

### 2. 系统架构

```
[浏览器 GitHub Pages]
        │ HTTPS
        ▼
[阿里云 FC HTTP API]
   ┌────┴────┐
   │ API 层  │  CORS / 校验 / 统一响应
   └────┬────┘
        │
   ┌────┼──────────────┬─────────────┐
   ▼    ▼              ▼             ▼
 解析  提取(LLM/规则)  匹配打分     缓存(Redis)
   │         │           │             ▲
   └─────────┴───────────┴─────────────┘
                 │
                 ▼
            统一 JSON Schema
```

**核心数据流**

1. 上传 PDF → 算 `file_hash` → 查缓存「解析+提取」→ 未命中则解析→清洗→LLM 提取→写缓存。  
2. 提交 JD（或与上传同请求）→ 算 `jd_hash` → 查缓存「匹配分」→ 未命中则抽 JD 关键词→简历-JD 匹配→AI 复评→写缓存。  
3. 合并返回：`parsed` + `profile` + `match` + `meta(cache_hit)`。

### 3. API 契约（REST）

统一响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": { },
  "meta": { "request_id": "...", "cache_hit": false }
}
```

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| `GET` | `/health` | 健康检查 |
| `POST` | `/api/v1/resumes/parse` | `multipart/form-data`：`file`；返回解析文本 + 关键信息 |
| `POST` | `/api/v1/resumes/analyze` | `file` + `job_description`（或 `resume_id` + JD）；一站式解析+提取+匹配 |
| `POST` | `/api/v1/match` | JSON：`resume_text` 或 `profile` + `job_description`；仅打分 |
| `GET` | `/api/v1/resumes/{resume_id}` | 按 ID/哈希取缓存结果（若实现存储） |

**建议 `data` Schema（analyze）**

```json
{
  "resume_id": "sha256...",
  "raw_text": "...",
  "cleaned_text": "...",
  "profile": {
    "name": "",
    "phone": "",
    "email": "",
    "address": "",
    "job_intention": "",
    "expected_salary": "",
    "work_years": null,
    "education": [],
    "projects": [],
    "skills": []
  },
  "job": {
    "keywords": [],
    "summary": ""
  },
  "match": {
    "score": 0,
    "skill_match_rate": 0,
    "experience_relevance": 0,
    "ai_score": null,
    "reasons": [],
    "missing_keywords": []
  }
}
```

### 4. 模块实现要点

#### 模块一：上传与解析

- 限制：仅 `.pdf`、大小上限（如 5MB）、Content-Type 校验。
- 多页：按页抽取文本拼接，页间 `\n\n`。
- 清洗：去多余空白、控制字符、页眉页脚重复行；按空行分段；可选保留「教育/工作/项目」等标题锚点。
- 输出：`raw_text` / `cleaned_text` / `page_count`。

#### 模块二：关键信息提取

- Prompt：严格 JSON Schema 输出；字段缺失填 `null`/`""`。
- 后处理：手机/邮箱正则校验与纠错；姓名长度与中文/英文规则。
- Fallback：规则引擎补齐基本四字段。
- 加分字段：意向、薪资、年限、学历列表、项目列表（title/role/desc/tech）。

#### 模块三：评分与匹配

- JD 关键词：LLM 抽 skills/年限/学历/加分项；规则侧用分词/字典并集。
- 规则分：技能命中率、年限区间、学历关键字、项目关键词相关度 → 加权合成。
- AI 分（加分）：把 `profile + JD` 喂给模型，输出 0–100 与短理由；最终分 = `α*规则 + β*AI`（可配置，默认 0.4/0.6）。
- 返回缺词列表与 reasons，方便前端展示。

#### 模块四：结果与缓存

- Key：`resume:{file_hash}`、`match:{file_hash}:{jd_hash}`。
- TTL：解析 24h、匹配 6h（可配）。
- 缓存内容含 schema 版本号，升级时 bump 避免脏读。

#### 模块五：前端

- 页面：上传区、JD 文本框、分析按钮、结果区（基本信息卡片、匹配分环形/进度、关键词标签、原因列表）。
- CORS：后端允许 Pages 域名；开发态允许 localhost。
- 配置：`VITE_API_BASE_URL` 指向 FC HTTP 地址。
- 部署：`gh-pages` 或 Actions 发布 `frontend/dist`。

### 5. 仓库目录结构（落地时创建）

```
resume-ai-analyzer/
├── README.md
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── api/routes.py
│   │   ├── services/
│   │   │   ├── pdf_parser.py
│   │   │   ├── text_cleaner.py
│   │   │   ├── extractor.py     # LLM + 规则
│   │   │   ├── matcher.py
│   │   │   └── cache.py
│   │   ├── schemas/
│   │   ├── prompts/
│   │   └── config.py
│   ├── requirements.txt
│   ├── s.yaml / template.yml    # FC 部署（Serverless Devs）
│   └── Dockerfile               # 若用自定义运行时
├── frontend/
│   ├── package.json
│   ├── src/
│   └── ...
└── docs/
    └── api.md                   # 可选；核心也可写在 README
```

### 6. 分步实施顺序（按此逐步编码）

| 步骤 | 内容 | 产出 | 预计 |
| ---- | ---- | ---- | ---- |
| **P0** | 本计划定稿 + 建仓骨架 + README 骨架 | 目录/依赖/空路由 | 0.5h |
| **P1** | PDF 解析 + 清洗 + `/parse` | 本地可测 PDF→文本 | 2h |
| **P2** | 规则提取 + LLM 提取 + Schema | `/parse` 返回 profile | 3h |
| **P3** | JD 关键词 + 规则匹配 + AI 评分 | `/analyze`、`/match` | 3h |
| **P4** | Redis 缓存 + 降级内存 | cache_hit 可观测 | 1.5h |
| **P5** | 适配 FC 部署（环境变量、体积、CORS） | 公网 API URL | 2h |
| **P6** | 前端页面 + 联调 | 本地闭环 | 2h |
| **P7** | GitHub Pages 部署 + README 完善 + 样例 PDF | 评审材料齐 | 1.5h |
| **缓冲** | 扫描件/异常 case/Prompt 调优 | 稳定性 | 余量 |

### 7. 配置与安全（提交前检查）

- 密钥全部环境变量：`LLM_API_KEY`、`REDIS_URL`、`ALLOWED_ORIGINS` 等；**绝不提交密钥**。
- 上传病毒扫描可省略；做大小/类型白名单即可。
- 日志打 `request_id`，不落全文敏感信息到公开仓库。
- README 明确：如何申请模型 Key、如何填 Secrets、如何一键部署 FC。

### 8. 测试清单

- [ ] 1 页 / 多页中文简历 PDF
- [ ] 英文简历字段提取
- [ ] 无邮箱/无电话的残缺简历（应优雅降级）
- [ ] 超大文件 / 非 PDF（4xx）
- [ ] 同文件二次请求 `cache_hit=true`
- [ ] JD 空文本 / 极短 JD
- [ ] 前端跨域联调成功
- [ ] 线上 Pages → 线上 FC 主链路可用

### 9. 当前进度与下一步

- [x] **第一步：工程实现计划**（本节）
- [x] **第二步：初始化前后端骨架**（已定稿：Python3.10 / qwen-plus / Vue3 / Docker Redis）
  - 后端：`backend/` FastAPI 可启动，含配置、Schema、路由占位、QwenClient、Redis 缓存降级、deps 懒加载
  - 前端：`frontend/` Vue3 + Vite，UploadForm / ResultPanel / API 封装，`npm run build` 已通过
  - Redis：项目根目录 `docker-compose.yml` 自建，不再使用阿里云 Redis
- [x] 第三步：实现 PDF 解析与清洗（`pdf_parser` + `text_cleaner`）
- [x] 第四步：实现关键信息提取（规则 + qwen-plus，失败降级）并接入 **`POST /api/v1/resumes/parse`**
- [x] 第五步：实现匹配评分（规则分 + qwen-plus；**`/analyze`**、**`/match`** 已接通）
- [ ] 第六步：完善 FC / 服务器部署配置
- [ ] 第七步：完善前端展示与 GitHub Pages
- [ ] 第八步：联调、样例与提交材料整理

---

**执行约定**：缓存已改为 **Docker Redis**。本地先 `docker compose up -d`，再启动后端。