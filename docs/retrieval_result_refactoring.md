# 检索结果状态管理重构文档

## 重构背景

之前的 `AirportMainServiceState` 中关于检索结果的状态管理存在不一致的问题：
- 知识库检索使用 `kb_context_docs` 和 `kb_context_docs_maxscore`
- 专家QA检索使用 `qa` 和 `qa_images`
- 多个字段分散管理，不够统一和规范

## 重构方案

### 1. 新增统一的检索结果模型 `RetrievalResult`

在 `agents/airport_service/state.py` 中新增：

```python
class RetrievalResult(BaseModel):
    """统一的检索结果模型"""
    source: Literal["expert_qa", "knowledge_base", "none"]  # 检索来源类型
    content: Optional[str]  # 检索到的文本内容
    score: Optional[float]  # 检索结果的相似度分数
    images: Optional[List[str]]  # 相关图片列表（如果有）
    metadata: Optional[Dict]  # 额外的元数据信息
```

### 2. 状态定义简化

**重构前：**
```python
class AirportMainServiceState(MessagesState):
    kb_context_docs: Optional[str] = None
    kb_context_docs_maxscore: Optional[float] = None
    qa: Optional[str] = None
    qa_images: Optional[str] = None
    # ... 其他字段
```

**重构后：**
```python
class AirportMainServiceState(MessagesState):
    retrieval_result: Optional[RetrievalResult] = None  # 统一的检索结果
    # ... 其他字段
```

### 3. 检索函数返回值统一

**`agents/airport_service/tools/airport.py`** 中的检索函数：

- `airport_knowledge_query2docs_main()` - 完整版检索（包含专家QA和知识库）
- `airport_knowledge_query2docs()` - 简化版检索（仅知识库）

都统一返回 `RetrievalResult` 对象。

**重构前返回：**
```python
{
    "qa": "...",  # 或者
    "qa_images": [...],
    "kb_context_docs": "...",
    "kb_context_docs_maxscore": 0.8
}
```

**重构后返回：**
```python
RetrievalResult(
    source="expert_qa",  # 或 "knowledge_base" 或 "none"
    content="...",
    score=0.8,
    images=[...],
    metadata={...}
)
```

### 4. 节点代码更新

#### `airport_knowledge_search` 节点

```python
# 执行统一检索
retrieval_result = await airport_knowledge_query2docs_main(user_query, messages)

# 根据来源类型处理
if retrieval_result.source == "expert_qa":
    # 直接返回专家QA答案
    return {
        "messages": [AIMessage(content=retrieval_result.content)],
        "retrieval_result": retrieval_result
    }

return {"retrieval_result": retrieval_result}
```

#### `airport_knowledge_agent` 节点

```python
# 获取统一的检索结果
retrieval_result = state.get("retrieval_result")

# 如果是专家QA，已经在search节点返回，直接清空
if retrieval_result and retrieval_result.source == "expert_qa":
    return {"retrieval_result": None}

# 检查检索结果有效性
if not retrieval_result or retrieval_result.source == "none":
    return Command(goto="chitchat_node", update={"retrieval_result": None})

# 使用统一的content字段
context = retrieval_result.content
```

## 重构优势

### 1. **统一性**
- 所有检索来源（专家QA、知识库）使用同一个数据结构
- 减少状态字段数量，从 4 个字段降为 1 个字段

### 2. **可扩展性**
- 添加新的检索源（如FAQ、文档）只需增加 `source` 类型
- `metadata` 字段可以存储任何额外信息

### 3. **类型安全**
- 使用 Pydantic 模型，提供完整的类型检查
- `source` 字段使用 `Literal` 类型，确保值的正确性

### 4. **代码清晰**
- 检索结果的处理逻辑更清晰
- 通过 `source` 字段轻松判断检索来源
- 日志记录更加统一和可追踪

### 5. **维护性**
- 修改检索结果结构只需修改一个模型
- 减少了状态管理的复杂度

## 影响范围

本次重构影响以下文件：

1. **状态定义**
   - `agents/airport_service/state.py` - 添加 `RetrievalResult` 模型，更新所有 State 类

2. **检索工具**
   - `agents/airport_service/tools/airport.py` - 更新返回值类型

3. **处理节点**
   - `agents/airport_service/main_nodes/airport.py` - 更新检索和处理逻辑
   - `agents/airport_service/problems_recommend_nodes/question_recommend.py` - 更新问题推荐节点

4. **状态类**
   - `AirportMainServiceState` - 主服务状态
   - `BusinessRecommendState` - 商业推荐状态
   - `QuestionRecommendState` - 问题推荐状态

## 使用示例

### 访问检索结果

```python
retrieval_result = state.get("retrieval_result")

if retrieval_result:
    print(f"来源: {retrieval_result.source}")
    print(f"内容: {retrieval_result.content}")
    print(f"分数: {retrieval_result.score}")
    
    if retrieval_result.images:
        print(f"图片: {retrieval_result.images}")
    
    if retrieval_result.metadata:
        print(f"元数据: {retrieval_result.metadata}")
```

### 判断检索来源

```python
if retrieval_result.source == "expert_qa":
    # 处理专家QA结果
    pass
elif retrieval_result.source == "knowledge_base":
    # 处理知识库结果
    pass
else:  # "none"
    # 无检索结果，转向其他处理
    pass
```

## 向后兼容性

本次重构为**破坏性变更**，旧的字段已完全移除：
- ❌ `kb_context_docs`
- ❌ `kb_context_docs_maxscore`
- ❌ `qa`
- ❌ `qa_images`

所有引用这些字段的代码都已更新为使用新的 `retrieval_result` 字段。

## 测试建议

重构后建议重点测试以下场景：

1. **专家QA命中**
   - 验证专家QA结果是否正确返回
   - 验证图片信息是否正确传递

2. **知识库检索**
   - 验证知识库检索结果是否正确
   - 验证分数阈值判断是否正常

3. **无结果情况**
   - 验证无结果时是否正确转向闲聊节点

4. **问题推荐**
   - 验证问题推荐功能是否正常工作

## 总结

本次重构通过引入统一的 `RetrievalResult` 模型，大大简化了检索结果的状态管理，提高了代码的可维护性、可扩展性和类型安全性。这是一次重要的架构优化，为后续功能扩展打下了良好的基础。

