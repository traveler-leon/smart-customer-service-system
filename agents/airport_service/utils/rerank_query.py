import asyncio
import aiohttp


async def rerank_results(results, user_question,reranker_model=None,reranker_address=None,top_k=5):
    """
    异步重排序函数，使用 HTTP API 调用重排序模型
    """
    if not reranker_address or not reranker_model:
        print("重排序模型配置缺失，跳过重排序")
        return results
    # 构建文档列表
    documents = [item['content'].strip() for item in results]    
    # 构建 API 请求体
    payload = {
        "model": reranker_model,
        "query": user_question,
        "documents": documents
    }
    
    # 构建 API URL
    api_url = f"http://{reranker_address}/v1/rerank"
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            async with session.post(api_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result_data = await response.json()
                    
                    # 根据重排序结果重新排列原始结果
                    min_score = 0.0
                    if 'results' in result_data:
                        reranked_results = [{"content": documents[item["index"]], "similarity": item['relevance_score']} for item in result_data['results']]
                        # 确保有结果再取最大值
                        if reranked_results:
                            max_similarity = max(item["similarity"] for item in reranked_results)
                        else:
                            max_similarity = 0.0
                        return reranked_results[:top_k],max_similarity
                    else:
                        print("重排序响应格式异常，使用原始结果")
                        return results[:top_k],0.0
                else:
                    print(f"重排序 API 调用失败，状态码: {response.status}")
                    return results[:top_k],0.0
                    
    except Exception as e:
        print(f"重排序过程发生错误: {str(e)}")
        return results[:top_k],0.0