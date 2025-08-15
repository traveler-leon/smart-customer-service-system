# 智能记忆筛选使用指南

## 概述

智能记忆筛选是一个基于多因子综合评分的记忆检索算法，它综合考虑向量相似度、时间遗忘因子和专家评分等多个维度，返回最符合条件的TopK记忆。

## 核心算法

### 综合评分公式

```
composite_score = similarity_score × similarity_weight + 
                 time_score × time_weight + 
                 quality_score × quality_weight
```

### 三个关键因子

1. **向量相似度 (similarity_score)**
   - 基于语义向量的相似度匹配
   - 范围: 0-1，越高表示语义越相似
   - 由底层的向量搜索引擎提供

2. **时间遗忘因子 (time_score)**
   - 使用指数衰减模型: `exp(-time_diff / time_decay_days)`
   - 范围: 0-1，越新的记忆得分越高
   - 可配置时间衰减周期

3. **专家评分 (quality_score)**
   - 专家对回答质量的评分
   - 范围: 0-1，专家审核通过的记忆才会被筛选
   - 确保结果的质量和准确性

## API 使用方式

### 1. 底层调用 (memory_manager)

```python
from agents.airport_service.context_engineering.memory_manager import memory_manager

results = await memory_manager.get_smart_filtered_memories(
    query="机场餐厅推荐",
    user_id="user123",
    agent_name="机场知识问答子智能体",
    limit=10,
    similarity_weight=0.5,    # 相似度权重
    time_weight=0.2,          # 时间权重  
    quality_weight=0.3,       # 质量权重
    min_quality_score=0.7,    # 最低质量门槛
    time_decay_days=30        # 时间衰减周期(天)
)
```

### 2. 智能体集成层调用

```python
from agents.airport_service.context_engineering.agent_memory import AgentMemoryMixin

smart_memories = await AgentMemoryMixin.retrieve_smart_filtered_memories(
    user_id="user123",
    current_query="机场餐厅推荐",
    agent_name="机场知识问答子智能体",
    limit=5,
    similarity_weight=0.6,
    time_weight=0.2,
    quality_weight=0.2
)
```

### 3. HTTP API 调用

```bash
POST /memory/v1/conversations/smart-filter
Content-Type: application/json

{
    "query": "机场餐厅推荐",
    "user_id": "user123",
    "agent_name": "机场知识问答子智能体",
    "limit": 10,
    "similarity_weight": 0.5,
    "time_weight": 0.2,
    "quality_weight": 0.3,
    "min_quality_score": 0.7,
    "time_decay_days": 30
}
```

## 参数配置指南

### 权重配置策略

1. **重视准确性场景** (客服、医疗等)
   ```python
   similarity_weight=0.3
   time_weight=0.2  
   quality_weight=0.5  # 高质量权重
   ```

2. **重视时效性场景** (新闻、股价等)
   ```python
   similarity_weight=0.3
   time_weight=0.5     # 高时间权重
   quality_weight=0.2
   ```

3. **重视相似度场景** (文档搜索等)
   ```python
   similarity_weight=0.7  # 高相似度权重
   time_weight=0.15
   quality_weight=0.15
   ```

4. **均衡场景** (一般对话)
   ```python
   similarity_weight=0.4
   time_weight=0.3
   quality_weight=0.3
   ```

### 时间衰减周期设置

- **7天**: 适用于快速变化的信息
- **30天**: 适用于一般业务场景  
- **90天**: 适用于相对稳定的知识
- **365天**: 适用于长期有效的信息

### 质量门槛设置

- **0.9+**: 仅返回最高质量的记忆
- **0.8+**: 高质量记忆
- **0.7+**: 中等以上质量记忆
- **0.5+**: 包含中等质量记忆

## 返回数据结构

```python
{
    "memory_id": "mem_123",
    "user_id": "user123", 
    "query": "用户查询",
    "response": "智能体回复",
    "agent_name": "智能体名称",
    "expert_verified": True,
    "quality_score": 0.95,
    "created_at": "2024-01-01T12:00:00",
    
    # 评分详情
    "similarity_score": 0.85,
    "time_score": 0.92,
    "composite_score": 0.89,
    "expert_corrected": False,
    
    "score_breakdown": {
        "similarity": 0.85,
        "time_factor": 0.92,
        "quality": 0.95,
        "weights": {
            "similarity": 0.5,
            "time": 0.2,
            "quality": 0.3
        }
    }
}
```

## 最佳实践

### 1. 权重调优

- 根据业务场景测试不同权重组合
- 观察TopK结果的质量和相关性
- 可以A/B测试不同配置的效果

### 2. 质量管理

- 建立专家审核流程
- 定期review低质量的记忆
- 设置合适的质量门槛

### 3. 时间管理

- 根据信息更新频率设置衰减周期
- 定期清理过时的记忆
- 考虑业务的季节性特点

### 4. 性能优化

- 候选集通常设置为目标数量的3-5倍
- 合理设置最大限制避免性能问题
- 考虑缓存热门查询的结果

## 使用示例

运行演示程序查看完整示例:

```bash
python examples/smart_memory_filter_demo.py
```

## 常见问题

### Q: 权重不加起来等于1怎么办？
A: 系统会自动归一化权重，并记录warning日志。

### Q: 没有专家审核的记忆会被返回吗？
A: 不会，智能筛选只返回expert_verified=True的记忆。

### Q: 如何处理时间解析失败？
A: 系统会给予默认的中等时间得分(0.5)，确保不影响整体筛选。

### Q: 相似度搜索返回空结果怎么办？
A: 可能是查询条件过于严格，建议降低min_quality_score或扩大搜索范围。

## 扩展功能

### 自定义评分因子

如需添加更多评分维度(如用户反馈、点击率等)，可以扩展`get_smart_filtered_memories`方法:

```python
# 在memory_manager.py中扩展
custom_score = calculate_custom_factor(result)
composite_score = (
    similarity_score * similarity_weight +
    time_score * time_weight +
    quality_score * quality_weight +
    custom_score * custom_weight
)
```

这样就可以根据业务需求灵活扩展评分模型。
