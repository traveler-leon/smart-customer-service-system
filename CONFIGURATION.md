# 项目配置与启动指南

本文档提供智能客服系统的详细配置说明和启动指南。

## 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [环境变量配置](#环境变量配置)
- [配置文件说明](#配置文件说明)
- [依赖服务部署](#依赖服务部署)
- [启动系统](#启动系统)
- [常见问题](#常见问题)

---

## 系统要求

### 运行环境
- **Python**: 3.12 或更高版本
- **包管理器**: [uv](https://github.com/astral-sh/uv) (推荐) 或 pip
- **操作系统**: Linux / macOS / Windows

### 依赖服务
- **Redis**: 用于会话状态存储
- **PostgreSQL**: 用于业务数据存储 
- **ChromaDB**: 用于向量存储
- **RAGFlow**: 用于知识库管理 

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/traveler-leon/smart-customer-service-system.git
cd smart-customer-service-system
```

### 2. 安装依赖

#### 使用 uv（推荐）

```bash
# uv 会自动创建虚拟环境并安装所有依赖
uv sync
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example.env

# 编辑 .env 文件，填入必要的配置
vim .env  # 或使用其他编辑器
```

### 4. 启动系统

```bash
# 使用 uv
uv run main.py

```

系统将在 `http://0.0.0.0:8081` 启动。

---

## 环境变量配置

### 配置文件位置

- **模板文件**: `.env.example` - 环境变量模板，包含所有可配置项
- **实际配置**: `.env` - 根据模板创建，填入实际值（不会提交到版本控制）

### 核心配置项

#### 1. 运行环境配置

```bash
# 环境类型：dev(开发) / prod(生产) / test(测试)
HZ_FUTURE_SMART_BRAIN_ENV=dev
```

#### 2. 内容生成大语言模型配置
这个模型的配置，主要是用于终端内容生成的，所以建议使用内容生成或者理解能力更强的大模型。
```bash
# 主 LLM 配置（必填）
LLM_BASE_URL=https://api.example.com/v1  # 示例：阿里云通义千问
LLM_API_KEY=your-api-key-here
LLM_MODEL=qwen-max
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1000
LLM_MAX_HISTORY_TURNS=10 # 保存历史对话轮次
```
#### 3. 路由 LLM配置（可选）
1. 路由llm是用于做主节点决策判断的，所以建议选择结构化输出或者更智能的大模型。
2. 如果未配置任何内容，则默认和内容生成大模型是一致
3. 如果配置了模型名字，但是未配置base_url,api_key，则默认模型提供商和内容生成大模型保持一致，为LLM_BASE_URL
```bash
ROUTER_LLM_BASE_URL=https://api.example.com/v1
ROUTER_LLM_API_KEY=your-api-key-here
ROUTER_LLM_MODEL=qwen-turbo
ROUTER_LLM_TEMPERATURE=0.3
```
#### 4. 图像理解 LLM（可选，用于多模态，）
1. 此模型必须是多模态模型，诸如（glm-4.1v，glm-4.5v，qwen3-vl等）
2. 如果未配置，默认和内容生成模型保持一致，此时，如果你的业务中需要用到图片识别，那么内容生成模型就要支持多模态，如果业务中暂时不需要图片识别
那么，内容生成模型是不是多模态都无所谓。
3. 如果配置了模型名字，但是未配置base_url,api_key，则默认模型提供商和内容生成大模型保持一致，为LLM_BASE_URL

```bash
IMAGE_LLM_API_KEY=your-api-key-here
IMAGE_LLM_BASE_URL=https://api.example.com/v1
IMAGE_LLM_MODEL=qwen-vl-max
```

**支持的 LLM 提供商**:
- 阿里云通义千问 (DashScope)
- 智谱 AI (GLM)
- 硅基流动 (SiliconFlow)
- OpenAI 兼容接口
- Xinference (本地部署)
- Ollama（本地部署）
- vllm （本地部署）
**所有只要符合openai接口规范的，都支持。**

#### 5. Embedding 模型配置
1. 如果未配置base-url和api-key，默认和内容生成模型的提供商保持一致
2. 此向量模型支持云端提供商，也支持本地部署，本地部署之后，诸如xinference部署了bge-large-zh-v1.5,则配置如下，对于本地来说，api-key可有可无，base-url如下，建议参考模型平台官网说明。
3. ** 最需要注意的是，向量模型要和ragflow配置的向量模型保持一致，因为涉及到检索匹配，向量维度一定要统一 **

```bash
# xinference部署案例（其他本地部署方式类似）
#EMBEDDING_API_KEY=sk-zcewmhyhkaelmhrijbipqbrlfxhwnfbuegcpynkhdbzkqixd
#EMBEDDING_BASE_URL="http://192.168.0.105:9997/v1"
#EMBEDDING_MODEL=bge-large-zh-v1.5
#EMBEDDING_DIMENSIONS=1024
#EMBEDDING_MAX_TOKENS=1024

EMBEDDING_BASE_URL=https://api.example.com/v1
EMBEDDING_API_KEY=sk-xxxxxxxxxxxxx
EMBEDDING_MODEL=bge-large-zh-v1.5
EMBEDDING_DIMENSIONS=1024
EMBEDDING_MAX_TOKENS=1024
```
#### 6. ReRank 模型配置
原理同Embedding模型的配置

```bash
# xinference部署案例（其他本地部署方式类似）
#RERANKER_BASE_URL=http://192.168.0.105:9997/v1/rerank
#RERANKER_API_KEY='leon'
#RERANKER_MODEL=bge-reranker-large

RERANKER_BASE_URL=https://api.example.com/v1/rerank
RERANKER_API_KEY='leon'
RERANKER_MODEL=bge-reranker-large
```

**推荐模型**:
- `bge-large-zh-v1.5`: 中文效果优秀，1024 维
- `=bge-reranker-large`: 中文效果优秀

#### 7. Redis 配置（必需）

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-password  # 如果有密码，建议先不设密码
REDIS_CHECKPOINT_TTL=7200
REDIS_STORE_TTL=86400
```

### 8. chroma配置（用于存储向量数据）
相关配置涉及到最近邻算法（最小世界图算法HNSW），如果不太懂，可以保持案例一致。
```bash
STORAGE_TYPE=chromadb # 必须是chromadb，不需要改动
CHROMA_HOST=192.168.0.105 # chromadb部署的地址
CHROMA_PORT=8000 # 端口

CHROMA_N_RESULTS=5
CHROMA_M=16
CHROMA_CONSTRUCTION_EF=100
CHROMA_SEARCH_EF=50
CHROMA_SPACE=cosine
```
#### 9. 数据库配置（Text2SQL 功能需要）
1. 这里的数据库其实是为了查询航班而设置了，可以看到只设置了库名，但为设置表名，这是因为我们是一text2sql的形式来取数的，所以表名要和sql的知识库保持一致。
```bash
# PostgreSQL
DB_TYPE=postgresql # 无需修改，建议保持一致
DB_HOST=192.168.0.105
DB_PORT=5432
DB_USER=hzwl
DB_PASSWORD=hzwl@12345
DB_DATABASE=hzwl
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20
DIALECT=PostgreSQL # 保持一致，无需修改
LANGUAGE=zh # 保持一致，无需修改。

```

#### 10. 知识库配置（RAG 功能需要）
1.本项目才有ragflow管理知识，所以需要结合ragflow
```bash
# RAGFlow 配置
KB_ADDRESS=http://localhost:9380 #ragflow地址
KB_API_KEY=ragflow-xxxxxxxxxxxxx #ragflow的key
KB_DATASET_NAME=民航知识库  # 您的ragflow中建立的知识库名称
KB_SIMILARITY_THRESHOLD=0.2 # 建议设置小一些，
KB_TOPK=6 

```
#### 11. 优质QA配置
1.QA_SCORE_THRESHOLD为匹配度，最大匹配度为1
```bash
QA_SCORE_THRESHOLD=0.75 #匹配度
QA_TIME_DECAY_FACTOR=0.8 #考虑时间衰减，这样如果有新的同样或者类似规定的知识更新的时候，保证匹配到最新的。

```
#### 12. 情感识别模型配置
1.如果你启用情感识别，则可以部署，本项目采用multilingual-sentiment-analysis模型，可自行往hugging-face下载
2.情感识别主要用于切人工客服和调整回复口气而用。
3.如果不需要情感识别，可以不用设置，前段传递参数的时候，对于情感识别参数要关闭。
```bash
EMOTION_MODEL= "/Users/hzwl/Documents/coding/models/multilingual-sentiment-analysis"

```

#### 13. 日志配置

```bash
LOG_LEVEL=DEBUG  # 开发环境用 DEBUG，生产环境用 INFO
LOG_DIR=logs
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=5
```

---


## 启动系统

### 开发环境启动

```bash
# 方式 1: 使用 uv（推荐）
uv run main.py
```

### 验证启动

启动成功后，访问以下地址验证：

- **API 文档**: http://localhost:8081/docs
- 打开docs文件夹下的chat.html文件进行聊天对话测试
---

**最后更新**: 2025-10-14

