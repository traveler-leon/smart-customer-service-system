"""
定义更丰富的ECharts图表类型和子类型
"""

# 基础图表类型及其子类型
CHART_TYPES = {
    # 折线图子类型
    "line": [
        {
            "name": "基础折线图",
            "subtype": "basic_line",
            "suitability_score": 5,  # 适用性评分(1-10)
            "description": "基础的折线图，适合展示连续数据的趋势变化"
        },
        {
            "name": "平滑曲线图",
            "subtype": "smooth_line",
            "suitability_score": 5,
            "description": "平滑曲线的折线图，视觉效果更加柔和"
        },
        {
            "name": "阶梯折线图",
            "subtype": "step_line",
            "suitability_score": 4,
            "description": "阶梯状的折线图，适合展示数据的阶段性变化"
        },
        {
            "name": "区域折线图",
            "subtype": "area_line",
            "suitability_score": 6,
            "description": "带有填充区域的折线图，强调数据量的变化"
        },
        {
            "name": "堆叠区域图",
            "subtype": "stacked_area_line",
            "suitability_score": 7,
            "description": "多系列堆叠的区域图，展示多个数据系列的叠加效果"
        },
        {
            "name": "渐变区域图",
            "subtype": "gradient_area_line",
            "suitability_score": 6,
            "description": "使用渐变色填充的区域图，视觉效果更加绚丽"
        }
    ],

    # 柱状图子类型
    "bar": [
        {
            "name": "基础柱状图",
            "subtype": "basic_bar",
            "suitability_score": 5,
            "description": "基础的垂直柱状图，适合类别数据的数值比较"
        },
        {
            "name": "条形图",
            "subtype": "horizontal_bar",
            "suitability_score": 6,
            "description": "水平方向的柱状图，适合类别较多的数据展示"
        },
        {
            "name": "堆叠柱状图",
            "subtype": "stacked_bar",
            "suitability_score": 7,
            "description": "垂直方向的堆叠柱状图，展示构成关系"
        },
        {
            "name": "堆叠条形图",
            "subtype": "stacked_horizontal_bar",
            "suitability_score": 7,
            "description": "水平方向的堆叠柱状图，适合类别较多的构成关系展示"
        },
        {
            "name": "柱状图+折线图",
            "subtype": "bar_line",
            "suitability_score": 6,
            "description": "柱状图和折线图的组合，适合展示不同量级的数据"
        },
        {
            "name": "极坐标柱状图",
            "subtype": "polar_bar",
            "suitability_score": 3,
            "description": "在极坐标系下的柱状图，适合周期性数据或环形分布"
        },
        {
            "name": "瀑布图",
            "subtype": "waterfall",
            "suitability_score": 4,
            "description": "展示数据变化过程的特殊柱状图，适合展示增减变化"
        },
        {
            "name": "分组柱状图",
            "subtype": "grouped_bar",
            "suitability_score": 7,
            "description": "多系列并排显示的柱状图，适合多组数据的直接比较"
        }
    ],

    # 饼图子类型
    "pie": [
        {
            "name": "基础饼图",
            "subtype": "basic_pie",
            "suitability_score": 5,
            "description": "基础的饼图，展示构成占比关系"
        },
        {
            "name": "环形图",
            "subtype": "doughnut",
            "suitability_score": 6,
            "description": "中间有空洞的饼图，可以在中心添加额外信息"
        },
        {
            "name": "玫瑰图",
            "subtype": "rose",
            "suitability_score": 4,
            "description": "扇区半径随数值变化的饼图，既展示占比又展示数值大小"
        },
        {
            "name": "嵌套饼图",
            "subtype": "nested_pie",
            "suitability_score": 3,
            "description": "内外两层的饼图，适合展示层级构成关系"
        },
        {
            "name": "南丁格尔玫瑰图",
            "subtype": "nightingale",
            "suitability_score": 4,
            "description": "扇区相等但半径不同的玫瑰图，强调数值差异"
        }
    ],

    # 散点图子类型
    "scatter": [
        {
            "name": "基础散点图",
            "subtype": "basic_scatter",
            "suitability_score": 5,
            "description": "基础的散点图，展示数据的分布关系"
        },
        {
            "name": "气泡图",
            "subtype": "bubble",
            "suitability_score": 6,
            "description": "散点大小随第三维数据变化的散点图，可展示三维数据关系"
        },
        {
            "name": "涟漪散点图",
            "subtype": "effect_scatter",
            "suitability_score": 4,
            "description": "带有涟漪动画效果的散点图，突出关键数据点"
        },
        {
            "name": "带标签散点图",
            "subtype": "labeled_scatter",
            "suitability_score": 5,
            "description": "带有标签的散点图，可直接标示数据点的额外信息"
        }
    ],

    # 热力图子类型
    "heatmap": [
        {
            "name": "基础热力图",
            "subtype": "basic_heatmap",
            "suitability_score": 5,
            "description": "基础的直角坐标系热力图，适合展示二维数据的密度分布"
        },
        {
            "name": "日历热力图",
            "subtype": "calendar_heatmap",
            "suitability_score": 4,
            "description": "以日历形式展示的热力图，适合按日期展示数据"
        },
        {
            "name": "极坐标热力图",
            "subtype": "polar_heatmap",
            "suitability_score": 3,
            "description": "在极坐标系下的热力图，适合展示环形分布的热力"
        }
    ],

    # 雷达图子类型
    "radar": [
        {
            "name": "基础雷达图",
            "subtype": "basic_radar",
            "suitability_score": 5,
            "description": "基础的雷达图，适合多维数据的综合展示"
        },
        {
            "name": "填充雷达图",
            "subtype": "filled_radar",
            "suitability_score": 6,
            "description": "带有填充区域的雷达图，更直观地展示数据面积"
        },
        {
            "name": "多层雷达图",
            "subtype": "multi_radar",
            "suitability_score": 7,
            "description": "多数据系列的雷达图，适合多组数据的对比"
        }
    ],

    # 漏斗图子类型
    "funnel": [
        {
            "name": "基础漏斗图",
            "subtype": "basic_funnel",
            "suitability_score": 5,
            "description": "基础的漏斗图，适合展示流程转化率"
        },
        {
            "name": "对比漏斗图",
            "subtype": "compare_funnel",
            "suitability_score": 6,
            "description": "左右对称的漏斗图，适合两组数据的对比"
        },
        {
            "name": "金字塔图",
            "subtype": "pyramid",
            "suitability_score": 5,
            "description": "上宽下窄的漏斗图，适合层级数据的展示"
        }
    ],

    # 仪表盘子类型
    "gauge": [
        {
            "name": "基础仪表盘",
            "subtype": "basic_gauge",
            "suitability_score": 5,
            "description": "基础的仪表盘，适合展示进度或完成率"
        },
        {
            "name": "多指针仪表盘",
            "subtype": "multi_gauge",
            "suitability_score": 4,
            "description": "带有多个指针的仪表盘，适合对比多个指标"
        },
        {
            "name": "进度仪表盘",
            "subtype": "progress_gauge",
            "suitability_score": 6,
            "description": "简化的进度条式仪表盘，更加现代的设计"
        }
    ],

    # 盒须图子类型
    "boxplot": [
        {
            "name": "基础盒须图",
            "subtype": "basic_boxplot",
            "suitability_score": 5,
            "description": "基础的盒须图，适合展示数据分布特征"
        },
        {
            "name": "分组盒须图",
            "subtype": "grouped_boxplot",
            "suitability_score": 6,
            "description": "多组对比的盒须图，适合多个类别数据分布的对比"
        }
    ],

    # 树图子类型
    "treemap": [
        {
            "name": "基础矩形树图",
            "subtype": "basic_treemap",
            "suitability_score": 5,
            "description": "基础的矩形树图，适合展示层级数据和占比关系"
        },
        {
            "name": "多层级树图",
            "subtype": "multi_treemap",
            "suitability_score": 4,
            "description": "可下钻的多层级树图，适合复杂层级数据的展示"
        },
        {
            "name": "渐变树图",
            "subtype": "gradient_treemap",
            "suitability_score": 5,
            "description": "使用渐变色的树图，视觉效果更加丰富"
        }
    ],

    # 桑基图
    "sankey": [
        {
            "name": "基础桑基图",
            "subtype": "basic_sankey",
            "suitability_score": 4,
            "description": "基础的桑基图，适合展示复杂的流向关系"
        }
    ],

    # 日历图
    "calendar": [
        {
            "name": "基础日历图",
            "subtype": "basic_calendar",
            "suitability_score": 3,
            "description": "基础的日历图，适合按日期展示数据"
        }
    ],

    # 表格
    "table": [
        {
            "name": "基础表格",
            "subtype": "basic_table",
            "suitability_score": 10,
            "description": "基础的数据表格，最直观地展示原始数据"
        },
        {
            "name": "条件格式表格",
            "subtype": "conditional_table",
            "suitability_score": 9,
            "description": "带有条件格式的表格，突出显示关键数据"
        },
        {
            "name": "热力表格",
            "subtype": "heatmap_table",
            "suitability_score": 8,
            "description": "单元格以热力图形式显示的表格，直观展示数值高低"
        }
    ]
}

# 为不同数据特征推荐的图表类型
DATA_FEATURE_RECOMMENDATIONS = {
    # 时间序列数据
    "time_series": [
        "line.basic_line", "line.smooth_line", "line.area_line", "bar.basic_bar",
        "heatmap.calendar_heatmap", "calendar.basic_calendar"
    ],
    
    # 类别比较数据
    "category_comparison": [
        "bar.basic_bar", "bar.horizontal_bar", "bar.grouped_bar", "pie.basic_pie",
        "pie.doughnut", "radar.basic_radar", "funnel.basic_funnel"
    ],
    
    # 分布数据
    "distribution": [
        "scatter.basic_scatter", "boxplot.basic_boxplot", "heatmap.basic_heatmap",
        "pie.rose", "pie.nightingale"
    ],
    
    # 构成关系数据
    "composition": [
        "pie.basic_pie", "pie.doughnut", "bar.stacked_bar", "bar.stacked_horizontal_bar",
        "line.stacked_area_line", "treemap.basic_treemap"
    ],
    
    # 相关性分析数据
    "correlation": [
        "scatter.basic_scatter", "scatter.bubble", "heatmap.basic_heatmap"
    ],
    
    # 排名数据
    "ranking": [
        "bar.horizontal_bar", "bar.basic_bar", "bar.waterfall", "funnel.basic_funnel",
        "pie.rose"
    ],
    
    # 流向关系数据
    "flow": [
        "sankey.basic_sankey"
    ],
    
    # 地理数据
    "geo": [
        "scatter.basic_scatter", "heatmap.basic_heatmap"  # 实际使用需配合地图组件
    ],
    
    # 多维度数据
    "multi_dimension": [
        "radar.basic_radar", "radar.filled_radar", "radar.multi_radar",
        "parallel.basic_parallel"
    ],
    
    # 监控数据
    "monitoring": [
        "gauge.basic_gauge", "gauge.progress_gauge", "line.basic_line"
    ]
}

# 常用视觉主题列表
COLOR_THEMES = [
    # 默认主题
    {
        "name": "默认",
        "colors": ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc']
    },
    # 商业/企业主题
    {
        "name": "商业蓝",
        "colors": ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a', '#d62728', '#ff9896', '#9467bd']
    },
    # 科技感主题
    {
        "name": "科技",
        "colors": ['#3366cc', '#dc3912', '#ff9900', '#109618', '#990099', '#0099c6', '#dd4477', '#66aa00', '#b82e2e']
    },
    # 自然/环保主题
    {
        "name": "自然",
        "colors": ['#5cb85c', '#8bc34a', '#4caf50', '#009688', '#35a8a8', '#3f51b5', '#7986cb', '#33b679', '#0b8043']
    },
    # 时尚/现代主题
    {
        "name": "时尚",
        "colors": ['#f94144', '#f3722c', '#f8961e', '#f9c74f', '#90be6d', '#43aa8b', '#577590', '#277da1', '#5c4742']
    },
    # 复古/怀旧主题
    {
        "name": "复古",
        "colors": ['#8a9a5b', '#704214', '#7d8471', '#b0b7c6', '#b5a642', '#856d4d', '#9e9764', '#c19a6b', '#a18276']
    },
    # 高对比度主题
    {
        "name": "高对比度",
        "colors": ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#ffff33', '#a65628', '#f781bf', '#999999']
    }
] 