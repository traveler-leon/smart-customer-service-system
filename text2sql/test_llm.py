from .llm.qwen_llm import QwenLLM  # 使用绝对导入

async def main():
    # 初始化配置
    config = {
        "api_key": "sk-2e8c1dd4f75a44bf8114b337a5498a91",  # 替换为您的API密钥
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",  # 百炼服务的base_url
        "model": "qwen2.5-72b-instruct"  # 使用千问2.5-72B模型
    }
    
    # 创建LLM实例
    llm = QwenLLM(config)
    
    try:
        # 测试简单提示
        response = await llm.submit_prompt("你好，请介绍一下你自己。")
        print("简单提示响应:", response)
        
        # 测试多轮对话
        messages = [
            llm.system_message("你是一个专业的AI助手。"),
            llm.user_message("你好，请介绍一下你自己。"),
            llm.assistant_message("你好！我是一个AI助手，很高兴为你服务。"),
            llm.user_message("你能做什么？")
        ]
        response = await llm.submit_prompt(messages)
        print("\n多轮对话响应:", response)
        
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
    finally:
        # 关闭客户端
        await llm.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
