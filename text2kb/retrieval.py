"""
知识库API客户端
提供与知识库系统异步通信功能
"""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from .config import KB_ADDRESS, KB_API_KEY
from common.logging import get_logger

# 获取模块日志记录器
logger = get_logger("text2kb")

async def get_dataset_id(address: str, name: str, api_key: str) -> str:
    """
    异步获取知识库数据集ID
    
    Args:
        address: API地址
        name: 数据集名称
        api_key: API密钥
        
    Returns:
        数据集ID字符串，如果获取失败则返回空字符串
    """
    logger.info(f"获取数据集ID: {name}")
    # 构建API URL
    base_url = f"http://{address}/api/v1/datasets"
    # 设置查询参数
    params = {
        "page": 1,
        "page_size": 10,
        "orderby": "create_time",
        "name": name
    }
    # 设置请求头
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('data') and len(data['data']) > 0:
                        dataset_id = data['data'][0]['id']
                        logger.debug(f"成功获取数据集ID: {dataset_id} (数据集: {name})")
                        return dataset_id
                    logger.warning(f"数据集不存在: {name}")
                else:
                    logger.warning(f"获取数据集ID API请求失败，状态码: {response.status}")
                return ""
    except Exception as e:
        logger.error(f"获取数据集ID异常: {e}", exc_info=True)
        return ""


async def retrieve_from_kb(question: str, dataset_name: str, address: str = KB_ADDRESS, api_key: str = KB_API_KEY, similarity_threshold: float = 0.1, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    从知识库中检索信息
    
    Args:
        question: 问题文本
        dataset_name: 数据集名称
        address: API地址，默认从配置中获取
        api_key: API密钥，默认从配置中获取
        similarity_threshold: 相似度阈值，低于此值的结果将被标记，默认为0.1
        top_k: 检索结果数量上限，默认为10
        
    Returns:
        检索结果列表，包含内容和标记信息，按相关性排序
    """
    logger.info(f"开始从知识库检索: '{question[:50]}...' (数据集: {dataset_name}, top_k: {top_k})")
    try:
        dataset_id = await get_dataset_id(address, dataset_name, api_key)
        if not dataset_id:
            logger.warning(f"未找到数据集: {dataset_name}")
            return []

        retrieval_url = f"http://{address}/api/v1/retrieval"
        
        # 准备请求数据
        payload = {
            "question": question,
            "dataset_ids": [dataset_id],
            "top_k": top_k
        }
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        logger.debug(f"发送检索请求: {retrieval_url}")
        # 发送异步POST请求
        async with aiohttp.ClientSession() as session:
            async with session.post(retrieval_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    retrieval_data = await response.json()
                    all_content = sorted(
                        retrieval_data['data']['chunks'],
                        key=lambda x: x['vector_similarity'],
                        reverse=True
                    )
                    print("超找到的长度为：",len(all_content))
                    # 添加相似度标记
                    results = []
                    for content in all_content:
                        similarity = content['vector_similarity']
                        results.append({
                            'content': content['content'],
                            'similarity': similarity,
                            'low_similarity': similarity < similarity_threshold
                        })
                    logger.info(f"检索完成: 找到 {len(results)} 条结果 (数据集: {dataset_name})")
                    # 记录低相似度结果的数量
                    low_similarity_count = sum(1 for r in results if r['low_similarity'])
                    if low_similarity_count > 0:
                        logger.warning(f"有 {low_similarity_count} 条结果的相似度低于阈值 {similarity_threshold}")
                    return results
                else:
                    logger.error(f"检索请求失败，状态码: {response.status}")
                    return []
    except Exception as e:
        logger.error(f"检索异常: {e}", exc_info=True)
        return [] 