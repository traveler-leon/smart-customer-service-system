"""
SQL到BI转换模块的示例使用脚本

这个脚本展示了如何使用sql2bi模块将SQL查询结果转换为ECharts图表配置
"""

from . import SQLData, convert_sql_to_chart, CHART_TYPES, COLOR_THEMES
import json
import random

def main():
    """示例使用sql2bi模块"""
    
    # 示例SQL和数据
    example_sql = """
    SELECT product_category, region, SUM(sales) as total_sales, AVG(profit) as avg_profit
    FROM sales_data 
    WHERE year = 2023 
    GROUP BY product_category, region 
    ORDER BY total_sales DESC
    """
    
    # 模拟数据
    example_data = [
        {"product_category": "电子产品", "region": "北京", "total_sales": 12500, "avg_profit": 4200},
        {"product_category": "电子产品", "region": "上海", "total_sales": 15800, "avg_profit": 5100},
        {"product_category": "电子产品", "region": "广州", "total_sales": 9300, "avg_profit": 3100},
        {"product_category": "服装", "region": "北京", "total_sales": 8200, "avg_profit": 2800},
        {"product_category": "服装", "region": "上海", "total_sales": 9100, "avg_profit": 3000},
        {"product_category": "服装", "region": "广州", "total_sales": 7300, "avg_profit": 2500},
        {"product_category": "食品", "region": "北京", "total_sales": 5300, "avg_profit": 1800},
        {"product_category": "食品", "region": "上海", "total_sales": 4800, "avg_profit": 1500},
        {"product_category": "食品", "region": "广州", "total_sales": 6100, "avg_profit": 2000},
    ]
    
    # 创建SQLData对象
    sql_data = SQLData(example_sql, example_data)
    
    # 打印可用的图表类型
    print("可用的图表类型和子类型:")
    for chart_type, subtypes in CHART_TYPES.items():
        print(f"  {chart_type}: {len(subtypes)}种子类型")
    
    print(f"\n可用的颜色主题: {', '.join([theme['name'] for theme in COLOR_THEMES])}")
    
    # 转换为图表配置
    chart_config = convert_sql_to_chart(sql_data)
    
    # 打印结果
    print(f"\n选择的图表类型: {chart_config['chart_type']}")
    print(f"图表子类型: {chart_config['chart_subtype']}")
    print(f"图表名称: {chart_config['chart_name']}")
    print(f"颜色主题: {chart_config['color_theme']}")
    print(f"消息: {chart_config['message']}")
    
    # 随机选择特定类型
    preferred_types = random.choice([['bar'], ['line'], ['pie'], ['scatter']])
    print(f"\n指定偏好图表类型 {preferred_types}:")
    chart_config2 = convert_sql_to_chart(sql_data, preferred_types=preferred_types)
    print(f"选择的图表类型: {chart_config2['chart_type']}")
    print(f"图表子类型: {chart_config2['chart_subtype']}")
    print(f"图表名称: {chart_config2['chart_name']}")
    
    # 排除特定类型
    excluded_types = random.choice([['bar', 'pie'], ['line', 'scatter'], ['radar', 'table']])
    print(f"\n排除图表类型 {excluded_types}:")
    chart_config3 = convert_sql_to_chart(sql_data, excluded_types=excluded_types)
    print(f"选择的图表类型: {chart_config3['chart_type']}")
    print(f"图表子类型: {chart_config3['chart_subtype']}")
    print(f"图表名称: {chart_config3['chart_name']}")
    
    # 强制选择新的图表类型
    print("\n强制选择与上次不同的图表:")
    prev_chart = chart_config3
    chart_config4 = convert_sql_to_chart(sql_data, prev_chart_info=prev_chart, force_new=True)
    print(f"上次图表: {prev_chart['chart_type']}/{prev_chart['chart_subtype']}")
    print(f"这次图表: {chart_config4['chart_type']}/{chart_config4['chart_subtype']}")

if __name__ == "__main__":
    main()