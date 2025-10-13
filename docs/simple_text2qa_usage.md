# 简化版 Text2QA 使用说明

## 概述

这是一个超级简化的Redis QA存储和检索系统，专为快速查询设计：

- **一个连接池** - Redis连接池管理
- **存QA对** - 支持单个和批量存储
- **取一个结果** - 搜索返回最匹配的一个QA对
- **无多余抽象** - 直接操作，简单明了

## 快速开始

### 1. 基础使用

```python
import asyncio
from text2qa.simple_redis_qa import create_simple_qa

async def main():
    # 创建QA系统（自动连接Redis）
    qa = await create_simple_qa(host="localhost", port=6379, db=2)
    
    try:
        # 添加QA对
        qa_id = await qa.add_qa(
            question="什么是Redis？",
            answer="Redis是内存数据库",
            tags=["Redis", "数据库"]
        )
        
        # 搜索（返回最匹配的一个）
        result = await qa.search_one("Redis是什么")
        if result:
            print(f"问题: {result['question']}")
            print(f"答案: {result['answer']}")
    
    finally:
        await qa.close()

asyncio.run(main())
```

### 2. 批量操作

```python
# 批量添加
qa_pairs = [
    {
        "question": "如何连接Redis？",
        "answer": "使用redis-py库",
        "tags": ["Redis", "连接"]
    },
    {
        "question": "Redis有什么用？", 
        "answer": "做缓存和数据库",
        "tags": ["Redis", "用途"]
    }
]

batch_ids = await qa.add_qa_batch(qa_pairs)
print(f"批量添加了 {len(batch_ids)} 个QA对")
```

## API接口

### 添加QA对

```http
POST /simple-text2qa/qa
{
    "question": "什么是Redis？",
    "answer": "Redis是内存数据库",
    "tags": ["Redis"]
}
```

### 搜索QA对

```http
POST /simple-text2qa/search
{
    "query": "Redis是什么",
    "tags": ["Redis"]  // 可选
}
```

返回最匹配的一个结果：
```json
{
    "success": true,
    "message": "搜索成功",
    "data": {
        "id": "uuid",
        "question": "什么是Redis？",
        "answer": "Redis是内存数据库",
        "tags": ["Redis"],
        "created_at": 1234567890
    }
}
```

### 获取QA对

```http
GET /simple-text2qa/qa/{qa_id}
```

### 删除QA对

```http
DELETE /simple-text2qa/qa/{qa_id}
```

### 获取总数

```http
GET /simple-text2qa/count
```

### 健康检查

```http
GET /simple-text2qa/ping
```

## 配置

### 环境变量

```bash
REDIS_HOST=localhost
REDIS_PORT=6379  
REDIS_QA_DB=2
REDIS_PASSWORD=your_password
REDIS_MAX_CONNECTIONS=20
QA_INDEX_NAME=qa_index
QA_KEY_PREFIX=qa:
```

### 代码配置

```python
from text2qa.simple_redis_qa import create_simple_qa

qa = await create_simple_qa(
    host="localhost",
    port=6379,
    db=2,
    password="your_password",
    max_connections=20
)
```

## 在机场客服中使用

```python
from text2qa.simple_redis_qa import create_simple_qa

# 初始化QA系统
qa_system = await create_simple_qa()

# 预设一些常见问题
await qa_system.add_qa(
    question="如何办理登机手续？",
    answer="可以在网上、自助机器或值机柜台办理登机手续。",
    tags=["登机", "值机"]
)

# 用户查询处理
async def handle_user_question(user_question: str) -> str:
    result = await qa_system.search_one(user_question)
    if result:
        return result['answer']
    else:
        return "抱歉，我没有找到相关答案，请联系人工客服。"

# 使用示例
answer = await handle_user_question("怎么值机？")
print(answer)  # 输出预设的答案
```

## 与现有系统集成

```python
# 在main.py中添加路由
from api.simple_text2qa_api import router as simple_qa_router

app.include_router(simple_qa_router)
```

就这么简单！没有复杂的中间件，没有多余的抽象，就是一个Redis连接池 + 存取QA对的功能。
