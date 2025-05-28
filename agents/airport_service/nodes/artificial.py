from collections import Counter
from difflib import SequenceMatcher

# 1. 用户明确请求转人工
def is_explicit_request(text):
    keywords = ["人工", "人工客服", "转人工", "转坐席", "客服", "工作人员", "服务人员"]
    return any(k in text for k in keywords)

# 2. 语义理解型请求
def is_implicit_request(text):
    phrases = ["不想和机器人聊", "叫个人来", "换个人", "找个人解决", "给我人来处理"]
    return any(p in text for p in phrases)

# 3. 情绪识别
def detect_emotion(texts):
    emotional_keywords = ["等了", "等了3小时", "重要会议", "必须赶上", "解决不了", "到底怎么办"]
    emotion_signs = ["！", "?", "你们", "不行"]
    text_blob = " ".join(texts)
    count = sum(k in text_blob for k in emotional_keywords) + sum(s in text_blob for s in emotion_signs)
    return count >= 3

# 4. 多轮对话相同问题（上下文连续问）
def is_multi_turn_repetition(dialogue):
    window = 3
    last_user_inputs = [text for role, text in dialogue[-window:] if role == "用户"]
    return len(set(last_user_inputs)) == 1 and len(last_user_inputs) >= 3

# 5. 同一问题重复3次（全局统计）
def is_exact_repeat(dialogue, threshold=3):
    user_inputs = [text for role, text in dialogue if role == "用户"]
    counter = Counter(user_inputs)
    return any(v >= threshold for v in counter.values())

# 6. 同一意思的问题重复3遍（语义相似判断）
def is_semantic_repeat(dialogue, threshold=3):
    user_inputs = [text for role, text in dialogue if role == "用户"]
    similar_groups = []

    for i, text1 in enumerate(user_inputs):
        group = [text1]
        for j in range(i + 1, len(user_inputs)):
            text2 = user_inputs[j]
            sim = SequenceMatcher(None, text1, text2).ratio()
            if sim > 0.75:
                group.append(text2)
        if len(group) >= threshold:
            return True
    return False

# 主判定函数
def should_transfer(dialogue):
    user_texts = [text for role, text in dialogue if role == "用户"]

    for text in user_texts:
        if is_explicit_request(text) or is_implicit_request(text):
            return True

    if detect_emotion(user_texts):
        return True
    if is_multi_turn_repetition(dialogue):
        return True
    if is_exact_repeat(dialogue):
        return True
    if is_semantic_repeat(dialogue):
        return True

    return False
