"""
知识问答模块 - 使用LangGraph实现

支持：
- 问题完整性分析
- 针对不完整问题的澄清
- 相关性检测和提问引导
- 粒度匹配检查
- 简洁回答生成
- 多样化语气风格
"""

from agents.knowledge_qa.graph import knowledge_qa_graph

__all__ = ["knowledge_qa_graph"] 