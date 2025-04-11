"""
航班信息查询模块 - 使用LangGraph实现

支持：
- 航班参数提取
- 参数完整性检查
- 动态SQL生成
- 错误处理与重试
- 结果简洁格式化
"""

from agents.flight_info.graph import flight_info_graph

__all__ = ["flight_info_graph"] 