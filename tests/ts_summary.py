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

if __name__ == "__main__":
    res = get_conversation_summary("test_token_123")
    print(res)