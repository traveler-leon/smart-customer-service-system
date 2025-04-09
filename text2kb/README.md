# Text2KB - 知识库检索模块

本模块提供从知识库中检索信息的异步API和工具。

## 功能特点

- 异步API设计，提高性能和并发处理能力
- 集成LangChain工具，易于与智能代理集成
- 简洁的接口设计，使用方便

## 安装依赖

```bash
pip install aiohttp langchain-core typing-extensions
```

## 使用示例

### 直接使用客户端API

```python
import asyncio
from text2kb.client import retrieve_from_kb

async def example():
    results = await retrieve_from_kb(
        question="查询问题", 
        dataset_name="数据集名称",
        address="自定义地址",
        api_key="自定义密钥",
        similarity_threshold=0.3,  # 自定义相似度阈值
        top_k=10  # 检索结果数量上限
    )
    
    # 处理结果（现在返回包含内容和相似度信息的字典列表）
    for result in results:
        content = result['content']        # 检索内容
        similarity = result['similarity']  # 相似度分数
        is_low = result['low_similarity']  # 是否低于相似度阈值
        
        print(f"相似度: {similarity:.4f} {'[低相似度]' if is_low else ''}")
        print(content)

# 运行示例
asyncio.run(example())
```

### 使用LangChain工具

```python
import asyncio
from text2kb.tools import kb_retrieve

async def example():
    result = await kb_retrieve.ainvoke({
        "question": "可以携带刀具吗?",
        "dataset_name": "深圳民航机场知识库"
    })
    
    print(result)

# 运行示例
asyncio.run(example())
```

### 在LangGraph中使用

```python
from text2kb.tools import call_kb_retrieve
from langgraph.graph import END, StateGraph

# 在图节点中使用
async def kb_lookup_node(state):
    question = state["question"]
    dataset_name = state["dataset_name"]
    
    response = await call_kb_retrieve(
        question=question,
        dataset_name=dataset_name,
        tool_call_id="some-tool-call-id"
    )
    
    return {"kb_response": response}

# 构建图
graph = StateGraph()
graph.add_node("kb_lookup", kb_lookup_node)
# ... 配置其他节点和边 ...
```

## 配置参数

可以在`config.py`中修改默认的API地址和密钥：

```python
# 知识库API配置
KB_ADDRESS = "your-api-address"  # 替换为实际地址 
KB_API_KEY = "your-api-key"  # 替换为实际API密钥
```

也可以在调用函数时直接传入参数：

```python
results = await retrieve_from_kb(
    question="查询问题", 
    dataset_name="数据集名称",
    address="自定义地址",
    api_key="自定义密钥",
    similarity_threshold=0.3,  # 自定义相似度阈值
    top_k=10  # 检索结果数量上限
)
``` 