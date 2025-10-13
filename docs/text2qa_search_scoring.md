# text2qa 智能搜索与评分机制

## 概述

text2qa 模块现在实现了智能的搜索评分机制，包括时间衰减和分数阈值过滤，确保返回的结果既相关又新鲜。

## 核心特性

### 1. 简化的搜索接口

- **输入参数**：只需要 `query` 字符串
- **移除了** `tags` 参数，简化调用接口
- **精确匹配**：只搜索 `question` 字段，不搜索答案内容

### 2. 时间衰减机制

搜索结果会根据QA对的创建时间应用时间衰减：

- **衰减公式**：`final_score = base_score * (time_decay_factor ^ days_old)`
- **默认衰减因子**：0.8（每天分数乘以0.8）
- **目的**：确保新内容比旧内容更容易被搜索到

#### 时间衰减示例

假设 `time_decay_factor = 0.8`：

- **当天创建**的QA：分数 = 1.0 × (0.8^0) = 1.0
- **1天前**创建的QA：分数 = 1.0 × (0.8^1) = 0.8
- **3天前**创建的QA：分数 = 1.0 × (0.8^3) = 0.512
- **7天前**创建的QA：分数 = 1.0 × (0.8^7) = 0.210
- **30天前**创建的QA：分数 = 1.0 × (0.8^30) = 0.001

### 3. 分数阈值过滤

- **默认阈值**：0.1
- **过滤逻辑**：低于阈值的结果不会返回
- **返回空值**：如果最佳匹配分数仍低于阈值，返回 `None`

## 配置参数

### 初始化参数

```python
qa = await create_simple_qa(
    host="localhost",
    port=6379,
    db=2,
    score_threshold=0.1,      # 分数阈值
    time_decay_factor=0.8     # 时间衰减因子
)
```

### 环境变量配置

```bash
# Redis连接
export REDIS_HOST="localhost"
export REDIS_PORT=6379
export REDIS_QA_DB=2

# 搜索评分参数
export QA_SCORE_THRESHOLD=0.1
export QA_TIME_DECAY_FACTOR=0.8
```

## 使用示例

### 基本搜索

```python
from text2qa.simple_redis_qa import create_simple_qa

# 创建QA系统
qa = await create_simple_qa(
    score_threshold=0.1,
    time_decay_factor=0.8
)

# 搜索QA对
result = await qa.search_one("机器学习")
if result:
    print(f"找到匹配: {result['question']}")
    print(f"答案: {result['answer']}")
else:
    print("未找到满足条件的QA对")
```

### API调用

```python
import requests

# 搜索请求
response = requests.post("http://localhost:8000/simple-text2qa/search", 
                        json={"query": "Redis有什么优点"})

data = response.json()
if data["success"] and data["data"]:
    qa = data["data"]
    print(f"问题: {qa['question']}")
    print(f"答案: {qa['answer']}")
else:
    print("未找到匹配结果或分数低于阈值")
```

## 评分算法详解

### 1. 基础分数计算

使用Redis Search的真实相似度分数（BM25算法），通过 `Query.with_scores()` 获取：

```python
# 启用分数返回
query = Query("搜索词").with_scores()
results = await redis_client.ft(index_name).search(query)

# 获取每个结果的分数
for doc in results.docs:
    redis_score = doc.score  # Redis Search的相似度分数
```

### 2. 时间衰减计算

```python
def calculate_time_decay(created_at, current_time, decay_factor):
    """计算时间衰减"""
    time_diff = current_time - created_at
    days_old = time_diff / (24 * 3600)
    return decay_factor ** days_old
```

### 3. 最终分数

```python
final_score = redis_search_score * time_decay
```

**分数范围说明**：
- Redis Search分数：通常在 0.1 - 5.0 范围内
- 时间衰减：0.0 - 1.0（随时间递减）
- 最终分数：0.0 - 5.0（理论最大值）

### 4. 阈值过滤

```python
if final_score >= score_threshold:
    return qa_result
else:
    return None
```

## 推荐配置

### 不同场景的配置建议

#### 1. 新闻/资讯类QA
- `time_decay_factor`: 0.7-0.8（时效性要求高）
- `score_threshold`: 0.2-0.3（质量要求高）

#### 2. 技术文档QA
- `time_decay_factor`: 0.9-0.95（技术文档更新较慢）
- `score_threshold`: 0.1-0.15（覆盖面要求高）

#### 3. 常见问题FAQ
- `time_decay_factor`: 0.95-0.99（基本不变）
- `score_threshold`: 0.05-0.1（尽量提供答案）

## 性能优化

### 1. 搜索范围控制

- 默认获取前10个候选结果进行分数计算
- 可根据数据量调整候选结果数量

### 2. 缓存机制

搜索结果的时间衰减计算相对稳定，可以考虑添加缓存：

```python
# 可以缓存最近N分钟的搜索结果
cache_key = f"search:{query_hash}:{time_bucket}"
```

### 3. 批量分数计算

对于高频搜索，可以预计算时间衰减分数。

## 监控指标

### 关键指标

1. **搜索命中率**：返回结果的搜索占比
2. **平均返回分数**：监控分数分布
3. **时间衰减影响**：新旧内容的搜索比例
4. **阈值有效性**：被阈值过滤的结果比例

### 日志示例

```
INFO - 返回最佳匹配: 分数 0.156, 问题: '什么是机器学习？'
INFO - 最佳匹配分数 0.087 低于阈值 0.1，返回空结果
DEBUG - QA abc123: 最终分数 0.2340 (基础:1.0, 时间衰减:0.234, 年龄:5.2天)
```

## 注意事项

1. **时间同步**：确保所有服务器时间同步，避免时间衰减计算错误
2. **阈值调优**：根据实际数据分布调整阈值，避免过高导致无结果
3. **衰减因子**：根据业务特点选择合适的衰减速度
4. **数据清理**：定期清理分数过低的旧数据
5. **A/B测试**：通过对比测试确定最佳参数组合
