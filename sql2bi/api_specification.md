# 机场智能客服聊天接口协议

## 1. 接口概述

机场智能客服聊天接口基于LangGraph框架设计，支持多种响应类型的流式输出，包括文本咨询、数据查询和表单办理等功能。系统利用LangGraph的会话状态管理和流式处理能力，为用户提供流畅的对话体验。

## 2. 基本信息

- **接口路径**: `/api/v1/airport-assistant/chat`
- **请求方法**: POST
- **内容类型**: application/json
- **响应类型**: text/event-stream (SSE)

## 3. 请求协议

```json
{
  "thread_id": "会话ID",
  "user_id": "用户唯一标识",
  "query": "用户输入的文本内容",
  "stream": true,
  "metadata": {
    "location": "用户当前位置信息",
    "device_info": "设备信息",
    "language": "zh-CN"
  }
}
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| thread_id | string | 是 | 会话标识，LangGraph利用此ID管理会话状态 |
| user_id | string | 是 | 用户唯一标识，用于用户画像关联 |
| query | string | 是 | 用户当前输入内容 |
| stream | boolean | 否 | 是否流式返回，默认为true |
| metadata | object | 否 | 可选的上下文信息 |

## 4. 响应协议（流式）

响应采用Server-Sent Events (SSE)格式，每个事件包含以下结构：

```
event: {event_type}
data: {JSON数据}
```

### 事件类型说明

| 事件类型 | 说明 |
| --- | --- |
| text | 文本类响应（纯文本或富文本） |
| data | 结构化数据（如航班信息） |
| visualization | 可视化指示（如何展示数据） |
| form | 交互式表单 |
| end | 响应结束标记 |
| error | 错误信息 |

## 5. 事件数据结构

每个事件的data部分包含统一的基础结构：

```json
{
  "id": "事件唯一标识",
  "sequence": 1,
  "content": {
    // 根据事件类型不同而变化
  }
}
```

### 5.1 文本响应 (event: text)

```json
{
  "id": "text-1",
  "sequence": 1,
  "content": {
    "text": "根",
    "format": "plain"
  }
}
```

### 5.1.1 文本格式选项

`format`字段用于指定文本内容的渲染方式，支持以下选项：

| 格式选项 | 说明 |
| --- | --- |
| plain | 纯文本格式，不包含任何样式 |
| markdown | Markdown格式，支持标题、列表、强调等基本格式 |
| html | HTML格式，可包含丰富的样式和布局 |
| rich | 富文本格式，支持字体、颜色等样式属性 |
| highlight | 高亮文本，用于强调重要信息 |

当文本内容需要特殊格式化时，应使用对应的format值并确保内容符合该格式规范。例如：

```json
{
  "id": "text-2",
  "sequence": 2,
  "content": {
    "text": "## 航班信息\\n* 航班号: MU5735\\n* 状态: **准点**",
    "format": "markdown"
  }
}
```

如不指定format字段，默认采用"plain"格式处理。

### 5.2 数据响应 (event: data)

```json
{
  "id": "data-1",
  "sequence": 2,
  "content": {
    "data_type": "flight_info",
    "data": [
      {
        "flight_no": "MU5735",
        "departure": "PVG",
        "arrival": "PEK",
        "scheduled_time": "2023-06-01T08:30:00",
        "status": "On time",
        "terminal": "T2",
        "gate": "A12"
      }
    ]
  }
}
```

### 5.3 可视化指示 (event: visualization)

```json
{
  "id": "vis-1",
  "sequence": 3,
  "content": {
    "visualization_type": "echarts",
    "title": "航班延误情况",
    "description": "按航空公司统计的延误情况",
    "data_reference": "data-1",
    "chart_info": {
      "chart_type": "bar",
      "chart_subtype": "basic_bar",
      "chart_name": "基础柱状图"
    },
    "config": {
      "colors": ["#FF5733", "#33FF57"],
      "legend_position": "right",
      "x_axis_label": "航空公司",
      "y_axis_label": "延误次数"
    },
    "echarts_option": {
      "xAxis": {
        "type": "category",
        "data": ["东航", "南航", "国航", "海航"]
      },
      "yAxis": {
        "type": "value"
      },
      "series": [
        {
          "type": "bar",
          "data": [120, 200, 150, 80]
        }
      ]
    },
    "sql_info": {
      "sql": "SELECT airline, COUNT(*) as delay_count FROM flights WHERE status='delayed' GROUP BY airline",
      "data_summary": "查询结果统计了各航空公司的延误航班数量"
    },
    "alternative_charts": [
      {
        "type": "pie",
        "subtype": "basic_pie",
        "name": "饼图"
      },
      {
        "type": "line",
        "subtype": "basic_line",
        "name": "折线图"
      }
    ]
  }
}
```

### 5.4 表单响应 (event: form)

```json
{
  "id": "form-1",
  "sequence": 4,
  "content": {
    "form_id": "checkin-123",
    "title": "值机办理",
    "description": "请填写以下信息完成值机",
    "action": "/api/v1/forms/submit",
    "fields": [
      {
        "id": "name",
        "type": "text",
        "label": "旅客姓名",
        "placeholder": "请输入姓名",
        "required": true
      },
      {
        "id": "id_number",
        "type": "text",
        "label": "证件号码",
        "placeholder": "请输入证件号码",
        "required": true,
        "validation": {
          "pattern": "^[A-Z0-9]{10,18}$",
          "error_message": "请输入有效的证件号码"
        }
      },
      {
        "id": "flight_no",
        "type": "text",
        "label": "航班号",
        "placeholder": "请输入航班号",
        "required": true
      }
    ],
    "buttons": [
      {
        "id": "submit",
        "label": "提交",
        "type": "submit"
      },
      {
        "id": "cancel",
        "label": "取消",
        "type": "cancel"
      }
    ]
  }
}
```

### 5.5 结束事件 (event: end)

```json
{
  "id": "end-1",
  "sequence": 5,
  "content": {
    "suggestions": ["查询行李规定", "值机办理", "航班动态"],
    "metadata": {
      "processing_time": "1.2s"
    }
  }
}
```

### 5.6 错误事件 (event: error)

```json
{
  "id": "error-1",
  "sequence": 1,
  "content": {
    "error_code": "service_unavailable",
    "error_message": "服务暂时不可用，请稍后再试"
  }
}
```

### 5.7 ID生成策略

事件ID生成对于字符级流式返回至关重要，特别是对于文本响应，建议采用以下生成策略：

1. **文本事件ID**：采用 `text-{timestamp}-{counter}` 格式
    - `timestamp`: 毫秒级时间戳，确保全局唯一性
    - `counter`: 单次请求内的递增计数器，从1开始
    - 示例: `text-1686245678123-1`, `text-1686245678125-2`
2. **数据事件ID**：采用 `data-{type}-{timestamp}` 格式
    - `type`: 数据类型简写，如flight、weather
    - 示例: `data-flight-1686245679456`
3. **可视化事件ID**：采用 `vis-{type}-{timestamp}` 格式
    - `type`: 可视化类型简写，如table、pie
    - 示例: `vis-table-1686245680789`
4. **表单事件ID**：采用 `form-{formType}-{timestamp}` 格式
    - `formType`: 表单类型，如checkin、booking
    - 示例: `form-checkin-1686245681012`
5. **结束事件ID**：采用 `end-{timestamp}` 格式
    - 示例: `end-1686245682345`
6. **错误事件ID**：采用 `error-{code}-{timestamp}` 格式
    - `code`: 错误代码简写
    - 示例: `error-auth-1686245683678`

对于字符级流式返回，生成策略需要考虑性能和唯一性平衡，建议:

- 使用批处理预生成ID池
- 字符流速控制在5-20ms一个字符
- 确保ID为可排序格式，便于断线重连时恢复

## 6. 使用场景示例

### 6.1 政策咨询（文本响应）

用户查询行李政策时，系统返回文本响应：

```
event: text
data: {"id":"text-1","sequence":1,"content":{"text":"根据最新规定，","format":"plain"}}

event: text
data: {"id":"text-2","sequence":2,"content":{"text":"每位乘客可免费托运一件不超过23公斤的行李，","format":"plain"}}

event: text
data: {"id":"text-3","sequence":3,"content":{"text":"手提行李不得超过7公斤。","format":"plain"}}

event: end
data: {"id":"end-1","sequence":4,"content":{"suggestions":["超重行李收费标准","物品限制规定"]}}
```

### 6.2 航班查询（数据+可视化）

用户查询航班信息时，系统返回航班数据和可视化指示：

```
event: visualization
data: {"id":"vis-1","sequence":1,"content":{"visualization_type":"table","title":"航班信息"}}

event: text
data: {"id":"text-1","sequence":2,"content":{"text":"您查询的航班MU5735从上海飞往北京，","format":"plain"}}

event: text
data: {"id":"text-2","sequence":3,"content":{"text":"目前状态为准点，计划起飞时间为2023年6月1日08:30。","format":"plain"}}

event: data
data: {"id":"data-1","sequence":4,"content":{"data_type":"flight_info","data":[{"flight_no":"MU5735","departure":"PVG","arrival":"PEK","scheduled_time":"2023-06-01T08:30:00","status":"On time","terminal":"T2","gate":"A12"}]}}

event: end
data: {"id":"end-1","sequence":5,"content":{"suggestions":["办理值机","查询登机口"]}}
```

### 6.3 SQL数据查询（图表可视化）

用户查询航空公司延误情况时，系统返回SQL查询结果和相应图表：

```
event: text
data: {"id":"text-1","sequence":1,"content":{"text":"根据您的查询，以下是各航空公司的航班延误情况：","format":"plain"}}

event: data
data: {"id":"data-sql-1","sequence":2,"content":{"data_type":"sql_result","data":[{"airline":"东方航空","delay_count":45,"on_time_rate":0.92},{"airline":"南方航空","delay_count":38,"on_time_rate":0.94},{"airline":"国航","delay_count":29,"on_time_rate":0.95}],"sql":"SELECT airline, COUNT(*) as delay_count, AVG(on_time) as on_time_rate FROM flights WHERE status='delayed' GROUP BY airline ORDER BY delay_count DESC"}}

event: visualization
data: {"id":"vis-chart-1","sequence":3,"content":{"visualization_type":"echarts","title":"航空公司延误统计","chart_info":{"chart_type":"bar","chart_subtype":"basic_bar","chart_name":"基础柱状图"},"echarts_option":{"xAxis":{"type":"category","data":["东方航空","南方航空","国航"]},"yAxis":{"type":"value"},"series":[{"data":[45,38,29],"type":"bar"}]},"alternative_charts":[{"type":"pie","subtype":"basic_pie","name":"饼图"},{"type":"line","subtype":"basic_line","name":"折线图"}]}}

event: text
data: {"id":"text-2","sequence":4,"content":{"text":"从图表可以看出，东方航空的延误航班数量最多，达到45个，但各航空公司的准点率都维持在90%以上。","format":"plain"}}

event: end
data: {"id":"end-1","sequence":5,"content":{"suggestions":["查看航班准点率趋势","比较不同机场延误情况"]}}
```

## 7. 图表类型支持

系统支持以下主要图表类型，每种类型下有多个子类型变体：

| 图表类型 | 主要子类型 | 适用场景 |
| --- | --- | --- |
| line (折线图) | basic_line, smooth_line, step_line, area_line | 时间趋势分析、连续数据展示 |
| bar (柱状图) | basic_bar, stacked_bar, horizontal_bar, waterfall | 分类数据比较、排名分析 |
| pie (饼图) | basic_pie, doughnut, rose, nightingale | 占比分析、构成分析 | 
| scatter (散点图) | basic_scatter, bubble, effect_scatter | 相关性分析、多维数据展示 |
| table (表格) | basic_table, conditional_table, heatmap_table | 精确数值展示、多维数据查看 |
| heatmap (热力图) | basic_heatmap | 密度分布、矩阵数据 |
| radar (雷达图) | basic_radar | 多维指标对比 |
| funnel (漏斗图) | basic_funnel | 转化流程分析 |
| gauge (仪表盘) | basic_gauge | 指标完成度、进度展示 |

前端应基于返回的`visualization_type`和`chart_info`字段判断展示方式，优先使用`echarts_option`字段中的完整配置实现可视化渲染。对于支持图表切换的场景，可利用`alternative_charts`字段提供用户选择其他图表类型的功能。

## 8. 集成说明

### 8.1 与sql2bi模块集成

系统的图表可视化功能由sql2bi模块提供支持，该模块能够根据SQL查询结果智能生成合适的图表。集成流程如下：

1. 接收用户数据查询请求
2. 执行SQL查询获取结果数据
3. 将SQL语句和结果传递给sql2bi模块
4. sql2bi分析数据特征，生成合适的图表配置
5. 将图表配置封装为visualization事件返回给前端

sql2bi模块支持多种图表类型的自动推荐，并可根据数据特征选择最合适的可视化方式。每次调用时，即使使用相同的SQL和数据，也可能返回不同的可视化建议，增加数据展示的多样性。

### 8.2 前端实现建议

前端应实现以下功能以充分利用接口能力：

1. 支持SSE流式接收和处理各类事件
2. 集成ECharts库用于渲染可视化内容
3. 实现图表类型切换功能，使用户可选择alternative_charts中提供的其他图表类型
4. 支持表格和图表的数据下载功能
5. 实现图表交互功能，如放大、缩小、数据筛选等

通过这些实现，可为用户提供丰富的数据可视化体验。 

## 9. 科幻风格可视化规范

机场智能客服系统采用科幻风格的可视化设计，为用户带来身临其境的未来科技感体验。

### 9.1 科幻视觉风格概述

可视化界面采用未来科技感设计，打造身临其境的科幻体验。设计灵感来源于先进的航空航天技术、未来机场概念和科幻电影美学，让用户在查询数据时仿佛置身于未来世界。

### 9.2 色彩方案

#### 9.2.1 主色调

- **深空蓝系列**：`#0A1629`, `#1A2943`, `#274060`
- **全息青色**：`#00F0FF`, `#00DBDE`, `#00A8E8`
- **离子紫色**：`#A742DF`, `#7B43E8`, `#6236FF`
- **能量赤橙**：`#FF5E3A`, `#FF2E63`, `#FB0094`

#### 9.2.2 科幻配色主题

- **太空舱主题**：深蓝背景配合霓虹蓝、电光紫光晕效果
- **全息投影主题**：半透明青色、钻石光效、微光粒子效果
- **量子计算主题**：深紫背景、亮蓝数据流、荧光绿能量线
- **火星基地主题**：深红背景、橙色能量、金属灰结构线

### 9.3 图表科幻化处理

#### 9.3.1 图表基础元素

- **坐标轴**：设计成发光线条，带脉冲动画
- **网格线**：使用虚线或点阵，具有微弱呼吸动效
- **背景**：深色渐变背景，添加星点或光线效果
- **标签**：采用未来感字体，配合光晕效果
- **图例**：设计成飘浮控制面板样式

#### 9.3.2 特殊图表效果

##### 折线图
- 发光轨迹线，线条边缘带模糊光晕
- 数据点使用明亮能量点，悬停时放大发光
- 区域填充使用半透明渐变，模拟全息投影

##### 柱状图
- 柱体设计成能量柱或全息投影
- 添加垂直扫描线动画和顶部粒子效果
- 柱体可使用光栅、电路图案或能量纹理

##### 饼图/环形图
- 扇区间添加发光分割线
- 扇区内使用透明渐变和能量流动纹理
- 悬停时扇区微微弹出并增强光效

##### 散点图
- 数据点设计为能量球或全息光点
- 添加光线连接相关数据点
- 背景可添加若隐若现的网格或引力场效果

##### 热力图
- 使用鲜艳的离子色彩渐变
- 添加能量波动或脉冲扩散动效
- 高值区域可添加光晕或粒子聚集效果

### 9.4 动效与交互

#### 9.4.1 科幻动效元素

- **数据加载**：模拟全息投影搭建过程，逐层构建
- **切换动画**：能量消散重组效果，类似传送或量子跃迁
- **悬停反馈**：光晕扩散、能量波纹、数据扫描线
- **点击反馈**：能量爆发、全息放大、界面波纹

#### 9.4.2 先进交互概念

- **全息缩放**：双手展开/收缩手势放大缩小图表
- **时空控制**：时间轴设计成可拖拽光束
- **语音交互**：支持语音命令控制图表变换
- **虚拟触控**：模拟悬浮触控面板，带反馈效果

### 9.5 科幻场景化展示

#### 9.5.1 航空监控中心风格

- 多重悬浮面板布局，主次分明
- 重要数据放置在视觉中心位置
- 边缘添加辅助数据流或监控元素
- 使用机场平面图作为背景元素

#### 9.5.2 驾驶舱视角

- 环形仪表盘布局，中央为主数据
- 周围环绕次要指标和趋势图
- 添加飞行参数和航路指示元素
- 操作按钮设计成驾驶舱控制面板风格

#### 9.5.3 空间站控制室

- 分区域浮动显示不同功能模块
- 中央大屏展示关键数据
- 侧边小屏显示辅助信息
- 添加状态指示灯和数据流动效果

### 9.6 科幻化图表组合示例

#### 9.6.1 航班流量监控台

- 中央为机场平面图热力图，显示实时人流
- 上方为航班频率折线图，带能量波动效果
- 右侧为航空公司分布全息环形图
- 左侧为实时数据流，展示航班起降信息

#### 9.6.2 延误预警系统

- 主视图为时间-延误热力地图，带天气因素叠加
- 右上角为延误原因分布全息饼图
- 左侧为航线负载全息条形图
- 底部为预测警告指标，带脉冲警示效果

#### 9.6.3 乘客体验监测站

- 中央雷达图展示满意度多维评分
- 环绕式时间轴展示评分趋势变化
- 侧边显示实时评论流，带情感分析指标
- 底部展示服务点状态，带故障预警系统

### 9.7 实现技术建议

#### 9.7.1 增强ECharts效果

- 使用渐变色、发光效果和粒子动画
- 自定义图表组件，添加科幻化图形元素
- 利用Canvas或WebGL提升绘制效能
- 添加背景特效和全局动画层

#### 9.7.2 高级动效实现

- 利用ECharts内置动画API
- 结合CSS动画增强UI元素效果
- 使用粒子库如Particles.js创建背景效果
- 采用WebGL着色器实现高级光效

#### 9.7.3 全息风格实现方案

- 使用CSS 3D变换创建视觉深度
- 半透明层叠创建全息投影错觉
- 模糊与锐利对比强化全息感
- 添加扫描线和噪点增强科技质感

### 9.8 设备适配考虑

- **大屏显示**：完整呈现控制中心级科幻效果
- **平板设备**：简化布局，保留核心动效
- **移动终端**：优化关键视觉元素，确保性能流畅

通过以上设计规范，机场智能客服系统将为用户带来身临其境的未来科幻体验，使数据不仅具有分析价值，更具有视觉震撼力和未来感，让用户在获取信息的同时享受科技带来的美感体验。 