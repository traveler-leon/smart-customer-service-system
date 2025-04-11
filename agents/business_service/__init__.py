"""
业务办理模块 - 使用LangGraph实现

支持：
- 业务类型智能识别
- 业务参数提取与验证
- 多轮对话收集参数
- 业务确认流程
- API调用与错误处理
- 友好结果展示
"""

from agents.business_service.graph import business_service_graph

__all__ = ["business_service_graph"] 