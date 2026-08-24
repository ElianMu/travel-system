# 景文智核 · 技术设计文档（TDD）

| 文档编号 | JWZH-TDD-001 |
|---------|--------------|
| 项目名称 | 景文智核 · 智能旅游知识库系统 |
| 文档版本 | v1.0 |
| 文档状态 | 正式发布 |
| 密级 | 内部公开 |

## 1. 修订历史

| 版本 | 修订日期 | 修订人 | 修订说明 |
|------|----------|--------|----------|
| v1.0 | 2026-08-24 | 技术研发组 | 首次发布，覆盖架构、技术选型、模块设计、接口、数据模型、ADR 与部署方案 |

## 2. 架构总览

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                前端 Web 层（Vue 3 + Element Plus）            │
│  问答 / 景点检索 / 线路检索 / 实用信息 / 内容导入 / 元数据管理   │
└─────────────────────────────────────────────────────────────┘
                              │ HTTP / SSE 依赖向下
┌─────────────────────────────────────────────────────────────┐
│                      接入层（API Layer）                      │
│   FastAPI Routers：/import  /search  /chat  /sessions        │
│   统一鉴权、参数校验、异常翻译、SSE 流式封装                    │
└─────────────────────────────────────────────────────────────┘
                              │ 依赖向下
┌─────────────────────────────────────────────────────────────┐
│                    应用服务层（Service Layer）                 │
│  ImportService │ SearchService │ ChatService │ SessionService │
└─────────────────────────────────────────────────────────────┘
                              │ 依赖向下
┌─────────────────────────────────────────────────────────────┐
│                领域/RAG 编排层（RAG Pipeline）                │
│  Loader → MetadataNormalizer → Splitter → Embedder →         │
│  VectorStore → Retriever →（Tavily 兜底）→ Generator        │
└─────────────────────────────────────────────────────────────┘
                              │ 依赖向下
┌─────────────────────────────────────────────────────────────┐
│                  基础设施层（Infrastructure）                 │
│  Chroma 向量库 │ MySQL │ 文件存储 │ LLM/Embedding/联网搜索客户端 │
└─────────────────────────────────────────────────────────────┘
       横切关注点：日志 / 链路追踪 / 指标 / 配置 / 异常处理 / 鉴权
```

### 2.2 依赖方向

依赖严格自上而下：接入层 → 应用服务层 → RAG 编排层 → 基础设施层。领域层不反向依赖接入层；基础设施层通过接口抽象（Port/Adapter）供上层调用，保证可替换（如 Chroma 替换为 Milvus、本机 MySQL 替换为云托管 RDS）。

## 3. 技术选型

| 领域 | 技术 | 版本 | 选型理由 |
|------|------|------|----------|
| 语言 | Python | 3.11 | 生态成熟，RAG/ML 库丰富 |
| Web 框架 | FastAPI | 0.115.x | 原生 async、OpenAPI 自动生成、SSE 友好 |
| ASGI 服务 | uvicorn | 0.32.x | 高性能 ASGI 服务 |
| RAG 编排 | LangChain + langchain-community | 0.3.x | 文档加载/切分/检索器抽象成熟 |
| LLM 接入 | langchain-openai（兼容协议） | 0.3.x | DeepSeek（deepseek-chat），OpenAI 兼容可平滑切换 |
| 向量库 | ChromaDB（chromadb） | 1.5.x | 本地持久化，生产可升级 Milvus |
| Embedding | BAAI/bge-base-zh-v1.5 | - | 中文效果佳、768 维、本地部署数据安全 |
| 联网搜索 | Tavily | - | 知识库无结果时联网兜底 |
| ORM | SQLAlchemy | 2.0.x | 屏蔽关系库差异，便于替换 |
| 数据校验 | Pydantic | 2.x | 请求/配置模型校验 |
| 流式 | sse-starlette | 2.x | SSE 事件流封装 |
| 数据库 | MySQL | 8.0 | 本机 MySQL，ORM 抽象可替换 |
| 可观测 | OpenTelemetry + Prometheus | - | 链路追踪与指标 |
| 前端框架 | Vue 3（Composition API） | 3.x | 组合式 API + <script setup>，生态成熟 |
| UI 组件库 | Element Plus | 2.x | 企业级中后台组件，与 Vue 3 配套 |
| 构建工具 | Vite | 5.x | 秒级冷启动，HMR 快，适合本机开发 |
| 路由 | Vue Router | 4.x | SPA 路由 |
| 状态管理 | Pinia | 2.x | 轻量状态管理，管理会话与消息 |
| HTTP 客户端 | Axios | 1.x | 拦截器统一鉴权/错误；流式用 fetch+ReadableStream |
| 运行 | 本机 Python 3.11 + uvicorn | - | 本机裸跑，无外部服务依赖 |

## 4. 目录结构

```
景文智核/
├── app/
│   ├── main.py                 # 应用入口，装配路由与中间件
│   ├── config.py               # 配置加载（pydantic-settings，分环境）
│   ├── api/                    # 接入层
│   │   ├── deps.py             # 依赖注入、鉴权
│   │   └── routes/
│   │       ├── import_.py      # 导入接口
│   │       ├── search.py       # 检索接口
│   │       ├── chat.py         # 问答/流式接口
│   │       └── session.py      # 会话历史接口
│   ├── services/               # 应用服务层
│   │   ├── import_service.py
│   │   ├── search_service.py
│   │   ├── chat_service.py
│   │   └── session_service.py
│   ├── rag/                    # RAG 编排层
│   │   ├── loader.py           # 文档加载
│   │   ├── normalizer.py       # 元数据规范化
│   │   ├── splitter.py         # 结构化切分
│   │   ├── embedder.py         # 向量化
│   │   ├── store.py            # 向量库写入/检索
│   │   ├── retriever.py        # 向量检索 + 联网兜底
│   │   ├── web_search.py      # Tavily 联网搜索
│   │   ├── generator.py        # LLM 生成 + 引用
│   │   └── prompts.py          # 提示词模板
│   ├── models/                 # ORM 模型
│   ├── schemas/                # Pydantic 请求/响应模型
│   └── core/                   # 横切：日志、异常、安全
├── data/                       # 来源文档
├── knowledge_base/             # 本地知识库文档目录
├── models/                     # 本地 Embedding 模型（bge-base-zh-v1.5）
├── storage/                    # 向量库持久化目录（ChromaDB）
├── tests/                      # 测试与评估集
├── pyproject.toml
├── .env.example
├── scripts/
│   └── import_all.py           # 批量导入脚本
└── frontend/                   # 前端（Vue 3 + Element Plus）
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.js
        ├── App.vue
        ├── router/index.js     # 路由
        ├── api/                # Axios 封装 + 接口调用
        ├── store/              # Pinia 状态
        ├── views/              # 页面
        │   ├── ChatView.vue          # 智能问答页
        │   ├── AttractionSearch.vue  # 景点检索页
        │   ├── RouteSearch.vue       # 线路检索页
        │   ├── InfoSearch.vue        # 实用信息页
        │   ├── ImportView.vue        # 内容导入页
        │   └── DocumentView.vue      # 元数据管理页
        └── components/         # 复用组件（消息气泡、引用列表、结果卡片等）
```

## 5. 模块设计

### 5.1 loader（文档加载）

- 职责：读取 Markdown 文档，解析一级标题（文档标题）、「## 元数据」区块与正文标题层级。
- 输入：文件路径或文件内容。
- 输出：`Document(title, metadata_raw, body)` 结构，`body` 保留 H2/H3 层级信息。

### 5.2 normalizer（元数据规范化）

- 职责：将来源元数据变体字段统一映射为规范 schema（对应 BR-002）。
- 映射表：

| 来源字段 | 规范字段 |
|----------|----------|
| 内容类型 | content_type |
| 城市 / 目的地 | region |
| 景点名称 / 线路名称 / 住宿名称 / 文档名称 | name |
| 主题 | theme |
| 来源文件名 | source_file |
| 来源路径 | source_path |

- 输出：`NormalizedMetadata` 对象，并写入文档元数据表。

### 5.3 splitter（结构化切分）

- 职责：按 H2/H3 标题边界切分正文，而非固定长度，保证片段语义完整（对应 FR-IMP-003）。
- 策略：以 H2 为一级分块边界，块过大时按 H3 细分；记录片段所属标题路径 `heading_path`。
- 输出：`List[Chunk]`，每个 Chunk 携带 `content`、`heading_path`、`document_id`、元数据。

### 5.4 embedder（向量化）

- 职责：调用 bge-base-zh-v1.5 对片段文本生成 768 维向量。
- 接口：`embed(texts: list[str]) -> list[list[float]]`。
- 特性：批量处理、失败重试、本地模型缓存加载。

### 5.5 store（向量库）

- 职责：Chroma Collection 的写入、删除、按文档清理、检索。
- Collection：`travel_kb`，metadata 含 `document_id`、`content_type`、`region`、`name`、`heading_path`、`source_file`。
- 支持按元数据过滤（如 `content_type == '景点介绍'`）。

### 5.6 retriever（向量检索 + 元数据过滤 + 联网兜底）

- 职责：向量语义检索，支持 `content_type` / `region` 元数据过滤，实现精确检索优先（对应 BR-005）。
- 流程：`query → 向量召回 Top-K → 元数据过滤 →（召回不足时）联网搜索兜底`。
- 本地无命中或相关度不足时，转 Tavily 联网搜索补充，保障答案可获取性。

### 5.7 generator（LLM 生成 + 引用）

- 职责：以检索片段为上下文，调用 LLM 生成答案，并强制附带引用来源。
- 输出：`Answer(text, citations)`，citations 含 `source_file`、`heading_path`、`chunk_id`、原文摘要。

### 5.8 应用服务层

| 服务 | 职责 |
|------|------|
| ImportService | 编排导入全流程，维护导入任务状态与失败隔离 |
| SearchService | 编排景点/线路/实用信息检索，返回结构化字段 |
| ChatService | 编排问答、多轮上下文、流式与降级 |
| SessionService | 会话与历史记录管理 |

## 6. 核心流程

### 6.1 内容导入流程（时序）

```
运营 → API → ImportService → Loader → Normalizer → Splitter → Embedder → Store → 任务状态更新
  1. 上传文档，创建 ImportTask(status=created)
  2. Loader 解析文档
  3. Normalizer 抽取并规范化元数据，写入 documents 表
  4. Splitter 结构化切分
  5. Embedder 批量向量化
  6. Store 写入 Chroma（含 metadata）
  7. 更新任务 status=success / 记录错误
异常：任一步失败 → status=failed + error_message，不影响其他任务（BR-004）
```

### 6.2 问答流程（时序）

```
游客 → API → ChatService → Retriever →（召回不足→联网搜索）→ Generator → 回答+引用
  1. 接收 query（多轮时先做查询改写，融合历史）
  2. Retriever 向量检索召回 Top-K 片段
  3. 本地召回不足时，转 Tavily 联网搜索补充
  4. Generator 组装提示词，调用 LLM 生成
  5. 返回答案 + citations
流式：SSE 通道逐 Token 返回，失败退化为非流式（BR-006）
```

## 7. 完整提示词

### 7.1 知识问答系统提示词

```
你是一名专业的旅游知识助手，回答必须严格基于下方提供的参考资料。
回答要求：
1. 只使用参考资料中的信息作答，不得编造资料中不存在的内容。
2. 如果资料无法回答，明确说明"根据现有知识库无法回答"。
3. 回答结尾列出引用来源，格式为：[来源文件名]（片段标题）。
4. 语言简洁、结构化，涉及景点/线路/价格等关键信息时优先给出明确结论。

参考资料：
{context}

问题：{question}
```

### 7.2 多轮查询改写提示词

```
结合对话历史，将用户当前问题改写为独立、语义完整的检索查询。
只输出改写后的查询，不要解释。

对话历史：
{history}

当前问题：{question}
```

### 7.3 元数据抽取（LLM 兜底）

```
从以下旅游文档的"元数据"区块抽取字段，输出 JSON：
{"content_type": "", "region": "", "name": "", "theme": ""}
字段缺失时填空字符串。字段名变体统一：城市/目的地→region；景点名称/线路名称/住宿名称/文档名称→name。

文档内容：
{content}
```

## 8. 工具/组件规格

| 组件 | 方法签名 | 返回 |
|------|----------|------|
| Embedder | `embed(texts: list[str]) -> list[list[float]]` | 向量列表（768 维） |
| Retriever | `retrieve(query: str, filters: dict, k: int) -> list[ChunkHit]` | 命中片段列表（含 score、metadata） |
| WebSearch | `search(query: str) -> list[WebHit]` | 联网搜索结果（Tavily） |
| Generator | `generate(query: str, context: str) -> Answer` | `Answer(text, citations)` |
| ImportService | `import_document(file) -> task_id` | 导入任务 ID |
| ImportService | `get_task(task_id) -> ImportTask` | 任务状态对象 |
| ChatService | `chat(query: str, session_id: str) -> Answer` | 答案与引用 |
| ChatService | `chat_stream(query: str, session_id: str) -> AsyncIterator[str]` | 增量 Token 流 |

## 9. 接口设计

### 9.1 REST 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/import | 上传文档（multipart），返回 task_id |
| GET | /api/v1/import/tasks/{task_id} | 查询导入任务状态 |
| GET | /api/v1/documents | 元数据列表，支持 content_type/region/name 筛选 |
| GET | /api/v1/search/attractions | 景点检索：query, city |
| GET | /api/v1/search/routes | 线路检索：query, region |
| GET | /api/v1/search/info | 实用信息：query, type(hotel/food/transport) |
| POST | /api/v1/chat | 单轮/多轮问答（非流式） |
| POST | /api/v1/chat/stream | 问答流式（SSE） |
| GET | /api/v1/sessions | 会话列表 |
| GET | /api/v1/sessions/{id}/messages | 会话消息 |
| DELETE | /api/v1/sessions/{id} | 删除会话 |

### 9.2 关键请求/响应示例

**POST /api/v1/chat**

```json
// 请求
{"query": "三亚有哪些必去景点", "session_id": "sess_123"}
// 响应
{
  "answer": "三亚的核心景点包括亚龙湾、蜈支洲岛、天涯海角和南山文化旅游区…",
  "citations": [
    {"source_file": "三亚景点推荐.md", "heading_path": "核心景点推荐 > 蜈支洲岛", "score": 0.92}
  ]
}
```

### 9.3 流式协议（SSE）

```
event: token
data: {"delta": "三亚"}

event: token
data: {"delta": "的核心景点"}

event: done
data: {"citations": [...]}
```

### 9.4 前端对接方式

- Axios 封装：统一 baseURL、请求拦截（鉴权头）、响应拦截（统一错误提示）。
- 流式对话：POST /api/v1/chat/stream 不支持 EventSource（仅 GET），前端用 `fetch` + `ReadableStream` 逐块读取 SSE 事件，渲染增量 Token。
- 会话管理：会话列表、消息历史通过 /sessions 接口读写；Pinia 保存当前会话与消息流。

## 10. 数据模型

### 10.1 关系型数据库（SQLAlchemy）

```sql
-- documents：来源文档与元数据
CREATE TABLE documents (
  id            BIGINT PRIMARY KEY AUTO_INCREMENT,
  source_file   VARCHAR(255) NOT NULL,
  source_path   VARCHAR(512),
  content_type  VARCHAR(32)  NOT NULL,
  region        VARCHAR(64),
  name          VARCHAR(128),
  theme         VARCHAR(255),
  status        VARCHAR(16)  DEFAULT 'imported',
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_content_type (content_type),
  KEY idx_region (region)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- chunks：切分片段
CREATE TABLE chunks (
  id            BIGINT PRIMARY KEY AUTO_INCREMENT,
  document_id   BIGINT NOT NULL,
  chunk_index   INT NOT NULL,
  heading_path  VARCHAR(512),
  content       TEXT NOT NULL,
  vector_id     VARCHAR(128),  -- 对应向量库条目
  KEY idx_document_id (document_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- import_tasks：导入任务
CREATE TABLE import_tasks (
  id               BIGINT PRIMARY KEY AUTO_INCREMENT,
  file_name        VARCHAR(255) NOT NULL,
  status           VARCHAR(16) DEFAULT 'created',  -- created/running/success/failed
  total_chunks     INT DEFAULT 0,
  processed_chunks INT DEFAULT 0,
  error_message    TEXT,
  created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
  finished_at      DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- sessions：会话
CREATE TABLE sessions (
  id          BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id  VARCHAR(64) UNIQUE NOT NULL,
  title       VARCHAR(255),
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- messages：会话消息
CREATE TABLE messages (
  id          BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id  VARCHAR(64) NOT NULL,
  role        VARCHAR(16) NOT NULL,   -- user/assistant
  content     TEXT NOT NULL,
  citations   TEXT,                   -- JSON 数组
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_session_id (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 10.2 向量库（Chroma）

- Collection：`travel_kb`
- 每条记录：`id=chunk_id`，`embedding`（768 维），`document`（片段文本），`metadata`（document_id、content_type、region、name、heading_path、source_file）。

## 11. 关键设计决策（ADR）

**ADR-001 采用 RAG 而非全量微调**
- 决策：以检索增强生成实现知识问答。
- 理由：知识持续更新，RAG 无需重训即可扩展内容；答案可追溯引用，符合可解释性需求。放弃微调（成本高、更新不便）。

**ADR-002 向量库选 ChromaDB，预留 Milvus 升级路径**
- 决策：使用 ChromaDB 1.5.x 本地持久化，通过 `store.py` 接口抽象隔离。
- 理由：ChromaDB 零运维、易上手，适合本机落地；数据规模增长后切换 Milvus 仅需替换 Adapter。放弃直接上 Milvus（一期运维成本高）。

**ADR-003 Embedding 选 bge-base-zh-v1.5 本地部署**
- 决策：本地加载 bge-base-zh-v1.5 生成 768 维向量。
- 理由：中文语义效果佳，本地化保障数据安全与零 API 成本。放弃纯在线 Embedding API（数据外发、成本随规模增长）。

**ADR-004 LLM 采用 OpenAI 兼容接口**
- 决策：通过 langchain-openai 兼容协议接入，Base URL / 模型名可配置。
- 理由：DeepSeek、Qwen 等主流模型均提供 OpenAI 兼容接口，便于切换与降级。放弃绑定单一厂商 SDK。

**ADR-005 结构化切分而非固定长度切分**
- 决策：按 H2/H3 标题边界切分。
- 理由：攻略文档天然按标题组织，结构切分保留语义完整性，提升引用可读性。放弃固定字符切分（易破坏段落语义）。

**ADR-006 元数据规范化前置**
- 决策：导入时统一将变体字段映射为规范 schema。
- 理由：来源元数据字段名不一致（城市/目的地等），前置规范化避免检索过滤时字段混乱。

**ADR-007 SSE 流式 + 非流式降级**
- 决策：优先 SSE 流式，失败自动降级为非流式。
- 理由：兼顾实时体验与可靠性（对应 BR-006）。

**ADR-008 本地向量检索 + 联网搜索兜底**
- 决策：优先本地向量检索，本地召回不足时转 Tavily 联网搜索补充。
- 理由：本地知识库覆盖攻略类内容，联网搜索兜底非知识库覆盖的实时/开放问题，兼顾准确性与可获取性（对应 BR-005）。

## 12. 非功能落地方案

### 12.1 鉴权与多租户

- 一期通过 API Key（请求头 `X-API-Key`）做轻量鉴权；数据模型预留 `tenant_id` 字段，V1.2 升级 JWT + RBAC，按租户隔离知识库与检索范围。

### 12.2 稳定性

- LLM/Embedding 外部调用统一封装重试（指数退避，最多 3 次）与超时（LLM 60s、Embedding 30s）。
- 引入熔断：连续失败阈值后短时间拒绝外部调用，避免雪崩。
- 导入失败隔离：任务级异常捕获，不向上抛出阻断服务。

### 12.3 可观测性

- 结构化日志（JSON），记录 trace_id、模块、耗时、错误栈。
- OpenTelemetry 链路追踪，覆盖导入、检索、生成全链路。
- Prometheus 指标：导入任务数、检索延迟、首 Token 延迟、外部调用错误率。

### 12.4 质量保障

- 单元测试：normalizer 映射、splitter 切分边界。
- 集成测试：导入→检索→问答链路。
- RAG 评估集：构造「问题 → 期望片段」样本，评估召回命中率与答案引用覆盖率。

### 12.5 安全设计

- 路径越界防护：导入仅允许访问配置的白名单目录，文件名做路径归一化校验。
- Prompt 注入防护：系统提示词明确「仅依据参考资料」，对用户输入做长度与格式约束。
- 密钥管理：API Key、LLM Key 通过环境变量注入，不落库、不入代码仓库。
- SQL 注入防护：全程 ORM 参数化查询。

### 12.6 数据治理

- 向量库与关系库定期备份；导入操作记录审计日志（操作人、文件、时间、结果）。
- 支持向量库重建：由 chunks 与 documents 表全量重建向量索引。

### 12.7 运行与运维

- 本机裸跑：`pip install` + `uvicorn` 直接启动，依赖本机 MySQL 与本地 ChromaDB，无容器编排。
- 配置分层：`.env`（密钥）→ 环境变量 → 配置文件，区分 dev/prod，密钥不入库、不入代码。
- 优雅停机：ASGI 服务监听 SIGTERM，完成在途请求后退出。
- 生产化预留：基础设施层通过 Port/Adapter 抽象，未来可平滑切换容器化（Docker）或云托管（RDS、Milvus、OSS）而不改业务代码。

## 13. 配置清单

| 配置项 | 说明 | 示例 |
|--------|------|------|
| DEEPSEEK_BASE_URL | LLM 接口地址 | https://api.deepseek.com |
| DEEPSEEK_API_KEY | LLM 密钥 | （环境变量） |
| DEEPSEEK_MODEL | 模型名 | deepseek-chat |
| TAVILY_API_KEY | 联网搜索密钥 | （环境变量） |
| EMBEDDING_MODEL | 向量模型 | BAAI/bge-base-zh-v1.5 |
| EMBEDDING_MODEL_PATH | 向量模型本地路径 | ./models/models--BAAI--bge-base-zh-v1.5/... |
| KNOWLEDGE_BASE_DIR | 知识库文档目录 | ./knowledge_base |
| VECTOR_STORE_DIR | 向量库目录（ASCII 路径） | /绝对路径/chroma |
| MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE | 数据库连接 | localhost / 3300 / root / *** / travel_kb |
| RETRIEVE_TOP_K | 召回数量 | 5 |

## 14. 错误处理

| 场景 | 处理策略 |
|------|----------|
| 文档解析失败 | 任务标记 failed，记录 error_message |
| 向量化失败 | 重试 3 次后任务失败，不影响其他任务 |
| LLM 超时/异常 | 返回统一错误码，流式降级为非流式 |
| 检索无结果 | 返回空结果并提示，不强行生成 |
| 越权/非法文件路径 | 拒绝访问，返回 403 |
| 会话不存在 | 返回 404 |

统一错误响应结构：`{"code": "IMPORT_FAILED", "message": "...", "trace_id": "..."}`。

## 15. 运行与初始化

### 15.1 本机裸跑

```bash
# 前提：本机 MySQL 已启动，并按 .env 配置数据库连接
pip install -e .
uvicorn app.main:app --reload
```

### 15.2 初始化与导入样例数据

```bash
# 首次启动自动建表；导入样例数据
curl -X POST http://localhost:8000/api/v1/import \
  -F "file=@data/景点攻略/三亚景点推荐.md"
```

## 16. 开发任务拆解

| 阶段 | 任务 | 依赖 |
|------|------|------|
| S0 | 项目初始化、配置、目录骨架 | - |
| S1 | 数据层（ORM 模型、MySQL、Chroma 封装） | S0 |
| S2 | 文档加载与元数据规范化 | S1 |
| S3 | 切分与向量化 | S2 |
| S4 | 导入任务编排与失败隔离 | S3 |
| S5 | 检索服务（向量检索 + 联网兜底） | S3 |
| S6 | 问答与引用 | S5 |
| S7 | 流式、多轮与历史记录 | S6 |
| S8 | 质量与治理（日志/追踪/测试/安全） | S7 |
| S9 | 本机运行与配置收尾 | S8 |
| S10 | 前端工程初始化（Vite + Vue 3 + Element Plus） | S9 |
| S11 | 检索页与管理页开发 | S10 |
| S12 | 智能问答页（流式对话 + 引用 + 历史） | S11 |

## 17. 前端设计

### 17.1 页面路由

| 路由 | 页面 | 对接接口 |
|------|------|----------|
| /chat | 智能问答页 | POST /api/v1/chat、/chat/stream、/sessions |
| /attractions | 景点检索页 | GET /api/v1/search/attractions |
| /routes | 线路检索页 | GET /api/v1/search/routes |
| /info | 实用信息查询页 | GET /api/v1/search/info |
| /admin/import | 内容导入页 | POST /api/v1/import、GET /api/v1/import/tasks/{id} |
| /admin/documents | 元数据管理页 | GET /api/v1/documents |

### 17.2 核心组件

| 组件 | 说明 |
|------|------|
| ChatPanel | 对话面板，渲染消息列表、输入框、发送 |
| MessageBubble | 消息气泡，区分用户/助手，支持 Markdown 渲染 |
| CitationList | 引用来源列表，展示 source_file、heading_path |
| SearchResultCard | 检索结果卡片，展示结构化字段 |
| ImportPanel | 导入面板，文件上传 + 任务状态轮询 |
| MetadataTable | 元数据表格，支持筛选 |

### 17.3 状态管理（Pinia）

- chatStore：当前会话、消息列表、流式状态（isStreaming）。
- 流式对话：逐块 append 到当前助手消息，`done` 事件写入 citations。

### 17.4 流式对话实现要点

- 用 `fetch('/api/v1/chat/stream', { method: 'POST', body: ... })` 发起请求，读取 `response.body.getReader()` 逐块解析 SSE。
- 每个 `token` 事件 append delta；`done` 事件结束并渲染引用。
- 流式异常时，前端回退调用非流式 /chat 接口保证有结果。

### 17.5 前后端联调

- 开发期：Vite dev server 通过 proxy 将 /api 转发到 FastAPI（http://localhost:8000），避免跨域。
- 生产期：`vite build` 产出静态资源，由 FastAPI 挂载 StaticFiles 或 Nginx 托管。
