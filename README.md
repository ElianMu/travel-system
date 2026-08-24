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

# 2. 配置环境变量（复制 .env.example 为 .env，填入密钥）
cp .env.example .env

# 3. 启动服务（启动时自动预热模型 + 建表）
uvicorn app.main:app --reload
```

启动后访问 http://localhost:8000/docs 查看接口文档。

## 导入知识库

```bash
# 批量导入 data/ 目录下全部文档
python -m scripts.import_all
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

## 运行测试

```bash
python -m pytest tests/ -v
```

> 说明：Windows 下 torch（Embedding 模型）与 pymysql 存在原生库冲突，应用启动时会先预热模型再建表，规避段错误。向量库采用 numpy 本地索引（数据量级下暴力余弦检索毫秒级），替代 chromadb 以规避其在 Windows 下的稳定性问题。
