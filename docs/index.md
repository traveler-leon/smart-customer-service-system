# 文档索引

欢迎使用智能客服系统！本页面汇总了所有可用文档，帮助您快速找到所需信息。

## 📚 文档导航

### 🚀 新手入门

| 文档 | 说明 | 适用场景 |
|-----|------|---------|
| [快速开始指南](../QUICKSTART.md) | 5分钟快速启动系统 | 初次使用、快速体验 |
| [README](../README.md) | 项目概述和功能介绍 | 了解项目全貌 |
| [环境变量模板](../.env.example) | 所有配置项模板 | 配置参考 |

### 🔧 配置与部署

| 文档 | 说明 | 适用场景 |
|-----|------|---------|
| [配置与启动指南](../CONFIGURATION.md) | 完整的配置说明和部署指南 | 详细配置、生产部署 |
| [Docker 部署指南](../DOCKER.md) | Docker 和 Docker Compose 部署 | 容器化部署、生产环境 |
| [启动脚本](../start.sh) | 一键检查环境并启动 | 本地开发 |

### 🏗️ 架构与设计

| 文档 | 说明 | 适用场景 |
|-----|------|---------|
| [系统架构](../README.md#系统架构) | 系统架构说明 | 理解系统设计 |
| [技术栈](../README.md#技术栈) | 使用的技术和框架 | 技术选型参考 |
| [功能亮点](../README.md#功能亮点) | 核心功能特性 | 了解系统能力 |

### 📖 功能文档

| 功能模块 | 说明 | 配置文件 |
|---------|------|---------|
| **RAG 问答** | 基于知识库的问答 | [text2kb.py](../config/modules/text2kb.py) |
| **Text2SQL** | 数据库查询 | [text2sql.py](../config/modules/text2sql.py) |
| **多智能体协作** | Agent 系统配置 | [agents.py](../config/modules/agents.py) |
| **记忆管理** | 长短期记忆系统 | [agents.py](../config/modules/agents.py) |

### 🛠️ 开发指南

| 文档 | 说明 | 适用场景 |
|-----|------|---------|
| [贡献指南](../README.md#贡献指南) | 如何参与项目贡献 | 开发者 |
| [配置工厂](../config/factory.py) | 配置管理代码 | 扩展开发 |
| [日志系统](../common/logging/) | 日志配置和使用 | 调试排错 |

---

## 📋 快速链接

### 常用命令

**启动系统**:
```bash
# 使用启动脚本
./start.sh

# 或使用 uv
uv run main.py

# 或使用 Docker
docker compose up -d
```

**查看日志**:
```bash
# 实时日志
tail -f logs/agents/app_$(date +%Y%m%d).log

# Docker 日志
docker compose logs -f
```

**测试接口**:
- API 文档: http://localhost:8081/docs
- 测试页面: http://localhost:8081/static/qa_test.html

### 配置文件位置

```
smart-customer-service-system/
├── .env.example              # 环境变量模板
├── config/                   # 配置目录
│   ├── dev.py               # 开发环境配置
│   ├── factory.py           # 配置工厂
│   └── modules/             # 模块配置
│       ├── agents.py        # 智能体配置
│       ├── text2kb.py       # 知识库配置
│       └── text2sql.py      # Text2SQL 配置
├── docker-compose.yml       # Docker Compose 配置
├── Dockerfile               # Docker 镜像配置
└── start.sh                 # 启动脚本
```

---

## 🔍 按场景查找文档

### 场景 1: 首次部署系统

1. 阅读 [README](../README.md) 了解项目
2. 按照 [快速开始指南](../QUICKSTART.md) 安装
3. 参考 [配置指南](../CONFIGURATION.md) 配置环境变量
4. 使用 `./start.sh` 启动系统

### 场景 2: Docker 容器化部署

1. 准备 `.env` 文件
2. 阅读 [Docker 部署指南](../DOCKER.md)
3. 执行 `docker compose --profile app --profile full up -d`

### 场景 3: 生产环境部署

1. 阅读 [配置指南](../CONFIGURATION.md) 的生产环境章节
2. 阅读 [Docker 部署指南](../DOCKER.md) 的生产环境建议
3. 配置监控和备份策略

### 场景 4: 功能定制开发

1. 了解 [系统架构](../README.md#系统架构)
2. 查看 [配置工厂](../config/factory.py) 代码
3. 参考对应模块的配置文件进行扩展

### 场景 5: 问题排查

1. 查看 [配置指南](../CONFIGURATION.md) 的故障排查章节
2. 查看 [Docker 指南](../DOCKER.md) 的故障排查章节
3. 检查日志：`logs/agents/app_*.log`

---

## 📊 配置项速查

### 必需配置

| 配置项 | 说明 | 示例值 |
|-------|------|--------|
| `LLM_BASE_URL` | LLM API 地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_API_KEY` | LLM API 密钥 | `sk-xxxxxxxxxxxxx` |
| `LLM_MODEL` | 模型名称 | `qwen-max` |
| `REDIS_HOST` | Redis 地址 | `localhost` |
| `REDIS_PORT` | Redis 端口 | `6379` |

### 可选配置

| 配置项 | 说明 | 何时需要 |
|-------|------|---------|
| `KB_ADDRESS` | RAGFlow 地址 | 使用 RAG 问答功能 |
| `DB_HOST` | 数据库地址 | 使用 Text2SQL 功能 |
| `CHROMA_HOST` | ChromaDB 地址 | 使用 Text2SQL 功能 |
| `ROUTER_LLM_MODEL` | 路由模型 | 优化意图识别性能 |
| `IMAGE_LLM_MODEL` | 视觉模型 | 支持图片理解 |

完整配置列表请查看 [.env.example](../.env.example)。

---

## 🆘 获取帮助

### 文档问题

- 📖 查阅相关文档的故障排查章节
- 🔍 搜索 [Issues](https://github.com/traveler-leon/smart-customer-service-system/issues)

### 技术支持

- 💬 提交 [Issue](https://github.com/traveler-leon/smart-customer-service-system/issues/new)
- 🤝 参与 [讨论](https://github.com/traveler-leon/smart-customer-service-system/discussions)
- ⭐ 关注项目获取最新更新

---

## 📝 文档贡献

发现文档问题或有改进建议？欢迎：

1. Fork 项目
2. 修改文档
3. 提交 Pull Request

感谢您的贡献！

---

**最后更新**: 2025-10-13

