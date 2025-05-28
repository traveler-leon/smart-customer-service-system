# 智能机场客服系统

## 📝 项目概述

智能机场客服系统是一个基于LangGraph+mcp构建的智能问答系统，专门为机场设计。               
技术上：系统采用多智能体协作架构，通过意图分类器将用户请求智能路由到不同的子智能体。由专业的子智能体来精准回答用户问题。              
业务上：系统主要提供四大类服务：           
1. 乘机须知问答，包括安检须知、联检(边检、海关、检疫)须知、出行须知（订票（改签）、值机、登机、中转、出发、到达、行李、证件）等；             
2. 信息查询（包括航班状态、时刻表等）；            
3. 业务办理（包括行李寄存、航班改签等）            
4. 以及闲聊。            
整体系统支持多轮对话，能够根据上下文理解用户意图，并通过知识库检索和数据库查询为用户提供准确、及时的信息服务。            

## 目录
- [📝 项目概述](#-项目概述)
- [🏗️ 系统架构](#️-系统架构)
  - [🛠️ 技术栈](#️-技术栈)
- [✨ 功能亮点](#-功能亮点)
  - [现有基于大模型的客服系统的问题分析](#现有基于大模型的客服系统的问题分析)
  - [我们的智能客服系统的两点](#我们的智能客服系统的两点)
- [🚀 快速开始](#-快速开始)
  - [环境要求](#环境要求)
  - [安装步骤](#安装步骤)
  - [运行系统](#运行系统)
- [🤝 贡献指南](#-贡献指南)
- [📜 许可证](#-许可证)

## 🏗️ 系统架构

系统基于LangGraph构建，采用图形化工作流结构，主要结构如下：
![系统架构图](./images/主架构图.png)

### 🛠️ 技术栈

- **LangGraph**: 构建工作流和状态管理
- **LangChain**: 基础组件库
- **MCP**: 以mcp技术弹性接入第三方服务，诸如高德mcp server，12306mcp servser

## ✨ 功能亮点
### 现有基于大模型的客服系统的问题分析
1. 总是以被动式的形式提供服务，用户问一个问题，智能客服回答一个问题。被动式的回答总是给人心理感觉还是个机器；
2. 回答的答案太过长篇大论，智能客服回答的答案虽然能解决用户问题，但是篇幅通常过长、内容需要用户进行阅读和理解；
3. 非个性化回答，任何人问同一个问题，答案都几乎一样，这是现有智能客服的范式导致。回答的答案不会考虑用户的历史画像。

### 我们的智能客服系统的两点
1. 主动+被动的形式来提供服务：当用户问题和知识库答案粒度不匹配时，智能客服会选择生成一个问题，要求用户澄清，如果匹配，则生成答案。这让用户从心理上感觉智能客服更新一个人。
2. 超短的答案回复，第一点的描述中，实现了一个漏斗式的问答交互，通过不断的问题澄清和追问，实现了主动的心理感受之外，也附带的实现了让每一次的回复都足够的短和精准。省去了用户的长时间理解，同时也给实时的语音交互和实时电话的接入提供了技术支持。
3. 个性化的问答：整个客服系统会通过历史咨询的历史来沉淀出用户画像，回答时会跟进用户画像实现个性化服务；
4. 闭环系统优化：系统设计了一个强大的记忆模块：可沉淀：用户画像、事实记忆、情景记忆等内容。反哺现有知识库。实现闭关增强。
5. 具备可选的多语言模块，支持多语言问答的同时，兼顾了问答的准确性
6. 具备可选的安全模块，能够对用户问题和智能客服回答的问题做安全审查。避免出现不合规内容。
7. 具备可选的多语言情绪识别模块，能够实时检测用户的情绪，使得客服系统可以根据用户的情绪来调整回答的语气、以及考虑是否切到人工（如果有人工坐席）

## 🚀 快速开始

### 环境要求

- Python 3.12+
- 依赖库：见`pyproject.toml`文件

### 安装步骤

1. 克隆项目并进入项目目录
```bash
git clone https://github.com/traveler-leon/smart-customer-service-system.git
cd smart-customer-service-system
```

2. 使用uv创建虚拟环境并安装依赖
```bash
uv sync
```

这样就使用uv替代了传统的venv和pip命令，保持了项目的其他安装流程不变。
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件，填入必要的API密钥和配置
```

### 运行系统

```bash
uv run main.py
```

## 🤝 贡献指南

欢迎贡献代码，请遵循以下步骤：
1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 📜 许可证

本项目采用 MIT 许可证。详情请见 [LICENSE](LICENSE) 文件。

```text
MIT License

Copyright (c) [2025] [traveler-leon]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
