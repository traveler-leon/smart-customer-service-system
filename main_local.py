import os
import asyncio
from agents.airport_service import graph_manager,build_airport_service_graph

import uuid






# 使用示例
async def run_example():
    """运行示例"""
    # 确保data目录存在
    os.makedirs("data", exist_ok=True)
    # 注册自定义图
    graph_manager.register_graph("airport_service_graph", build_airport_service_graph())
    
    # 创建对话线程
    threads = {
        "configurable": {"thread_id": "123"}
    }
    
    print("==== 使用自定义图 'custom_graph' ====")
    print("开始交互式对话 (输入'退出'或'exit'结束)")
    
    while True:
        user_input = input("用户: ")
        if user_input.lower() in ["退出", "exit", "quit"]:
            print("对话已结束")
            break
            
        async for result in graph_manager.process_chat_message(message=user_input
                                                               ,thread_id=threads
                                                               ,graph_id="airport_service_graph"
                                                               ,output_node=["router","airport_assistant_node","flight_assistant_node","chitchat_node"]):
            print(result,flush=True)



# async def main():
#     graph = get_compiled_graph()
    
#     # 使用UUID作为thread_id
#     threads = {
#         "configurable": {"thread_id": str(uuid.uuid4())}
#     }
#     print("Hello from smart-customer-service-system!")
#     print("欢迎使用机场客服系统，请输入您的问题（输入'退出'结束对话）：")
#     while True:
#         user_input = input("用户: ")
#         if user_input.lower() in ["退出", "exit", "quit"]:
#             print("感谢使用机场客服系统，再见！")
#             break
        
#         async for msg,metadata in graph.astream({"messages": ("user", user_input)}, threads, stream_mode="messages"):
#            if msg.content and metadata["langgraph_node"] in ["router","airport_assistant_node","flight_assistant_node"]:
#               print(msg.content,flush=True)

def view_graph():
    try:
        graph = build_airport_service_graph()
        graph_image = graph.compile().get_graph().draw_mermaid_png()
        with open("main_graph.png", "wb") as f:
            f.write(graph_image)
    except Exception as e:
        print(e)


if __name__ == "__main__":
    asyncio.run(run_example())
    # view_graph()
