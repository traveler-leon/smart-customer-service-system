from .embedding.qwen_model import QwenEmbedding  # 使用绝对导入

async def main():
    # 初始化配置
    config = {
        "api_key": "sk-2e8c1dd4f75a44bf8114b337a5498a91",  # 替换为您的API密钥
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",  # 服务的base_url
        "embedding_model": "text-embedding-v3"  # 使用的嵌入模型
    }
    
    # 创建Embedding实例
    embedding_provider = QwenEmbedding(config)
    
    try:
        # 测试单个文本嵌入
        text = "这是一段用于测试嵌入功能的示例文本。"
        result = await embedding_provider.generate_embedding(text)
        
        print("文本嵌入结果:")
        print(f"嵌入向量维度: {len(result['embedding'])}")
        print(f"使用的token数量: {result['tokens_used']}")
        
        # 打印嵌入向量的前5个元素作为示例
        print(f"嵌入向量前5个元素: {result['embedding'][:5]}")
        
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        
    finally:
        # 关闭客户端
        await embedding_provider.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 