# text2qa 灵活存储结构指南

## 概述

text2qa 模块现在支持灵活的QA存储结构，可以存储基本的问答对，同时支持可选的图片和任意扩展字段。

## 核心特性

### 1. 灵活的存储结构

- **必需字段**：`question`（问题）、`answer`（答案）
- **可选字段**：
  - `tags`：标签列表
  - `images`：图片URL/路径列表
  - **任意扩展字段**：如 `difficulty`、`category`、`author`、`source_url`、`rating` 等

### 2. 精确的搜索匹配

- 用户查询（`query`）**只匹配** `question` 字段
- 不搜索答案内容，确保精确匹配
- 支持标签过滤
- 返回最匹配的一个结果

### 3. 高性能异步操作

- Redis连接池管理
- 批量存储使用pipeline
- 异步I/O操作

## 使用示例

### 基本QA对

```python
from text2qa import create_simple_qa

qa = await create_simple_qa()

# 只存储问题和答案
qa_id = await qa.add_qa(
    question="什么是Python？",
    answer="Python是一种高级编程语言。"
)
```

### 带图片的QA对

```python
# 存储带图片的QA
qa_id = await qa.add_qa(
    question="如何安装Python？",
    answer="从官网下载安装包进行安装。",
    tags=["Python", "安装"],
    images=[
        "https://example.com/python-install-1.png",
        "https://example.com/python-install-2.png"
    ]
)
```

### 带扩展字段的QA对

```python
# 存储带扩展字段的QA
qa_id = await qa.add_qa(
    question="Redis有什么优点？",
    answer="Redis具有高性能、支持多种数据结构等优点。",
    tags=["Redis", "数据库"],
    images=["https://example.com/redis-arch.png"],
    difficulty="中级",
    category="数据库",
    author="技术专家",
    source_url="https://redis.io/docs",
    rating=4.5
)
```

### 批量添加

```python
qa_pairs = [
    {
        "question": "什么是Docker？",
        "answer": "Docker是一个容器化平台。",
        "tags": ["Docker", "容器"],
        "images": ["https://example.com/docker.png"],
        "difficulty": "中级",
        "type": "技术问答"
    },
    {
        "question": "什么是微服务？",
        "answer": "微服务是一种架构模式。",
        "tags": ["架构", "微服务"],
        "video_url": "https://example.com/microservices.mp4",
        "links": ["https://microservices.io"]
    }
]

batch_ids = await qa.add_qa_batch(qa_pairs)
```

### 搜索和检索

```python
# 搜索（只匹配问题字段）
result = await qa.search_one("Python")
if result:
    print(f"问题: {result['question']}")
    print(f"答案: {result['answer']}")
    print(f"图片: {result.get('images', [])}")
    print(f"扩展字段: {result.get('extra_fields', {})}")

# 按标签搜索
result = await qa.search_one("", tags=["Python"])

# 获取完整QA数据
full_data = await qa.get_qa(qa_id)
```

## 数据结构

### Redis存储格式

```json
{
    "id": "uuid-string",
    "question": "问题内容",
    "answer": "答案内容",
    "tags": ["标签1", "标签2"],
    "images": ["图片URL1", "图片URL2"],
    "extra_fields": {
        "difficulty": "中级",
        "category": "数据库",
        "author": "技术专家",
        "custom_field": "自定义值"
    },
    "created_at": 1234567890.123
}
```

### Redis索引字段

- `question`：文本字段，可搜索、可排序
- `answer`：文本字段
- `tags`：标签字段
- `images`：文本字段
- `extra_fields`：文本字段
- `created_at`：数值字段，可排序

## API接口

所有API接口都支持新的灵活结构：

- `POST /simple-text2qa/qa` - 添加单个QA对
- `POST /simple-text2qa/qa/batch` - 批量添加QA对
- `POST /simple-text2qa/search` - 搜索QA对
- `GET /simple-text2qa/qa/{qa_id}` - 获取特定QA对
- `DELETE /simple-text2qa/qa/{qa_id}` - 删除QA对
- `GET /simple-text2qa/count` - 获取QA总数
- `GET /simple-text2qa/ping` - 健康检查

## 配置说明

配置文件 `config/modules/simple_text2qa.py` 支持所有Redis连接参数：

```python
SIMPLE_TEXT2QA_CONFIG = {
    "host": "localhost",
    "port": 6379,
    "db": 2,
    "password": None,
    "max_connections": 20,
    "index_name": "qa_index",
    "key_prefix": "qa:"
}
```

## 注意事项

1. **搜索范围**：用户查询只匹配 `question` 字段，不会搜索答案内容
2. **返回结果**：搜索始终返回最匹配的一个结果
3. **扩展字段**：可以添加任意数量和类型的扩展字段
4. **图片支持**：images 字段存储图片URL或文件路径列表
5. **数据完整性**：所有数据在 Redis 中以 JSON 格式存储，保持结构完整

## 示例文件

- `examples/simple_qa_example.py` - 完整的使用示例
- `test_flexible_qa.py` - 测试灵活存储结构的脚本
