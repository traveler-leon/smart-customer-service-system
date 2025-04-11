from langchain_core.tools import tool



@tool
def question_clarification(question: str) -> str:
    """
    用户问题澄清工具。因为当前用户的问题在语法结构上不完整，需要继续澄清。
    
    Args:
        question: 用户需要进一步澄清的问题。
    Examples:
        >>> airport_knowledge_query("安检需要注意什么？")
        "乘客需要通过安检门，随身行李需要通过X光机检查。液体不超过100ml，需要放在透明袋中。"
    """
    pass


