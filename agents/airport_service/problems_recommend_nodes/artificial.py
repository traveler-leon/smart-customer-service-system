import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from langchain_core.runnables import RunnableConfig
import torch
from transformers import pipeline
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from agents.airport_service.state import QuestionRecommendState
from agents.airport_service.core import emotion
from common.logging import get_logger

# 获取情感识别节点专用日志记录器
logger = get_logger("agents.problems-recommend-nodes.artificial")

_emotion_classifier = None
_emotion_mapping = {"Very Negative": 0, "Negative": 1, "Neutral": 2, "Positive": 3, "Very Positive": 4}

def initialize_emotion_classifier():
    """初始化情感分析分类器"""
    global _emotion_classifier
    
    if _emotion_classifier is not None:
        return _emotion_classifier
    try:
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        logger.info(f"情感分析模型使用设备: {device}")
        tokenizer = AutoTokenizer.from_pretrained(emotion["model_path"])
        model = AutoModelForSequenceClassification.from_pretrained(emotion["model_path"]).to(device)
        
        _emotion_classifier = pipeline(
            "text-classification",
            model=model,
            tokenizer=tokenizer,
            device=0 if torch.cuda.is_available() else -1
        )
        
        logger.info("情感分析模型初始化成功")
        return _emotion_classifier
        
    except Exception as e:
        logger.error(f"情感分析模型初始化失败: {e}")
        return None

def analyze_emotion_with_model(text: str)->dict:
    """使用深度学习模型进行情感分析"""
    global _emotion_classifier
    
    if _emotion_classifier is None:
        _emotion_classifier = initialize_emotion_classifier()
    
    try:
        result = _emotion_classifier(text)
        emotion_label = result[0]['label']
        confidence = result[0]['score']
        emotion_score = _emotion_mapping.get(emotion_label, 2)  # 默认为中性
                
        is_negative = emotion_score <= 1  # Very Negative 或 Negative
        return {
            "reason": "用户情绪已经非常的负面，需要转人工",
            "is_negative": is_negative
        }
        
    except Exception as e:
        logger.error(f"情感分析出错: {e}")
        return {
            "reason": "用户情绪中性，不需要转人工",
            "is_negative": False
        }

# 1. 用户明确请求转人工
def is_explicit_request(text:str)->bool:
    keywords = ["人工", "人工客服", "转人工", "转坐席", "客服", "工作人员", "服务人员"]
    return any(k in text for k in keywords)

# 2. 同一问题重复n次（全局统计）
def is_exact_repeat(messages: list, threshold: int = 3) -> bool:
    recent_human_messages = []
    
    for message in reversed(messages):
        if hasattr(message, '__class__') and message.__class__.__name__ == 'HumanMessage':
            recent_human_messages.append(message.content)
            if len(recent_human_messages) >= threshold:
                break
    if len(recent_human_messages) < threshold:
        return False
    first_content = recent_human_messages[0]
    return all(content == first_content for content in recent_human_messages)

# 主判定函数
def should_transfer(state: QuestionRecommendState,user_query:str):
    if is_explicit_request(user_query):
        return {"reason": "用户明确输入请求转人工", "is_negative": True}
    if is_exact_repeat(state["messages"]):
        return {"reason": "用户重复输入相同问题3 次，需要转人工", "is_negative": True}
    
    emotion_result = analyze_emotion_with_model(user_query)
    return  emotion_result
    

async def detect_emotion(state: QuestionRecommendState, config: RunnableConfig ):
    """
    情感识别节点
    
    Args:
        state: 当前状态对象
        config: 可运行配置
        store: 存储对象
    """
    Is_emotion = config["configurable"].get("Is_emotion", False)
    user_query = state.get("user_query") if state.get("user_query") else config["configurable"].get("user_query", "")
    logger.info(f"进入情感识别子智能体 - 是否需要情感识别: {Is_emotion},识别内容: {user_query}")

    if not Is_emotion:
        return state
    else:
        should_transfer_result = should_transfer(state,user_query)
        logger.info(f"情感识别结果: {should_transfer_result}")
        return {"emotion_result": should_transfer_result,"user_query":user_query}
