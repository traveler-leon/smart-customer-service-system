# SQL2BI 模块

SQL2BI 是一个将SQL查询结果智能转换为ECharts图表配置的工具。根据数据特性，自动分析并选择最适合的可视化图表，以科幻、随机的方式呈现数据洞察。

## 主要特性

- 自动分析SQL语句结构和查询结果数据特性
- 智能匹配适合的图表类型，支持10+种ECharts图表及其各种子类型
- 同一数据每次随机选择不同图表类型，提供多样化的视觉体验
- 支持指定偏好或排除特定图表类型，灵活控制图表生成
- 随机选择配色方案，增强视觉多样性
- 生成完整的ECharts配置选项，可直接用于前端渲染
- 支持表格、折线图、柱状图、饼图、散点图、堆叠图、热力图、雷达图等多种图表及其变体

## 安装依赖

本模块依赖以下Python包：

```bash
pip install pandas numpy
```

## 快速开始

### 1. 导入模块

```python
from sql2bi import SQLData, convert_sql_to_chart
# 或者使用便捷工具函数
from sql2bi.utils import sql_result_to_chart
```

### 2. 创建SQL数据对象

```python
# SQL语句
sql = """
SELECT product_category, region, SUM(sales) as total_sales 
FROM sales_data 
WHERE year = 2023 
GROUP BY product_category, region
"""

# 查询结果数据
data = [
    {"product_category": "电子产品", "region": "北京", "total_sales": 12500},
    {"product_category": "电子产品", "region": "上海", "total_sales": 15800},
    # 更多数据...
]

# 方法1: 创建SQLData对象
sql_data = SQLData(sql, data)
chart_config = convert_sql_to_chart(sql_data)

# 方法2: 使用便捷函数
chart_config = sql_result_to_chart(sql, data)
```

### 3. 控制图表选择

```python
# 排除特定图表类型
chart_config = convert_sql_to_chart(sql_data, excluded_types=['pie', 'radar'])

# 偏好特定图表类型
chart_config = convert_sql_to_chart(sql_data, preferred_types=['bar', 'line'])

# 强制选择不同于上次的图表类型
chart_config2 = convert_sql_to_chart(sql_data, prev_chart_info=chart_config, force_new=True)
```

### 4. 在前端使用

将`echarts_option`传递给前端ECharts实例：

```javascript
// 前端示例代码
const chart = echarts.init(document.getElementById('chart-container'));
chart.setOption(chart_config.echarts_option);
```

## 输出示例

```json
{
  "chart_type": "bar", 
  "chart_subtype": "stacked_bar", 
  "chart_name": "堆叠柱状图", 
  "echarts_option": {
    "title": {"text": "数据分析结果", "left": "center", "top": 10, "textStyle": {"fontSize": 18}}, 
    "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}}, 
    "legend": {"bottom": 10, "left": "center", "data": ["北京", "上海", "广州"]}, 
    "xAxis": {"type": "category", "data": ["电子产品", "服装", "食品"], "name": "product_category", "nameLocation": "middle", "nameGap": 30, "axisLabel": {"interval": 0, "rotate": 30}}, 
    "yAxis": {"type": "value", "name": "total_sales", "nameLocation": "middle", "nameGap": 40, "splitLine": {"show": true, "lineStyle": {"type": "dashed"}}}, 
    "grid": {"left": "5%", "right": "5%", "bottom": "15%", "top": "15%", "containLabel": true}, 
    "color": ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de", "#3ba272", "#fc8452", "#9a60b4", "#ea7ccc"], 
    "animation": true, 
    "animationDuration": 1000, 
    "animationEasing": "elasticOut", 
    "series": [
      {"name": "北京", "type": "bar", "stack": "total", "emphasis": {"focus": "series"}, "data": [12500, 8200, 5300], "label": {"show": true, "position": "inside"}}, 
      {"name": "上海", "type": "bar", "stack": "total", "emphasis": {"focus": "series"}, "data": [15800, 9100, 4800], "label": {"show": true, "position": "inside"}}, 
      {"name": "广州", "type": "bar", "stack": "total", "emphasis": {"focus": "series"}, "data": [9300, 7300, 6100], "label": {"show": true, "position": "inside"}}
    ]
  }, 
  "suitable_charts": [...],
  "color_theme": "默认", 
  "message": "已选择 堆叠柱状图 进行展示"
}
```

## 支持的图表类型

SQL2BI模块支持以下主要图表类型及其多种变体：

- **折线图系列**: 基础折线图、平滑曲线图、阶梯折线图、区域折线图、堆叠区域图等
- **柱状/条形图系列**: 基础柱状图、条形图、堆叠柱状图、分组柱状图、柱线混合图、瀑布图等
- **饼图系列**: 基础饼图、环形图、玫瑰图、嵌套饼图、南丁格尔玫瑰图等
- **散点图系列**: 基础散点图、气泡图、涟漪散点图、带标签散点图等
- **热力图系列**: 基础热力图、日历热力图、极坐标热力图等
- **雷达图系列**: 基础雷达图、填充雷达图、多层雷达图等
- **漏斗图系列**: 基础漏斗图、对比漏斗图、金字塔图等
- **其他图表**: 仪表盘、盒须图、树图、桑基图、日历图等
- **表格展示**: 基础表格、条件格式表格、热力表格等

## 图表选择逻辑

模块会根据以下因素选择合适的图表类型：

1. 数据列的类型(数值型、类别型、时间型、文本型)
2. SQL查询的特性(是否有GROUP BY, 是否有聚合函数等)
3. 类别数量和数据分布
4. 数据维度和特征
5. 用户指定的偏好或排除条件

每次调用时会随机选择一个合适的图表类型和子类型，保持数据展示的多样性和趣味性。

## 配色方案

SQL2BI模块内置了多种配色方案，包括：

- 默认配色
- 商业蓝
- 科技感
- 自然环保
- 时尚现代
- 复古怀旧
- 高对比度

每次生成图表时会随机选择一种配色方案，增强视觉多样性。

## 实用工具函数

SQL2BI模块提供了一些实用工具函数：

```python
from sql2bi.utils import sql_result_to_chart, chart_config_to_json
from sql2bi.utils import get_available_chart_types, get_random_chart_type

# 从SQL结果直接生成图表
chart_config = sql_result_to_chart(sql, data)

# 转换为JSON字符串
json_str = chart_config_to_json(chart_config)

# 获取所有可用图表类型
chart_types = get_available_chart_types()

# 随机获取一个图表类型
random_chart = get_random_chart_type()
``` 