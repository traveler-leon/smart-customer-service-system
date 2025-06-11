import asyncio
import json
import websockets
from typing import Callable, Optional, Dict, Any

class ChatWebSocketClient:
    def __init__(self, url: str, token: str = ''):
        self.url = url
        self.token = token
        self.websocket = None
        self.message_callbacks = {}

    async def connect(self):
        """建立WebSocket连接"""
        try:
            self.websocket = await websockets.connect(self.url)
            print("WebSocket连接已建立")
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False

    async def send_message(
        self,
        cid: str,
        msgid: str,
        query_txt: str,
        multi_params: Optional[Dict[str, Any]] = None,
        on_token: Optional[Callable[[str, Dict], None]] = None
    ) -> str:
        """发送消息并接收响应"""
        if not self.websocket:
            raise Exception("WebSocket连接未建立")

        message = {
            "cid": cid,
            "msgid": msgid,
            "query_txt": query_txt,
            "token": self.token
        }

        if multi_params:
            message["multi_params"] = multi_params

        # 发送消息
        await self.websocket.send(json.dumps(message, ensure_ascii=False))

        full_response = ""

        # 接收响应
        async for response in self.websocket:
            try:
                data = json.loads(response)

                if data.get("event") == "start":
                    print(f"消息 {msgid} 开始处理")

                elif data.get("event") == "end":
                    print(f"\n消息 {msgid} 处理完成")
                    break

                elif data.get("error"):
                    raise Exception(f"服务器错误: {data['error']}")

                elif data.get("item") and data["item"].get("answer_txt"):
                    token = data["item"]["answer_txt"]
                    full_response += token

                    if on_token:
                        on_token(token, data)
                    else:
                        print(token, end="", flush=True)

            except json.JSONDecodeError as e:
                print(f"解析响应失败: {e}")

        return full_response

    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()

# 测试函数
async def test_basic_chat(client):
    """测试基础聊天功能"""
    print("\n" + "="*50)
    print("测试基础聊天功能")
    print("="*50)
    
    response = await client.send_message(
        cid="user123",
        msgid="msg001",
        query_txt="你好，请问你是谁？"
    )
    print(f"\n完整响应: {response}")

async def test_translate_function(client):
    """测试翻译功能"""
    print("\n" + "="*50)
    print("测试翻译功能 (Is_translate=True)")
    print("="*50)
    
    # 测试中文翻译为英文
    print("\n--- 测试中文翻译 ---")
    response1 = await client.send_message(
        cid="user123",
        msgid="msg002",
        query_txt="你好，我想预订一张机票去北京",
        multi_params={"Is_translate": True, "Is_emotion": False}
    )
    print(f"\n完整响应: {response1}")
    
    # 测试英文翻译
    print("\n--- 测试英文翻译 ---")
    response2 = await client.send_message(
        cid="user123",
        msgid="msg003",
        query_txt="Hello, I would like to book a flight to Beijing",
        multi_params={"Is_translate": True, "Is_emotion": False}
    )
    print(f"\n完整响应: {response2}")

async def test_emotion_function(client):
    """测试情感识别功能"""
    print("\n" + "="*50)
    print("测试情感识别功能 (Is_emotion=True)")
    print("="*50)
    
    # 测试积极情感
    print("\n--- 测试积极情感 ---")
    response1 = await client.send_message(
        cid="user123",
        msgid="msg004",
        query_txt="我今天心情很好，想要预订一个愉快的旅行！",
        multi_params={"Is_translate": False, "Is_emotion": True}
    )
    print(f"\n完整响应: {response1}")
    
    # 测试消极情感
    print("\n--- 测试消极情感 ---")
    response2 = await client.send_message(
        cid="user123",
        msgid="msg005",
        query_txt="我对你们的服务很不满意，航班延误让我很生气！",
        multi_params={"Is_translate": False, "Is_emotion": True}
    )
    print(f"\n完整响应: {response2}")
    
    # 测试中性情感
    print("\n--- 测试中性情感 ---")
    response3 = await client.send_message(
        cid="user123",
        msgid="msg006",
        query_txt="请帮我查询明天北京到上海的航班信息",
        multi_params={"Is_translate": False, "Is_emotion": True}
    )
    print(f"\n完整响应: {response3}")

async def test_combined_function(client):
    """测试翻译和情感识别组合功能"""
    print("\n" + "="*50)
    print("测试翻译+情感识别组合功能")
    print("="*50)
    
    response = await client.send_message(
        cid="user123",
        msgid="msg007",
        query_txt="I'm very excited about my upcoming trip to China!",
        multi_params={"Is_translate": True, "Is_emotion": True}
    )
    print(f"\n完整响应: {response}")

async def run_all_tests():
    """运行所有测试"""
    client = ChatWebSocketClient('ws://localhost:8081/chat/v1/ws', 'test_token')

    try:
        # 建立连接
        if await client.connect():
            # 运行各项测试
            await test_basic_chat(client)
            # await test_translate_function(client)
            # await test_emotion_function(client)
            # await test_combined_function(client)
            
        else:
            print("无法建立WebSocket连接，请检查服务器是否启动")

    except Exception as e:
        print(f"测试失败: {e}")
    finally:
        await client.close()

# 单独测试某个功能的函数
async def test_single_feature():
    """单独测试某个功能"""
    client = ChatWebSocketClient('ws://localhost:8081/chat/v1/ws', 'test_token')
    
    try:
        if await client.connect():
            print("请选择要测试的功能:")
            print("1. 基础聊天")
            print("2. 翻译功能")
            print("3. 情感识别")
            print("4. 翻译+情感识别")
            print("5. 全部测试")
            
            choice = input("请输入选择 (1-5): ")
            
            if choice == "1":
                await test_basic_chat(client)
            elif choice == "2":
                await test_translate_function(client)
            elif choice == "3":
                await test_emotion_function(client)
            elif choice == "4":
                await test_combined_function(client)
            elif choice == "5":
                await run_all_tests()
                return
            else:
                print("无效选择")
                
    except Exception as e:
        print(f"测试失败: {e}")
    finally:
        await client.close()

# 运行测试
if __name__ == "__main__":
    print("WebSocket功能测试程序")
    print("确保服务器已启动在 localhost:8081")
    print("-" * 50)
    
    # 直接运行所有测试
    asyncio.run(run_all_tests())
    
    # 如果想要交互式选择，可以使用：
    # asyncio.run(test_single_feature())
