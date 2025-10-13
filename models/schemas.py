from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any, Union, List

class SummaryRequest(BaseModel):
    cid: str
    msgid: str

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
class EventContent(BaseModel):
    """事件内容基础模型"""
    pass

class TextEventContent(EventContent):
    """文本事件内容"""
    text: str = Field(..., description="文本内容")
    format: str = Field("plain", description="文本格式：plain, markdown, html, rich, highlight")

class RichContentImage(BaseModel):
    """富文本内容中的图片对象"""
    id: str = Field(..., description="图片唯一标识")
    content_type: str = Field(..., description="图片MIME类型")
    data: str = Field(..., description="Base64编码的图片数据")
    alt_text: Optional[str] = Field(None, description="图片替代文本")
    description: Optional[str] = Field(None, description="图片描述")

class RichContentEventContent(EventContent):
    """富文本内容事件"""
    text: str = Field(..., description="文本内容")
    format: str = Field("plain", description="文本格式：plain, markdown")
    images: Optional[List[RichContentImage]] = Field(None, description="图片数组")
    layout: str = Field("text_first", description="布局方式：text_first, image_first, text_image_mixed, image_gallery")

class DataEventContent(EventContent):
    """数据事件内容"""
    data_type: str = Field(..., description="数据类型")
    data: Union[List[Dict[str, Any]], Dict[str, Any]] = Field(..., description="数据内容")
    sql: Optional[str] = Field(None, description="SQL查询语句")
    data_summary: Optional[str] = Field(None, description="数据摘要")

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

class FlightInfo(BaseModel):
    """航班信息"""
    flight_number: str = Field(..., description="航班号")
    flight_status: Optional[str] = Field(None, description="航班状态")
    abnormal_status: Optional[str] = Field(None, description="异常状态")
    abnormal_reason: Optional[str] = Field(None, description="异常原因")
    
    # 出发信息
    departure_station: Optional[str] = Field(None, description="出发机场")
    departure_terminal: Optional[str] = Field(None, description="出发航站楼")
    scheduled_departure_time: Optional[str] = Field(None, description="计划出发时间")
    changed_departure_time: Optional[str] = Field(None, description="变更出发时间")
    actual_departure_time: Optional[str] = Field(None, description="实际出发时间")
    
    # 到达信息
    destination_station: Optional[str] = Field(None, description="目的地机场")
    destination_terminal: Optional[str] = Field(None, description="到达航站楼")
    scheduled_arrival_time: Optional[str] = Field(None, description="计划到达时间")
    changed_arrival_time: Optional[str] = Field(None, description="变更到达时间")
    actual_arrival_time: Optional[str] = Field(None, description="实际到达时间")
    
    # 航线和航空公司信息
    full_route_path: Optional[str] = Field(None, description="完整航线路径")
    airline_twocharcode: Optional[str] = Field(None, description="航空公司两字代码")
    airline_company: Optional[str] = Field(None, description="航空公司名称")
    aircraft_type: Optional[str] = Field(None, description="机型")
    
    # 登机和服务信息
    boarding_gate: Optional[str] = Field(None, description="登机口")
    checkin_counter: Optional[str] = Field(None, description="值机柜台")
    baggage_carousel: Optional[str] = Field(None, description="行李转盘")
    
    # 登机时间信息
    scheduled_cut_off_time: Optional[str] = Field(None, description="计划截载时间")
    changed_cut_off_time: Optional[str] = Field(None, description="变更截载时间")
    actual_cut_off_time: Optional[str] = Field(None, description="实际截载时间")
    expected_security_check_duration: Optional[str] = Field(None, description="预计安检时长")
    scheduled_boarding_time: Optional[str] = Field(None, description="计划登机时间")
    changed_boarding_time: Optional[str] = Field(None, description="变更登机时间")
    actual_boarding_time: Optional[str] = Field(None, description="实际登机时间")
    scheduled_boarding_end_time: Optional[str] = Field(None, description="计划登机结束时间")
    changed_boarding_end_time: Optional[str] = Field(None, description="变更登机结束时间")
    actual_boarding_end_time: Optional[str] = Field(None, description="实际登机结束时间")
    expected_boarding_walking_duration: Optional[str] = Field(None, description="预计登机步行时长")
    
    # 其他信息
    shared_flight_number: Optional[str] = Field(None, description="共享航班号")
    subscribe_supported: bool = Field(..., description="是否支持订阅")
    airline_logo: Optional[str] = Field(None, description="航空公司logo")

class FlightListEventContent(EventContent):
    """航班列表事件内容"""
    title: str = Field(..., description="列表标题或提示信息")
    flights: List[FlightInfo] = Field(..., description="航班对象数组")
    action_hint: Optional[str] = Field(None, description="展示在前端的提示语")

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
    content: Union[TextEventContent, RichContentEventContent, DataEventContent, FormEventContent, FlightListEventContent, EndEventContent, ErrorEventContent] = Field(..., description="事件内容")



# 图片信息模型
class ImageData(BaseModel):
    """图片数据模型"""
    filename: str = Field(..., description="图片文件名")
    content_type: str = Field(..., description="图片MIME类型")
    data: str = Field(..., description="图片数据（base64编码）")

# 问题推荐接口相关模型
class QuestionRecommendRequest(BaseModel):
    """问题推荐请求模型"""
    thread_id: str = Field(..., description="会话标识")
    user_id: str = Field(..., description="用户唯一标识")
    query: Optional[str] = Field(None, description="用户当前输入内容")
    image: Optional[ImageData] = Field(None, description="可选的图片数据")
    metadata: Optional[Dict[str, Any]] = Field(None, description="可选的上下文信息")
    
    @model_validator(mode='after')
    def validate_query_or_image(self):
        if not self.query and not self.image:
            raise ValueError('query和image至少需要提供一个')
        return self

class RecommendedQuestion(BaseModel):
    """推荐问题模型"""
    question: str = Field(..., description="推荐的问题文本")
    confidence: Optional[float] = Field(None, description="推荐置信度")
    category: Optional[str] = Field(None, description="问题分类")

class QuestionRecommendResponse(BaseModel):
    """问题推荐响应模型"""
    ret_code: str = Field(..., description="返回码")
    ret_msg: str = Field(..., description="返回消息")
    item: Dict[str, Any] = Field(..., description="响应数据")

class QuestionRecommendItem(BaseModel):
    """问题推荐响应项模型"""
    thread_id: str = Field(..., description="会话标识")
    user_id: str = Field(..., description="用户标识")
    recommended_questions: List[str] = Field(..., description="推荐的问题列表")
    processing_time: Optional[str] = Field(None, description="处理时间")

# 商业推荐接口相关模型
class BusinessRecommendRequest(BaseModel):
    """商业推荐请求模型"""
    thread_id: str = Field(..., description="会话标识")
    user_id: str = Field(..., description="用户唯一标识")
    query: Optional[str] = Field(None, description="用户当前输入内容")
    image: Optional[ImageData] = Field(None, description="可选的图片数据")
    metadata: Optional[Dict[str, Any]] = Field(None, description="可选的上下文信息")
    
    @model_validator(mode='after')
    def validate_query_or_image(self):
        if not self.query and not self.image:
            raise ValueError('query和image至少需要提供一个')
        return self

class BusinessRecommendResponse(BaseModel):
    """商业推荐响应模型"""
    ret_code: str = Field(..., description="返回码")
    ret_msg: str = Field(..., description="返回消息")
    item: Dict[str, Any] = Field(..., description="响应数据")

class BusinessRecommendItem(BaseModel):
    """商业推荐响应项模型"""
    thread_id: str = Field(..., description="会话标识")
    user_id: str = Field(..., description="用户标识")
    recommended_business: List[str] = Field(..., description="推荐的业务列表")
    processing_time: Optional[str] = Field(None, description="处理时间")
