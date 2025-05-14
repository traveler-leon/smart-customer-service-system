from pydantic import BaseModel
from typing import Optional, Dict, Any, Union

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
