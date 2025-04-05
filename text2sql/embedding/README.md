# 嵌入模型提供者

## 概述

嵌入模型提供者用于生成文本的向量表示，用于语义搜索、相似度计算等任务。在text2sql系统中，嵌入模型将自然语言问题和SQL查询转换为向量形式，便于在向量数据库中存储和检索。

## OpenAI兼容接口

本系统采用了基于OpenAI兼容接口的统一实现方式，支持多家厂商的嵌入服务。由于很多国内外厂商都兼容OpenAI的API规范，我们只需通过配置以下参数即可无缝切换不同供应商：

- `base_url`: API服务地址
- `api_key`: 认证密钥
- `embedding_model`: 模型名称

## 配置示例

```python
config = {
    "embedding": {
        "type": "openai",  # 使用OpenAI兼容的接口
        "api_key": "sk-zcewmhyhkaelmhrijbipqbrlfxhwnfbuegcpynkhdbzkqixd",
        "base_url": "https://api.siliconflow.cn/v1",  # 硅流API
        "embedding_model": "BAAI/bge-large-zh-v1.5"  # BGE中文嵌入模型
    }
}
```

## 支持的服务商示例

只需修改`base_url`和相应的`api_key`，即可支持以下服务商：

### OpenAI
```python
"embedding": {
    "type": "openai",
    "api_key": "sk-xxxx",
    "base_url": "https://api.openai.com/v1",
    "embedding_model": "text-embedding-ada-002"
}
```

### 硅流科技
```python
"embedding": {
    "type": "openai",
    "api_key": "sk-xxxx",
    "base_url": "https://api.siliconflow.cn/v1",
    "embedding_model": "BAAI/bge-large-zh-v1.5"
}
```

### 智谱AI
```python
"embedding": {
    "type": "openai",
    "api_key": "sk-xxxx",
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "embedding_model": "embedding-2"
}
```

### Azure OpenAI
```python
"embedding": {
    "type": "openai",
    "api_key": "xxxx",
    "base_url": "https://your-resource.openai.azure.com/openai/deployments/your-deployment-name",
    "api_version": "2023-05-15",
    "embedding_model": "text-embedding-ada-002"
}
```

## 使用示例

```python
from text2sql.base.factory import AsyncSmartSqlFactory

# 创建SmartSQL实例
config = {
    "embedding": {
        "type": "openai",
        "api_key": "sk-xxxx",
        "base_url": "https://api.siliconflow.cn/v1",
        "embedding_model": "BAAI/bge-large-zh-v1.5"
    },
    # 其他配置...
}

smart_sql = await AsyncSmartSqlFactory.create(config)

# 生成嵌入向量
embedding = await smart_sql.generate_embedding("SELECT * FROM users")
```

## 解耦的好处

虽然采用统一的OpenAI兼容接口，系统仍保持了大模型和嵌入模型的解耦设计：

1. 可以使用不同厂商的LLM和嵌入模型服务
2. 可以为不同任务选择性能和成本最优的模型
3. 配置灵活，适应不同场景需求