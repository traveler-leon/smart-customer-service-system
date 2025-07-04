from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Union, List

class UserInput(BaseModel):
    cid: str
    msgid: str
    query_txt: str
    partnerid: Optional[str] = None
    multi_params: Optional[Union[str, Dict[str, Any]]] = None

class SummaryRequest(BaseModel):
    cid: str
    msgid: str

class APIResponseItem(BaseModel):
    cid: str
    msgid: str
    answer_txt: Union[str, Dict[str, Any]]  # 允许字符串或字典
    answer_txt_type: str

class APIResponse(BaseModel):
    ret_code: str
    ret_msg: str
    item: APIResponseItem

class HumanAgentSummaryRequest(BaseModel):
    cid: str
    msgid: str
    conversation_list: list

# Text2SQL 训练相关模型
class TrainingDataItem(BaseModel):
    """单个训练数据项"""
    ddl: Optional[str] = Field(None, description="DDL语句")
    description: Optional[str] = Field(None, description="DDL描述")
    documentation: Optional[str] = Field(None, description="文档信息")
    question: Optional[str] = Field(None, description="问题")
    sql: Optional[str] = Field(None, description="SQL语句")
    tags: Optional[str] = Field(None, description="标签")

class TrainingRequest(BaseModel):
    """训练请求"""
    training_data: List[TrainingDataItem] = Field(..., description="训练数据列表")
    clear_existing: bool = Field(False, description="是否清除现有数据")

class TrainingResponse(BaseModel):
    """训练响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    success_count: int = Field(0, description="成功训练的数据条数")
    failed_count: int = Field(0, description="失败的数据条数")
    total_count: int = Field(0, description="总数据条数")

class ClearDataRequest(BaseModel):
    """清除数据请求"""
    collections: Optional[List[str]] = Field(None, description="要清除的集合列表，为空则清除所有")

class ClearDataResponse(BaseModel):
    """清除数据响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    cleared_collections: List[str] = Field([], description="已清除的集合列表")

# 机场聊天接口协议相关模型
class AirportChatRequest(BaseModel):
    """机场聊天请求模型"""
    thread_id: str = Field(..., description="会话标识，LangGraph利用此ID管理会话状态")
    user_id: str = Field(..., description="用户唯一标识，用于用户画像关联")
    query: str = Field(..., description="用户当前输入内容")
    stream: bool = Field(True, description="是否流式返回")
    metadata: Optional[Dict[str, Any]] = Field(None, description="可选的上下文信息，支持任意键值对")

class EventContent(BaseModel):
    """事件内容基础模型"""
    pass

class TextEventContent(EventContent):
    """文本事件内容"""
    text: str = Field(..., description="文本内容")
    format: str = Field("plain", description="文本格式：plain, markdown, html, rich, highlight")

class DataEventContent(EventContent):
    """数据事件内容"""
    data_type: str = Field(..., description="数据类型")
    data: Union[List[Dict[str, Any]], Dict[str, Any]] = Field(..., description="数据内容")
    sql: Optional[str] = Field(None, description="SQL查询语句")
    data_summary: Optional[str] = Field(None, description="数据摘要")

class ChartInfo(BaseModel):
    """图表信息"""
    chart_type: str = Field(..., description="图表类型")
    chart_subtype: str = Field(..., description="图表子类型")
    chart_name: str = Field(..., description="图表名称")

class AlternativeChart(BaseModel):
    """备选图表"""
    type: str = Field(..., description="图表类型")
    subtype: str = Field(..., description="图表子类型")
    name: str = Field(..., description="图表名称")

class VisualizationConfig(BaseModel):
    """可视化配置"""
    colors: Optional[List[str]] = Field(None, description="颜色配置")
    legend_position: Optional[str] = Field(None, description="图例位置")
    x_axis_label: Optional[str] = Field(None, description="X轴标签")
    y_axis_label: Optional[str] = Field(None, description="Y轴标签")

class SqlInfo(BaseModel):
    """SQL信息"""
    sql: str = Field(..., description="SQL查询语句")
    data_summary: str = Field(..., description="数据摘要")

class VisualizationEventContent(EventContent):
    """可视化事件内容"""
    visualization_type: str = Field(..., description="可视化类型")
    title: str = Field(..., description="标题")
    description: Optional[str] = Field(None, description="描述")
    data_reference: Optional[str] = Field(None, description="数据引用ID")
    chart_info: ChartInfo = Field(..., description="图表信息")
    config: Optional[VisualizationConfig] = Field(None, description="可视化配置")
    echarts_option: Dict[str, Any] = Field(..., description="ECharts配置选项")
    sql_info: Optional[SqlInfo] = Field(None, description="SQL信息")
    alternative_charts: Optional[List[AlternativeChart]] = Field(None, description="备选图表")

class FormField(BaseModel):
    """表单字段"""
    id: str = Field(..., description="字段ID")
    type: str = Field(..., description="字段类型")
    label: str = Field(..., description="字段标签")
    value: Optional[str] = Field(None, description="字段值")
    placeholder: Optional[str] = Field(None, description="占位符")
    required: bool = Field(False, description="是否必填")
    validation: Optional[Dict[str, Any]] = Field(None, description="验证规则")

class FormButton(BaseModel):
    """表单按钮"""
    id: str = Field(..., description="按钮ID")
    label: str = Field(..., description="按钮标签")
    type: str = Field(..., description="按钮类型")

class FormEventContent(EventContent):
    """表单事件内容"""
    form_id: str = Field(..., description="表单ID")
    title: str = Field(..., description="表单标题")
    description: Optional[str] = Field(None, description="表单描述")
    action: str = Field(..., description="表单提交地址")
    fields: List[FormField] = Field(..., description="表单字段")
    buttons: List[FormButton] = Field(..., description="表单按钮")

class EndEventContent(EventContent):
    """结束事件内容"""
    suggestions: Optional[List[str]] = Field(None, description="建议操作")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class ErrorEventContent(EventContent):
    """错误事件内容"""
    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误消息")

class ChatEvent(BaseModel):
    """聊天事件模型"""
    id: str = Field(..., description="事件唯一标识")
    sequence: int = Field(..., description="事件序号")
    content: Union[TextEventContent, DataEventContent, VisualizationEventContent, FormEventContent, EndEventContent, ErrorEventContent] = Field(..., description="事件内容")
