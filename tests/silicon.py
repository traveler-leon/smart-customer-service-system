import os
from openai import OpenAI,AsyncOpenAI
import asyncio

client = AsyncOpenAI(
    api_key="sk-zcewmhyhkaelmhrijbipqbrlfxhwnfbuegcpynkhdbzkqixd",  # 如果您没有配置环境变量，请在此处用您的API Key进行替换
    base_url="https://api.siliconflow.cn/v1"  # 百炼服务的base_url
)

async def main():
    completion = await client.embeddings.create(
        model="BAAI/bge-large-zh-v1.5",
        input='我是谁.',
        encoding_format="float"
    )
    print(completion.usage.total_tokens,completion.data[0].embedding)



if __name__ == "__main__":
    asyncio.run(main())


