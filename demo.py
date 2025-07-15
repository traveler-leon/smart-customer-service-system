import requests

url = "http://localhost:8081/api/v1/business-recommend/business"

headers = {
    "Content-Type": "application/json"
}

data = {
    "thread_id": "test-session-123",
    "user_id": "test-user-456",
    "query": "我行动不便？"
}

response = requests.post(url, json=data, headers=headers)

# 打印响应结果
print("Status code:", response.status_code)
print("Response JSON:", response.json())




