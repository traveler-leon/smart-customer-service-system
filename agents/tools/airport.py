from langchain_core.tools import tool



@tool
def airport_knowledge_query(question: str) -> str:
    """
    查询乘机相关知识的工具
    
    此工具用于回答用户关于乘机过程中的各类问题，包括但不限于安检流程、行李规定、
    登机手续、值机办理、航班延误处理等常见乘机知识。
    
    Args:
        question: 用户提出的乘机相关问题，应当是一个完整的问句，例如"液体可以带多少上飞机？"
                 "行李超重怎么办？"或"如何办理值机手续？"等
    Examples:
        >>> airport_knowledge_query("安检需要注意什么？")
        "乘客需要通过安检门，随身行李需要通过X光机检查。液体不超过100ml，需要放在透明袋中。"
    """
    pass


