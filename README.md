# 景文智核 · 智能旅游知识库系统

面向旅游场景的检索增强生成（RAG）知识库系统，支持景点攻略、线路推荐、酒店信息、美食推荐、交通指南的内容导入、检索与带引用的知识问答。

## 技术栈

- 后端：Python 3.11+ / FastAPI / SQLAlchemy / MySQL
- RAG：本地 bge-base-zh-v1.5 向量化 + numpy 向量索引 + 余弦检索
- LLM：DeepSeek（OpenAI 兼容），支持流式输出
- 联网搜索：Tavily（知识库无结果时兜底）
- 前端：Vue 3 + Element Plus（见 frontend/）

## 本机运行

```bash
# 1. 创建虚拟环境并安装依赖
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .

# 2. 配置环境变量（复制 .env.example 为 .env，填入密钥与 MySQL 连接）
cp .env.example .env

# 3. 创建数据库（表在服务启动时自动创建）
mysql -h <host> -P <port> -u <user> -p -e "CREATE DATABASE IF NOT EXISTS travel_kb CHARACTER SET utf8mb4"

# 4. 启动服务（启动时自动预热模型 + 建表）
scripts/start.sh                  # 开发模式，带热重载
APP_ENV=prod scripts/start.sh     # 生产模式，缺少密钥时拒绝启动
```

启动后访问 http://localhost:8000/docs 查看接口文档。可用环境变量 `HOST`、`PORT` 修改监听地址。

服务收到 SIGTERM 后停止接收新连接，等待在途请求完成（最长 30 秒）再退出。

### 配置分层

优先级从高到低：环境变量、`.env.{APP_ENV}`、`.env`、代码默认值。`APP_ENV` 取 `dev` 或 `prod`。

### 接口鉴权

设置 `API_KEY` 后，`/api/v1/*` 需携带请求头 `X-API-Key`，否则返回 401；`/health` 和 `/metrics` 不受影响。`API_KEY` 为空时不启用，生产环境必填。

前端通过 `VITE_API_KEY` 传入相同的值（如 `VITE_API_KEY=xxx npm run build`）。该值会打进前端代码，只适合内网或受信任的使用者，不能当作用户登录。

### 前端

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173，/api 转发到 http://localhost:8000
```

## 导入知识库

```bash
# 批量导入 data/ 目录下全部文档；同名文件会替换旧版本，可重复执行
python -m scripts.import_all

# 由 MySQL 中的文档与片段全量重建向量索引
python -m scripts.rebuild_index
```

## 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/import | 上传文档导入 |
| GET  | /api/v1/import/tasks/{id} | 导入任务状态 |
| GET  | /api/v1/search/attractions | 景点检索 |
| GET  | /api/v1/search/routes | 线路检索 |
| GET  | /api/v1/search/info | 实用信息（hotel/food/transport） |
| POST | /api/v1/chat | 问答（非流式） |
| POST | /api/v1/chat/stream | 问答（SSE 流式） |
| GET/POST/DELETE | /api/v1/sessions | 会话管理 |
| GET  | /metrics | Prometheus 指标 |

错误响应统一为 `{"code": "...", "message": "...", "trace_id": "..."}`。

## 测试与评估

```bash
pip install -e ".[dev]"

# 测试使用独立的 travel_kb_test 库与临时向量索引，结束后自动清理；MySQL 不可用时跳过相关用例
python -m pytest tests/ -v

# RAG 评估：输出召回命中率与引用覆盖率；加 --llm 时额外统计答案正文的引用
python -m scripts.evaluate_rag
```

> 说明：Windows 下 torch（Embedding 模型）与 pymysql 存在原生库冲突，应用启动时会先预热模型再建表，规避段错误。向量库采用 numpy 本地索引（数据量级下暴力余弦检索毫秒级），替代 chromadb 以规避其在 Windows 下的稳定性问题。
