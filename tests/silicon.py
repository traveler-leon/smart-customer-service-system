import os
from openai import OpenAI,AsyncOpenAI
import asyncio

client = AsyncOpenAI(
    api_key="sk-2e8c1dd4f75a44bf8114b337a5498a91",  # 如果您没有配置环境变量，请在此处用您的API Key进行替换
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"  # 百炼服务的base_url
)

async def main():
    # completion = await client.embeddings.create(
    #     model="BAAI/bge-large-zh-v1.5",
    #     input='我是谁.',
    #     encoding_format="float"
    # )
    # print(completion.usage.total_tokens,completion.data[0].embedding)


    completion = await client.chat.completions.create(
        model="qwen2.5-72b-instruct", # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        messages=[
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': '你是谁？'}],
        )
    print(completion.choices[0].message.content,completion.usage.prompt_tokens,completion.usage.completion_tokens)


if __name__ == "__main__":
    asyncio.run(main())


