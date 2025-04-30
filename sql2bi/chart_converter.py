import random
import re
from typing import List, Dict, Any, Tuple, Optional, Union
import pandas as pd
import numpy as np
import json

from .chart_types import CHART_TYPES, COLOR_THEMES, DATA_FEATURE_RECOMMENDATIONS


class SQLData:
    """SQL数据和SQL语句的封装类"""
    
    def __init__(self, sql: str, data: List[Dict[str, Any]], column_names: Optional[List[str]] = None):
        """
        初始化SQL数据
        
        Args:
            sql: SQL查询语句
            data: 查询结果数据，列表中的每个字典代表一行数据
            column_names: 列名列表，如果为None，则从data中提取
        """
        self.sql = sql
        self.data = data
        
        # 如果没有提供列名，则从数据中提取
        if column_names is None and data and len(data) > 0:
            self.column_names = list(data[0].keys())
        else:
            self.column_names = column_names or []
            
        # 将数据转换为pandas DataFrame以便于分析
        self.df = pd.DataFrame(data)
    
    def get_data_types(self) -> Dict[str, str]:
        """
        分析每一列的数据类型
        
        Returns:
            字典，键为列名，值为数据类型（'numeric', 'categorical', 'temporal', 'text'）
        """
        if self.df.empty:
            return {}
            
        data_types = {}
        for column in self.column_names:
            if column not in self.df.columns:
                continue
                
            # 检查是否为数值型
            if pd.api.types.is_numeric_dtype(self.df[column]):
                data_types[column] = 'numeric'
            # 检查是否为时间型
            elif pd.api.types.is_datetime64_dtype(self.df[column]) or self._is_date_string(self.df[column]):
                data_types[column] = 'temporal'
            # 检查是否为类别型（判断唯一值数量）
            elif self.df[column].nunique() < min(10, len(self.df) / 3):
                data_types[column] = 'categorical'
            # 其他视为文本型
            else:
                data_types[column] = 'text'
                
        return data_types
    
    def _is_date_string(self, series: pd.Series) -> bool:
        """
        检查一个字符串系列是否可能是日期
        """
        # 简单的日期模式匹配
        date_patterns = [
            r'\d{4}-\d{1,2}-\d{1,2}',  # yyyy-mm-dd
            r'\d{1,2}/\d{1,2}/\d{4}',  # mm/dd/yyyy
            r'\d{4}年\d{1,2}月\d{1,2}日'  # yyyy年mm月dd日
        ]
        
        # 检查前10个非空值
        sample = series.dropna().head(10)
        if len(sample) == 0:
            return False
            
        # 尝试匹配日期模式
        for pattern in date_patterns:
            if all(isinstance(val, str) and re.match(pattern, val) for val in sample):
                return True
                
        # 尝试解析为日期
        try:
            pd.to_datetime(sample)
            return True
        except:
            return False
            
    def analyze_sql(self) -> Dict[str, Any]:
        """
        分析SQL语句，提取有用信息
        
        Returns:
            包含SQL分析结果的字典
        """
        sql_lower = self.sql.lower()
        
        # 提取SELECT的列
        select_pattern = r'select\s+(.*?)\s+from'
        select_match = re.search(select_pattern, sql_lower)
        selected_columns = []
        if select_match:
            cols = select_match.group(1).split(',')
            selected_columns = [col.strip() for col in cols]
        
        # 检查是否包含聚合函数
        aggregation_funcs = ['count', 'sum', 'avg', 'min', 'max']
        has_aggregation = any(func in sql_lower for func in aggregation_funcs)
        
        # 检查是否有GROUP BY
        has_group_by = 'group by' in sql_lower
        group_by_cols = []
        if has_group_by:
            group_pattern = r'group by\s+(.*?)(?:having|order by|limit|$)'
            group_match = re.search(group_pattern, sql_lower)
            if group_match:
                group_by_cols = [col.strip() for col in group_match.group(1).split(',')]
        
        # 检查是否有ORDER BY
        has_order_by = 'order by' in sql_lower
        
        return {
            'selected_columns': selected_columns,
            'has_aggregation': has_aggregation,
            'has_group_by': has_group_by,
            'group_by_columns': group_by_cols,
            'has_order_by': has_order_by
        }


def _get_suitable_chart_types(sql_data: SQLData) -> List[Dict[str, Any]]:
    """
    根据SQL和数据特性，确定合适的图表类型和子类型
    
    Args:
        sql_data: SQLData对象
    
    Returns:
        合适的图表类型和配置列表
    """
    suitable_charts = []
    data_types = sql_data.get_data_types()
    sql_analysis = sql_data.analyze_sql()
    
    # 数据行数
    row_count = len(sql_data.data)
    # 数据列数
    col_count = len(sql_data.column_names)
    
    # 找出数值型列
    numeric_cols = [col for col, type_ in data_types.items() if type_ == 'numeric']
    # 找出类别型列
    categorical_cols = [col for col, type_ in data_types.items() if type_ == 'categorical']
    # 找出时间型列
    temporal_cols = [col for col, type_ in data_types.items() if type_ == 'temporal']
    
    # 确定数据特征
    data_features = []
    
    # 时间序列数据
    if len(temporal_cols) >= 1 and len(numeric_cols) >= 1:
        data_features.append("time_series")
    
    # 类别比较数据
    if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
        data_features.append("category_comparison")
    
    # 分布数据
    if len(numeric_cols) >= 1:
        data_features.append("distribution")
    
    # 构成关系数据
    if sql_analysis['has_group_by'] and len(numeric_cols) >= 1:
        data_features.append("composition")
    
    # 相关性分析数据
    if len(numeric_cols) >= 2:
        data_features.append("correlation")
    
    # 排名数据
    if len(categorical_cols) >= 1 and len(numeric_cols) >= 1 and sql_analysis['has_order_by']:
        data_features.append("ranking")
    
    # 多维度数据
    if len(numeric_cols) >= 3:
        data_features.append("multi_dimension")
    
    # 基于数据特征推荐图表
    recommended_charts = set()
    for feature in data_features:
        if feature in DATA_FEATURE_RECOMMENDATIONS:
            recommended_charts.update(DATA_FEATURE_RECOMMENDATIONS[feature])
    
    # 表格类型添加，不再放大权重
    for table_type in CHART_TYPES.get('table', []):
        suitable_charts.append({
            'type': 'table',
            'subtype': table_type['subtype'],
            'name': table_type['name'],
            'suitability': table_type['suitability_score'],  # 移除放大系数
            'columns': sql_data.column_names
        })
    
    # 折线图
    if len(numeric_cols) >= 1 and (len(temporal_cols) >= 1 or len(categorical_cols) >= 1):
        x_axis = temporal_cols[0] if temporal_cols else categorical_cols[0]
        
        # 计算基础适用性
        base_suitability = 8 if temporal_cols else 6
        
        # 添加各种折线图子类型
        for line_type in CHART_TYPES.get('line', []):
            # 不为时间序列数据时，跳过一些不太适合的子类型
            if not temporal_cols and line_type['subtype'] in ['area_line', 'stacked_area_line']:
                continue
                
            for y_col in numeric_cols:
                suitable_charts.append({
                    'type': 'line',
                    'subtype': line_type['subtype'],
                    'name': line_type['name'],
                    'suitability': base_suitability * line_type['suitability_score'],
                    'x_axis': x_axis,
                    'y_axis': y_col
                })
    
    # 柱状图/条形图
    if len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
        for category_col in categorical_cols:
            # 检查类别数量
            unique_categories = sql_data.df[category_col].nunique()
            
            for bar_type in CHART_TYPES.get('bar', []):
                # 根据类别数量调整适用性
                adjusted_suitability = bar_type['suitability_score']
                
                # 类别较多时，水平条形图更适合
                if unique_categories > 10 and 'horizontal' in bar_type['subtype']:
                    adjusted_suitability += 2
                # 类别较少时，垂直柱状图更适合
                elif unique_categories <= 10 and 'horizontal' not in bar_type['subtype']:
                    adjusted_suitability += 1
                
                # 跳过不适合当前数据的子类型
                if 'stacked' in bar_type['subtype'] and len(categorical_cols) < 2:
                    continue
                if bar_type['subtype'] == 'bar_line' and (len(numeric_cols) < 2 or unique_categories > 10):
                    continue
                
                for value_col in numeric_cols:
                    chart_info = {
                        'type': 'bar',
                        'subtype': bar_type['subtype'],
                        'name': bar_type['name'],
                        'suitability': adjusted_suitability * 10,
                        'category': category_col,
                        'value': value_col
                    }
                    
                    # 对于堆叠类型，需要额外的堆叠字段
                    if 'stacked' in bar_type['subtype'] and len(categorical_cols) >= 2:
                        for stack_col in [c for c in categorical_cols if c != category_col]:
                            chart_info_with_stack = chart_info.copy()
                            chart_info_with_stack['stack'] = stack_col
                            suitable_charts.append(chart_info_with_stack)
                    else:
                        suitable_charts.append(chart_info)
    
    # 饼图
    if len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
        for category_col in categorical_cols:
            # 饼图更适合少量类别
            unique_categories = sql_data.df[category_col].nunique()
            
            if 2 <= unique_categories <= 15:  # 扩大一些可接受的类别数范围
                for pie_type in CHART_TYPES.get('pie', []):
                    # 调整适用性评分
                    adjusted_suitability = pie_type['suitability_score']
                    
                    # 类别数量对不同饼图子类型的影响
                    if unique_categories <= 7:
                        adjusted_suitability += 1  # 少量类别更适合基础饼图
                    elif pie_type['subtype'] in ['rose', 'nightingale']:
                        adjusted_suitability += 1  # 玫瑰图更适合处理较多类别
                    
                    for value_col in numeric_cols:
                        suitable_charts.append({
                            'type': 'pie',
                            'subtype': pie_type['subtype'],
                            'name': pie_type['name'],
                            'suitability': adjusted_suitability * 10,
                            'category': category_col,
                            'value': value_col
                        })
    
    # 散点图
    if len(numeric_cols) >= 2:
        for scatter_type in CHART_TYPES.get('scatter', []):
            for i, x_col in enumerate(numeric_cols):
                for y_col in numeric_cols[i+1:]:
                    chart_info = {
                        'type': 'scatter',
                        'subtype': scatter_type['subtype'],
                        'name': scatter_type['name'],
                        'suitability': scatter_type['suitability_score'] * 10,
                        'x_axis': x_col,
                        'y_axis': y_col
                    }
                    
                    # 对于气泡图，需要第三个数值维度
                    if scatter_type['subtype'] == 'bubble' and len(numeric_cols) >= 3:
                        for size_col in [col for col in numeric_cols if col != x_col and col != y_col]:
                            bubble_info = chart_info.copy()
                            bubble_info['size_field'] = size_col
                            suitable_charts.append(bubble_info)
                    else:
                        suitable_charts.append(chart_info)
    
    # 热力图
    if len(categorical_cols) >= 2 and len(numeric_cols) >= 1:
        for heatmap_type in CHART_TYPES.get('heatmap', []):
            for x_cat in categorical_cols:
                for y_cat in [c for c in categorical_cols if c != x_cat]:
                    for value_col in numeric_cols:
                        # 日历热力图需要时间列
                        if heatmap_type['subtype'] == 'calendar_heatmap' and not temporal_cols:
                            continue
                            
                        suitable_charts.append({
                            'type': 'heatmap',
                            'subtype': heatmap_type['subtype'],
                            'name': heatmap_type['name'],
                            'suitability': heatmap_type['suitability_score'] * 10,
                            'x_axis': x_cat,
                            'y_axis': y_cat,
                            'value': value_col
                        })
    
    # 雷达图
    if len(numeric_cols) >= 3 and len(categorical_cols) >= 1:
        for radar_type in CHART_TYPES.get('radar', []):
            for category_col in categorical_cols:
                if sql_data.df[category_col].nunique() <= 10:  # 限制类别数量
                    suitable_charts.append({
                        'type': 'radar',
                        'subtype': radar_type['subtype'],
                        'name': radar_type['name'],
                        'suitability': radar_type['suitability_score'] * 10,
                        'category': category_col,
                        'indicators': numeric_cols[:6]  # 最多取6个指标
                    })
    
    # 箱线图
    if len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
        for boxplot_type in CHART_TYPES.get('boxplot', []):
            for category_col in categorical_cols:
                for value_col in numeric_cols:
                    suitable_charts.append({
                        'type': 'boxplot',
                        'subtype': boxplot_type['subtype'],
                        'name': boxplot_type['name'],
                        'suitability': boxplot_type['suitability_score'] * 10,
                        'category': category_col,
                        'value': value_col
                    })
    
    # 漏斗图
    if len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
        for funnel_type in CHART_TYPES.get('funnel', []):
            for category_col in categorical_cols:
                # 漏斗图适合展示转化过程，类别数不宜太多或太少
                if 3 <= sql_data.df[category_col].nunique() <= 10:
                    for value_col in numeric_cols:
                        suitable_charts.append({
                            'type': 'funnel',
                            'subtype': funnel_type['subtype'],
                            'name': funnel_type['name'],
                            'suitability': funnel_type['suitability_score'] * 10,
                            'category': category_col,
                            'value': value_col
                        })
    
    # 树图
    if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
        for treemap_type in CHART_TYPES.get('treemap', []):
            for category_col in categorical_cols:
                for value_col in numeric_cols:
                    suitable_charts.append({
                        'type': 'treemap',
                        'subtype': treemap_type['subtype'],
                        'name': treemap_type['name'],
                        'suitability': treemap_type['suitability_score'] * 10,
                        'category': category_col,
                        'value': value_col
                    })
    
    # 仪表盘 - 适合单个数值的展示
    if len(numeric_cols) >= 1:
        for gauge_type in CHART_TYPES.get('gauge', []):
            # 仪表盘通常用于展示单个指标，如完成率、进度等
            # 为每个数值列创建一个仪表盘选项
            for value_col in numeric_cols:
                suitable_charts.append({
                    'type': 'gauge',
                    'subtype': gauge_type['subtype'],
                    'name': gauge_type['name'],
                    'suitability': gauge_type['suitability_score'] * 8,  # 稍降低权重，因为仪表盘通常不是首选
                    'value': value_col
                })
    
    # 桑基图 - 需要源和目标两个类别字段
    if len(categorical_cols) >= 2 and len(numeric_cols) >= 1:
        for sankey_type in CHART_TYPES.get('sankey', []):
            for source_col in categorical_cols:
                for target_col in [c for c in categorical_cols if c != source_col]:
                    for value_col in numeric_cols:
                        suitable_charts.append({
                            'type': 'sankey',
                            'subtype': sankey_type['subtype'],
                            'name': sankey_type['name'],
                            'suitability': sankey_type['suitability_score'] * 8,
                            'source': source_col,
                            'target': target_col,
                            'value': value_col
                        })
    
    # 如果图表类型太少，增加一些次优选择的权重
    if len(suitable_charts) < 5:
        for chart in suitable_charts:
            if chart['type'] not in ['table', 'line', 'bar', 'pie']:
                chart['suitability'] *= 1.5  # 增加较少见图表类型的权重
    
    return suitable_charts


def _generate_echarts_option(chart_info: Dict[str, Any], sql_data: SQLData) -> Dict[str, Any]:
    """
    根据图表类型生成ECharts配置选项
    
    Args:
        chart_info: 图表类型和配置信息
        sql_data: SQLData对象
    
    Returns:
        ECharts配置选项
    """
    chart_type = chart_info['type']
    df = sql_data.df
    
    # 基本配置
    option = {
        'title': {
            'text': f'数据分析图表'
        },
        'tooltip': {
            'trigger': 'axis',
            'axisPointer': {'type': 'shadow'}
        },
        'legend': {},
        'color': [
            '#5470c6', '#91cc75', '#fac858', '#ee6666', 
            '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'
        ]
    }
    
    if chart_type == 'table':
        # 表格特殊处理
        return {
            'type': 'table',
            'columns': [{'title': col, 'dataIndex': col} for col in chart_info['columns']],
            'dataSource': sql_data.data
        }
    
    elif chart_type == 'line':
        x_axis = chart_info['x_axis']
        y_axis = chart_info['y_axis']
        
        # 按X轴排序数据
        if pd.api.types.is_numeric_dtype(df[x_axis]):
            sorted_df = df.sort_values(x_axis)
        else:
            sorted_df = df
        
        option.update({
            'xAxis': {
                'type': 'category',
                'data': sorted_df[x_axis].tolist(),
                'name': x_axis
            },
            'yAxis': {
                'type': 'value',
                'name': y_axis
            },
            'series': [{
                'name': y_axis,
                'type': 'line',
                'data': sorted_df[y_axis].tolist(),
                'smooth': True
            }]
        })
    
    elif chart_type == 'bar':
        category = chart_info['category']
        value = chart_info['value']
        
        # 聚合数据
        agg_data = df.groupby(category)[value].sum().reset_index()
        
        option.update({
            'xAxis': {
                'type': 'category',
                'data': agg_data[category].tolist(),
                'name': category
            },
            'yAxis': {
                'type': 'value',
                'name': value
            },
            'series': [{
                'name': value,
                'type': 'bar',
                'data': agg_data[value].tolist()
            }]
        })
    
    elif chart_type == 'pie':
        category = chart_info['category']
        value = chart_info['value']
        
        # 聚合数据
        agg_data = df.groupby(category)[value].sum().reset_index()
        
        pie_data = [{'name': str(row[category]), 'value': float(row[value])} 
                   for _, row in agg_data.iterrows()]
        
        option.update({
            'series': [{
                'name': value,
                'type': 'pie',
                'radius': '60%',
                'data': pie_data,
                'emphasis': {
                    'itemStyle': {
                        'shadowBlur': 10,
                        'shadowOffsetX': 0,
                        'shadowColor': 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        })
    
    elif chart_type == 'scatter':
        x_axis = chart_info['x_axis']
        y_axis = chart_info['y_axis']
        
        scatter_data = [[float(row[x_axis]), float(row[y_axis])] 
                       for _, row in df.iterrows() if pd.notna(row[x_axis]) and pd.notna(row[y_axis])]
        
        option.update({
            'xAxis': {
                'type': 'value',
                'name': x_axis
            },
            'yAxis': {
                'type': 'value',
                'name': y_axis
            },
            'series': [{
                'name': f'{x_axis} vs {y_axis}',
                'type': 'scatter',
                'data': scatter_data,
                'symbolSize': 12
            }]
        })
    
    elif chart_type == 'stacked_bar':
        category = chart_info['category']
        stack = chart_info['stack']
        value = chart_info['value']
        
        # 聚合数据
        agg_data = df.pivot_table(index=category, columns=stack, values=value, aggfunc='sum').fillna(0)
        
        categories = agg_data.index.tolist()
        stacks = agg_data.columns.tolist()
        
        series = []
        for stack_val in stacks:
            series.append({
                'name': str(stack_val),
                'type': 'bar',
                'stack': 'total',
                'emphasis': {'focus': 'series'},
                'data': agg_data[stack_val].tolist()
            })
        
        option.update({
            'legend': {'data': [str(s) for s in stacks]},
            'xAxis': {
                'type': 'category',
                'data': categories,
                'name': category
            },
            'yAxis': {
                'type': 'value',
                'name': value
            },
            'series': series
        })
    
    elif chart_type == 'heatmap':
        x_axis = chart_info['x_axis']
        y_axis = chart_info['y_axis']
        value = chart_info['value']
        
        # 聚合数据
        agg_data = df.pivot_table(index=y_axis, columns=x_axis, values=value, aggfunc='mean').fillna(0)
        
        x_categories = agg_data.columns.tolist()
        y_categories = agg_data.index.tolist()
        
        # 准备热力图数据
        data = []
        for i, y_val in enumerate(y_categories):
            for j, x_val in enumerate(x_categories):
                data.append([j, i, float(agg_data.loc[y_val, x_val])])
        
        option.update({
            'tooltip': {
                'position': 'top'
            },
            'xAxis': {
                'type': 'category',
                'data': [str(x) for x in x_categories],
                'splitArea': {'show': True},
                'name': x_axis
            },
            'yAxis': {
                'type': 'category',
                'data': [str(y) for y in y_categories],
                'splitArea': {'show': True},
                'name': y_axis
            },
            'visualMap': {
                'min': 0,
                'max': agg_data.values.max(),
                'calculable': True,
                'orient': 'horizontal',
                'left': 'center',
                'bottom': '15%'
            },
            'series': [{
                'name': value,
                'type': 'heatmap',
                'data': data,
                'label': {'show': True},
                'emphasis': {
                    'itemStyle': {
                        'shadowBlur': 10,
                        'shadowColor': 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        })
    
    elif chart_type == 'radar':
        category = chart_info['category']
        indicators = chart_info['indicators']
        
        # 准备雷达图指标
        radar_indicators = [{'name': ind, 'max': df[ind].max() * 1.2} for ind in indicators]
        
        # 按类别聚合数据
        categories = df[category].unique().tolist()
        series_data = []
        
        for cat in categories:
            cat_data = df[df[category] == cat]
            values = [cat_data[ind].mean() for ind in indicators]
            series_data.append({
                'name': str(cat),
                'value': values
            })
        
        option.update({
            'radar': {
                'indicator': radar_indicators
            },
            'series': [{
                'name': '雷达图',
                'type': 'radar',
                'data': series_data
            }]
        })
    
    elif chart_type == 'boxplot':
        category = chart_info['category']
        value = chart_info['value']
        
        # 准备箱线图数据
        categories = df[category].unique().tolist()
        boxplot_data = []
        
        for cat in categories:
            cat_values = df[df[category] == cat][value].dropna().tolist()
            if cat_values:
                boxplot_data.append(cat_values)
        
        option.update({
            'xAxis': {
                'type': 'category',
                'data': [str(c) for c in categories],
                'name': category
            },
            'yAxis': {
                'type': 'value',
                'name': value
            },
            'series': [{
                'name': value,
                'type': 'boxplot',
                'data': boxplot_data
            }]
        })
    
    elif chart_type == 'funnel':
        category = chart_info['category']
        value = chart_info['value']
        
        # 聚合数据
        agg_data = df.groupby(category)[value].sum().reset_index()
        
        # 按值排序
        agg_data = agg_data.sort_values(value, ascending=False)
        
        funnel_data = [{'name': str(row[category]), 'value': float(row[value])} 
                      for _, row in agg_data.iterrows()]
        
        option.update({
            'series': [{
                'name': value,
                'type': 'funnel',
                'data': funnel_data,
                'label': {
                    'position': 'inside',
                    'formatter': '{b} ({c})',
                    'color': '#fff'
                }
            }]
        })
    
    elif chart_type == 'treemap':
        category = chart_info['category']
        value = chart_info['value']
        
        # 聚合数据
        agg_data = df.groupby(category)[value].sum().reset_index()
        
        treemap_data = [{'name': str(row[category]), 'value': float(row[value])} 
                       for _, row in agg_data.iterrows()]
        
        option.update({
            'series': [{
                'name': value,
                'type': 'treemap',
                'data': treemap_data
            }]
        })
    
    return option


def _generate_enhanced_echarts_option(chart_info: Dict[str, Any], sql_data: SQLData, 
                               color_theme: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据图表类型生成增强版的ECharts配置选项
    
    Args:
        chart_info: 图表类型和配置信息
        sql_data: SQLData对象
        color_theme: 配色方案
    
    Returns:
        增强版的ECharts配置选项
    """
    chart_type = chart_info['type']
    chart_subtype = chart_info.get('subtype', 'basic')
    df = sql_data.df
    
    # 设置随机标题
    chart_titles = [
        '数据分析结果', '数据可视化', '数据趋势展示', 
        '数据洞察', '统计分析图表', '数据概览'
    ]
    
    # 基本配置
    option = {
        'title': {
            'text': random.choice(chart_titles),
            'left': 'center',
            'top': 10,
            'textStyle': {
                'fontSize': 18
            }
        },
        'tooltip': {
            'trigger': 'axis',
            'axisPointer': {'type': 'shadow'}
        },
        'legend': {
            'bottom': 10,
            'left': 'center'
        },
        'color': color_theme['colors'],
        'animation': True,
        'animationDuration': 1000,
        'animationEasing': random.choice(['cubicOut', 'elasticOut', 'bounceOut']),
    }
    
    # 表格类型
    if chart_type == 'table':
        # 表格特殊处理
        table_config = {
            'type': 'table',
            'columns': [{'title': col, 'dataIndex': col} for col in chart_info['columns']],
            'dataSource': sql_data.data
        }
        
        # 条件格式表格
        if chart_subtype == 'conditional_table':
            # 找出数值列进行条件格式化
            numeric_cols = []
            for column in chart_info['columns']:
                if column in sql_data.df.columns and pd.api.types.is_numeric_dtype(sql_data.df[column]):
                    numeric_cols.append(column)
            
            if numeric_cols:
                table_config['conditional_columns'] = numeric_cols
                table_config['conditional_type'] = 'gradient'
                table_config['conditional_palette'] = color_theme['colors'][:3]
        
        # 热力表格
        elif chart_subtype == 'heatmap_table':
            table_config['heatmap'] = True
            table_config['heatmap_palette'] = color_theme['colors'][1:4]
            
        return table_config

    # 折线图
    elif chart_type == 'line':
        x_axis = chart_info['x_axis']
        y_axis = chart_info['y_axis']
        
        # 按X轴排序数据
        if pd.api.types.is_numeric_dtype(df[x_axis]):
            sorted_df = df.sort_values(x_axis)
        else:
            sorted_df = df
        
        option.update({
            'xAxis': {
                'type': 'category',
                'data': sorted_df[x_axis].tolist(),
                'name': x_axis,
                'nameLocation': 'middle',
                'nameGap': 30,
                'axisLine': {
                    'lineStyle': {
                        'color': '#333'
                    }
                },
                'axisLabel': {
                    'rotate': 0
                }
            },
            'yAxis': {
                'type': 'value',
                'name': y_axis,
                'nameLocation': 'middle',
                'nameGap': 40,
                'axisLine': {
                    'show': True,
                    'lineStyle': {
                        'color': '#333'
                    }
                },
                'splitLine': {
                    'show': True,
                    'lineStyle': {
                        'type': 'dashed'
                    }
                }
            },
            'grid': {
                'left': '5%',
                'right': '5%',
                'bottom': '15%',
                'top': '15%',
                'containLabel': True
            },
            'dataZoom': [
                {
                    'type': 'inside',
                    'start': 0,
                    'end': 100
                },
                {
                    'type': 'slider',
                    'show': True,
                    'start': 0,
                    'end': 100,
                    'height': 20,
                    'bottom': 5
                }
            ]
        })
        
        # 基础折线图
        series_config = {
            'name': y_axis,
            'type': 'line',
            'data': sorted_df[y_axis].tolist(),
            'emphasis': {
                'focus': 'series'
            },
            'markPoint': {
                'data': [
                    {'type': 'max', 'name': '最大值'},
                    {'type': 'min', 'name': '最小值'}
                ]
            }
        }
        
        # 根据子类型调整配置
        if chart_subtype == 'smooth_line':
            series_config['smooth'] = True
            
        elif chart_subtype == 'step_line':
            series_config['step'] = 'middle'
            series_config['smooth'] = False
            
        elif chart_subtype == 'area_line':
            series_config['areaStyle'] = {
                'opacity': 0.3
            }
            series_config['smooth'] = True
            
        elif chart_subtype == 'stacked_area_line':
            # 需要多条线才能显示堆叠效果，可能需要使用分组
            series_config['areaStyle'] = {
                'opacity': 0.5
            }
            series_config['stack'] = 'Total'
            series_config['smooth'] = True
            
        elif chart_subtype == 'gradient_area_line':
            series_config['areaStyle'] = {
                'color': {
                    'type': 'linear',
                    'x': 0,
                    'y': 0,
                    'x2': 0,
                    'y2': 1,
                    'colorStops': [
                        {'offset': 0, 'color': color_theme['colors'][0]},
                        {'offset': 1, 'color': 'rgba(255, 255, 255, 0.1)'}
                    ]
                }
            }
            series_config['smooth'] = True
            series_config['lineStyle'] = {
                'width': 3
            }
        
        option['series'] = [series_config]
    
    # 柱状图/条形图
    elif chart_type == 'bar':
        category = chart_info['category']
        value = chart_info['value']
        
        # 聚合数据
        agg_data = df.groupby(category)[value].sum().reset_index()
        
        # 水平条形图与垂直柱状图差异配置
        is_horizontal = 'horizontal' in chart_subtype
        
        # 设置坐标轴
        x_axis_config = {
            'type': 'category',
            'data': agg_data[category].tolist(),
            'name': category,
            'nameLocation': 'middle',
            'nameGap': 30,
            'axisLabel': {
                'interval': 0,
                'rotate': 0 if is_horizontal else 30
            }
        }
        
        y_axis_config = {
            'type': 'value',
            'name': value,
            'nameLocation': 'middle',
            'nameGap': 40,
            'splitLine': {
                'show': True,
                'lineStyle': {
                    'type': 'dashed'
                }
            }
        }
        
        if is_horizontal:
            option['yAxis'] = x_axis_config
            option['xAxis'] = y_axis_config
        else:
            option['xAxis'] = x_axis_config
            option['yAxis'] = y_axis_config
        
        # 设置图表网格
        option['grid'] = {
            'left': '5%',
            'right': '5%',
            'bottom': '15%',
            'top': '15%',
            'containLabel': True
        }
        
        # 基础系列配置
        series_config = {
            'name': value,
            'type': 'bar',
            'data': agg_data[value].tolist(),
            'emphasis': {
                'focus': 'series'
            },
            'markPoint': {
                'data': [
                    {'type': 'max', 'name': '最大值'},
                ]
            },
            'label': {
                'show': True,
                'position': 'outside' if is_horizontal else 'top'
            }
        }
        
        # 根据子类型调整配置
        if chart_subtype in ['stacked_bar', 'stacked_horizontal_bar']:
            if 'stack' in chart_info:
                stack_col = chart_info['stack']
                
                # 重新聚合数据以支持堆叠
                agg_data = df.pivot_table(
                    index=category, 
                    columns=stack_col, 
                    values=value, 
                    aggfunc='sum'
                ).fillna(0)
                
                categories = agg_data.index.tolist()
                stacks = agg_data.columns.tolist()
                
                if is_horizontal:
                    option['yAxis']['data'] = categories
                else:
                    option['xAxis']['data'] = categories
                
                option['legend']['data'] = [str(s) for s in stacks]
                
                # 创建系列
                series = []
                for stack_val in stacks:
                    stack_series = {
                        'name': str(stack_val),
                        'type': 'bar',
                        'stack': 'total',
                        'emphasis': {'focus': 'series'},
                        'data': agg_data[stack_val].tolist(),
                        'label': {
                            'show': True,
                            'position': 'inside'
                        }
                    }
                    series.append(stack_series)
                
                option['series'] = series
                return option
        
        elif chart_subtype == 'bar_line':
            # 如果有额外的数值列，添加折线图
            if len(chart_info.get('extra_y_cols', [])) > 0:
                extra_y_col = chart_info['extra_y_cols'][0]
                extra_data = df.groupby(category)[extra_y_col].sum().reset_index()
                
                line_series = {
                    'name': extra_y_col,
                    'type': 'line',
                    'yAxisIndex': 1,
                    'data': extra_data[extra_y_col].tolist(),
                    'smooth': True,
                    'symbolSize': 8,
                    'lineStyle': {
                        'width': 3
                    }
                }
                
                # 添加第二个Y轴
                option['yAxis'] = [option['yAxis'], {
                    'type': 'value',
                    'name': extra_y_col,
                    'nameLocation': 'middle',
                    'nameGap': 40,
                    'splitLine': {
                        'show': False
                    },
                    'position': 'right'
                }]
                
                option['series'] = [series_config, line_series]
                return option
        
        elif chart_subtype == 'waterfall':
            # 转换为瀑布图数据
            waterfall_data = []
            total = 0
            
            for i, row in agg_data.iterrows():
                item_value = row[value]
                total += item_value
                
                waterfall_data.append({
                    'name': str(row[category]),
                    'value': item_value,
                    'itemStyle': {
                        'color': color_theme['colors'][0] if item_value > 0 else color_theme['colors'][1]
                    }
                })
            
            # 添加总计
            waterfall_data.append({
                'name': '总计',
                'value': total,
                'itemStyle': {
                    'color': color_theme['colors'][2]
                }
            })
            
            series_config['data'] = waterfall_data
            series_config['label']['position'] = 'top'
        
        elif chart_subtype == 'grouped_bar':
            # 需要额外的分组维度
            if 'group_by' in chart_info and chart_info['group_by'] in df.columns:
                group_col = chart_info['group_by']
                
                # 重新聚合数据以支持分组
                grouped_data = df.pivot_table(
                    index=category, 
                    columns=group_col, 
                    values=value, 
                    aggfunc='sum'
                ).fillna(0)
                
                categories = grouped_data.index.tolist()
                groups = grouped_data.columns.tolist()
                
                if is_horizontal:
                    option['yAxis']['data'] = categories
                else:
                    option['xAxis']['data'] = categories
                
                option['legend']['data'] = [str(g) for g in groups]
                
                # 创建系列
                series = []
                for group_val in groups:
                    group_series = {
                        'name': str(group_val),
                        'type': 'bar',
                        'emphasis': {'focus': 'series'},
                        'data': grouped_data[group_val].tolist()
                    }
                    series.append(group_series)
                
                option['series'] = series
                return option
        
        elif chart_subtype == 'polar_bar':
            # 创建极坐标柱状图
            option['polar'] = {}
            option['angleAxis'] = {
                'type': 'category',
                'data': agg_data[category].tolist()
            }
            option['radiusAxis'] = {}
            
            series_config['coordinateSystem'] = 'polar'
            series_config.pop('markPoint', None)
            
            option.pop('xAxis', None)
            option.pop('yAxis', None)
        
        # 添加默认系列
        if 'series' not in option:
            option['series'] = [series_config]
    
    # 饼图
    elif chart_type == 'pie':
        category = chart_info['category']
        value = chart_info['value']
        
        # 聚合数据
        agg_data = df.groupby(category)[value].sum().reset_index()
        
        pie_data = [{'name': str(row[category]), 'value': float(row[value])} 
                   for _, row in agg_data.iterrows()]
        
        series_config = {
            'name': value,
            'type': 'pie',
            'radius': '55%',
            'center': ['50%', '50%'],
            'data': pie_data,
            'label': {
                'formatter': '{b}: {d}%'
            },
            'emphasis': {
                'itemStyle': {
                    'shadowBlur': 10,
                    'shadowOffsetX': 0,
                    'shadowColor': 'rgba(0, 0, 0, 0.5)'
                }
            }
        }
        
        if chart_subtype == 'doughnut':
            series_config['radius'] = ['40%', '70%']
            
        elif chart_subtype == 'rose':
            series_config['roseType'] = 'radius'
            series_config['radius'] = ['20%', '70%']
            
        elif chart_subtype == 'nested_pie':
            # 创建两层嵌套饼图
            # 需要额外的分类字段
            if 'inner_category' in chart_info and chart_info['inner_category'] in df.columns:
                inner_category = chart_info['inner_category']
                
                # 聚合内层数据
                inner_data = df.groupby(inner_category)[value].sum().reset_index()
                inner_pie_data = [{'name': str(row[inner_category]), 'value': float(row[value])} 
                               for _, row in inner_data.iterrows()]
                
                inner_series = {
                    'name': inner_category,
                    'type': 'pie',
                    'radius': ['0%', '40%'],
                    'center': ['50%', '50%'],
                    'label': {
                        'position': 'inner',
                        'formatter': '{b}: {d}%'
                    },
                    'data': inner_pie_data
                }
                
                # 调整外层饼图
                series_config['radius'] = ['50%', '70%']
                
                option['series'] = [inner_series, series_config]
                return option
                
        elif chart_subtype == 'nightingale':
            series_config['roseType'] = 'area'
            series_config['radius'] = ['20%', '70%']
            
        option['series'] = [series_config]
        
        # 调整饼图特定布局
        option.pop('grid', None)
        option.pop('xAxis', None)
        option.pop('yAxis', None)
        
        # 增加饼图图例位置
        option['legend']['orient'] = 'vertical'
        option['legend']['left'] = 'left'
        option['legend']['top'] = 'middle'
    
    # 散点图
    elif chart_type == 'scatter':
        x_axis = chart_info['x_axis']
        y_axis = chart_info['y_axis']
        
        scatter_data = [[float(row[x_axis]), float(row[y_axis])] 
                      for _, row in df.iterrows() if pd.notna(row[x_axis]) and pd.notna(row[y_axis])]
        
        option.update({
            'xAxis': {
                'type': 'value',
                'name': x_axis,
                'nameLocation': 'middle',
                'nameGap': 30,
                'scale': True
            },
            'yAxis': {
                'type': 'value',
                'name': y_axis,
                'nameLocation': 'middle',
                'nameGap': 40,
                'scale': True
            },
            'grid': {
                'left': '5%',
                'right': '5%',
                'bottom': '15%',
                'top': '15%',
                'containLabel': True
            },
            'dataZoom': [
                {
                    'type': 'inside',
                    'xAxisIndex': 0,
                    'start': 0,
                    'end': 100
                },
                {
                    'type': 'inside',
                    'yAxisIndex': 0,
                    'start': 0,
                    'end': 100
                }
            ]
        })
        
        series_config = {
            'name': f'{x_axis} vs {y_axis}',
            'type': 'scatter',
            'data': scatter_data,
            'symbolSize': 12,
            'emphasis': {
                'focus': 'series',
                'label': {
                    'show': True,
                    'position': 'top'
                }
            }
        }
        
        if chart_subtype == 'bubble' and 'size_field' in chart_info:
            size_field = chart_info['size_field']
            
            # 重新生成带有气泡大小的数据
            bubble_data = []
            for _, row in df.iterrows():
                if pd.notna(row[x_axis]) and pd.notna(row[y_axis]) and pd.notna(row[size_field]):
                    # 用第三个维度的值确定气泡大小
                    size_value = float(row[size_field])
                    # 确保有合理的气泡大小范围
                    symbol_size = 4 + abs(size_value) * 50 / df[size_field].abs().max()
                    bubble_data.append([float(row[x_axis]), float(row[y_axis]), size_value, symbol_size])
            
            series_config['data'] = bubble_data
            series_config['symbolSize'] = lambda param: param[3]
            series_config['emphasis']['label']['formatter'] = lambda param: param.dataIndex
        
        elif chart_subtype == 'effect_scatter':
            series_config['type'] = 'effectScatter'
            series_config['showEffectOn'] = 'render'
            series_config['rippleEffect'] = {
                'brushType': 'stroke'
            }
            series_config['symbolSize'] = 15
        
        elif chart_subtype == 'labeled_scatter':
            # 添加标签
            series_config['label'] = {
                'show': True,
                'position': 'right',
                'formatter': lambda param: param.dataIndex
            }
            
            if 'label_field' in chart_info and chart_info['label_field'] in df.columns:
                label_field = chart_info['label_field']
                
                # 带标签的数据
                labeled_data = []
                for i, row in df.iterrows():
                    if pd.notna(row[x_axis]) and pd.notna(row[y_axis]):
                        labeled_data.append({
                            'value': [float(row[x_axis]), float(row[y_axis])],
                            'name': str(row[label_field])
                        })
                
                series_config['data'] = labeled_data
                series_config['label']['formatter'] = lambda param: param.dataIndex
        
        option['series'] = [series_config]
    
    # 热力图
    elif chart_type == 'heatmap':
        x_axis = chart_info['x_axis']
        y_axis = chart_info['y_axis']
        value = chart_info['value']
        
        # 基础热力图配置
        if chart_subtype == 'basic_heatmap':
            # 聚合数据
            agg_data = df.pivot_table(index=y_axis, columns=x_axis, values=value, aggfunc='mean').fillna(0)
            
            x_categories = agg_data.columns.tolist()
            y_categories = agg_data.index.tolist()
            
            # 准备热力图数据
            data = []
            for i, y_val in enumerate(y_categories):
                for j, x_val in enumerate(x_categories):
                    data.append([j, i, float(agg_data.loc[y_val, x_val])])
            
            option.update({
                'tooltip': {
                    'position': 'top'
                },
                'xAxis': {
                    'type': 'category',
                    'data': [str(x) for x in x_categories],
                    'splitArea': {'show': True},
                    'name': x_axis,
                    'nameLocation': 'middle',
                    'nameGap': 30
                },
                'yAxis': {
                    'type': 'category',
                    'data': [str(y) for y in y_categories],
                    'splitArea': {'show': True},
                    'name': y_axis,
                    'nameLocation': 'middle',
                    'nameGap': 60
                },
                'visualMap': {
                    'min': 0,
                    'max': agg_data.values.max(),
                    'calculable': True,
                    'orient': 'horizontal',
                    'left': 'center',
                    'bottom': '5%',
                    'inRange': {
                        'color': color_theme['colors'][1:5]
                    }
                },
                'grid': {
                    'left': '10%',
                    'right': '10%',
                    'bottom': '15%',
                    'top': '15%',
                }
            })
            
            series_config = {
                'name': value,
                'type': 'heatmap',
                'data': data,
                'label': {
                    'show': True
                },
                'emphasis': {
                    'itemStyle': {
                        'shadowBlur': 10,
                        'shadowColor': 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }
            
            option['series'] = [series_config]
    
    # 默认情况，使用_generate_echarts_option函数
    if 'series' not in option:
        return _generate_echarts_option(chart_info, sql_data)
    
    return option


def convert_sql_to_chart(sql_data: SQLData, excluded_types: List[str] = None, 
                         preferred_types: List[str] = None, force_new: bool = True,
                         prev_chart_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    将SQL数据转换为随机的适合的ECharts图表配置
    
    Args:
        sql_data: SQLData对象，包含SQL语句和查询结果
        excluded_types: 要排除的图表类型列表，例如['pie', 'radar']
        preferred_types: 偏好的图表类型列表，给这些类型更高的权重
        force_new: 是否强制选择与上次不同的图表类型
        prev_chart_info: 上次使用的图表信息，用于不重复选择相同的图表
    
    Returns:
        包含图表类型和ECharts配置的字典
    """
    if excluded_types is None:
        excluded_types = []
        
    if preferred_types is None:
        preferred_types = []
        
    if not sql_data.data:
        return {
            'chart_type': 'table',
            'chart_subtype': 'basic_table',
            'chart_name': '基础表格',
            'echarts_option': {
                'type': 'table',
                'columns': [{'title': col, 'dataIndex': col} for col in sql_data.column_names],
                'dataSource': []
            },
            'message': '没有数据可供展示'
        }
    
    # 获取适合的图表类型
    all_suitable_charts = _get_suitable_chart_types(sql_data)
    
    # 如果没有找到合适的图表类型，默认使用表格
    if not all_suitable_charts:
        return {
            'chart_type': 'table',
            'chart_subtype': 'basic_table',
            'chart_name': '基础表格',
            'echarts_option': {
                'type': 'table',
                'columns': [{'title': col, 'dataIndex': col} for col in sql_data.column_names],
                'dataSource': sql_data.data
            },
            'message': '无法确定合适的图表类型，使用表格展示'
        }
    
    # 应用排除和偏好设置
    suitable_charts = []
    
    # 按图表类型分组，以便每种类型的图表只选择一个代表
    chart_by_type = {}
    for chart in all_suitable_charts:
        # 排除指定的图表类型
        if chart['type'] in excluded_types:
            continue
            
        # 如果需要选择新的图表类型，排除上次使用的
        if force_new and prev_chart_info and \
           prev_chart_info.get('chart_type') == chart['type'] and \
           prev_chart_info.get('chart_subtype') == chart.get('subtype'):
            continue
            
        # 按类型分组收集图表
        chart_type = chart['type']
        if chart_type not in chart_by_type:
            chart_by_type[chart_type] = []
        chart_by_type[chart_type].append(chart)
    
    # 从每个类型中随机选择一个代表
    for chart_type, charts in chart_by_type.items():
        # 随机选择该类型的一个图表
        selected_chart = random.choice(charts)
        suitable_charts.append(selected_chart)
    
    # 确保至少有一个可选图表
    if not suitable_charts:
        # 如果因为排除条件太严格导致没有图表，放宽条件
        suitable_charts = all_suitable_charts
    
    # 所有图表类型平等随机选择，不再使用加权选择
    selected_chart = random.choice(suitable_charts)
    
    # 随机选择配色方案
    selected_theme = random.choice(COLOR_THEMES)
    
    # 生成图表配置
    chart_config = _generate_enhanced_echarts_option(selected_chart, sql_data, selected_theme)
    
    chart_type = selected_chart['type']
    chart_subtype = selected_chart.get('subtype', 'basic')
    chart_name = selected_chart.get('name', f'{chart_type}图')
    
    return {
        'chart_type': chart_type,
        'chart_subtype': chart_subtype,
        'chart_name': chart_name,
        'echarts_option': chart_config,
        'suitable_charts': [{'type': c['type'], 'subtype': c.get('subtype', 'basic'), 'name': c.get('name', '')} 
                           for c in suitable_charts],
        'color_theme': selected_theme['name'],
        'message': f'已选择 {chart_name} 进行展示'
    } 