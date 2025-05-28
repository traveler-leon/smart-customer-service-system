import requests
import json

def get_conversation_summary(token:str):
    url = 'http://127.0.0.1:8081/chat/v1/summary'
    headers = {
        'Content-Type': 'application/json',
        'token': token
    }
    payload = {
        'cid': "test_user_124",
        'msgid': "test_msg_124"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()
    return data

def get_human_agent_conversation_summary(token: str):
    url = 'http://127.0.0.1:8081/chat/v1/human-agent-summary'
    headers = {
        'Content-Type': 'application/json',
        'token': token
    }
    payload = {
        'cid': "test_user_124",
        'msgid': "test_msg_124",
        'conversation_list': [
            {"role": "user", "content": "你好，人工客服在吗？"},
            {"role": "agent", "content": "您好，请问有什么可以帮您？"},
            {"role": "user", "content": "我想咨询下航班延误怎么办？"},
            {"role": "agent", "content": "请问您的航班号是多少？我帮您查询。"}
        ]
    }
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()
    return data

if __name__ == "__main__":
    # res = get_conversation_summary("test_token_123")
    # print(res)
    print("\n---人工坐席摘要接口测试---")
    res2 = get_human_agent_conversation_summary("test_token_123")
    print(res2)