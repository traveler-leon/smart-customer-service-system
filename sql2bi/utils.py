"""
SQL2BI实用工具函数
"""

import random
from typing import List, Dict, Any, Optional
import json
from .chart_converter import SQLData, convert_sql_to_chart

def sql_result_to_chart(
    sql: str, 
    data: List[Dict[str, Any]], 
    column_names: Optional[List[str]] = None,
    excluded_types: Optional[List[str]] = None,
    preferred_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    从SQL和查询结果直接生成图表配置
    
    Args:
        sql: SQL查询语句
        data: 查询结果数据 (行列表)
        column_names: 列名列表(可选，如果data中没有提供)
        excluded_types: 要排除的图表类型列表(可选)
        preferred_types: 偏好的图表类型列表(可选)
        
    Returns:
        ECharts配置选项和图表信息
    """
    # 创建SQLData对象
    sql_data = SQLData(sql, data, column_names)
    
    # 转换为图表配置
    return convert_sql_to_chart(
        sql_data, 
        excluded_types=excluded_types, 
        preferred_types=preferred_types
    )

def chart_config_to_json(chart_config: Dict[str, Any]) -> str:
    """
    将图表配置转换为JSON字符串
    
    Args:
        chart_config: 图表配置字典
        
    Returns:
        JSON格式的图表配置字符串
    """
    return json.dumps(chart_config, ensure_ascii=False, indent=2)

def get_available_chart_types() -> Dict[str, List[Dict[str, Any]]]:
    """
    获取所有可用的图表类型和子类型
    
    Returns:
        图表类型和子类型列表
    """
    from .chart_types import CHART_TYPES
    return CHART_TYPES

def get_random_chart_type() -> Dict[str, Any]:
    """
    随机获取一个图表类型和子类型
    
    Returns:
        随机选择的图表类型信息
    """
    from .chart_types import CHART_TYPES
    
    # 随机选择图表类型
    chart_type = random.choice(list(CHART_TYPES.keys()))
    
    # 随机选择子类型
    subtypes = CHART_TYPES[chart_type]
    chart_subtype = random.choice(subtypes)
    
    return {
        'type': chart_type,
        'subtype': chart_subtype['subtype'],
        'name': chart_subtype['name'],
        'description': chart_subtype['description']
    } 