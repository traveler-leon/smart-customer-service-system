"""
向量存储工具函数，用于知识库检索
"""

import os
from typing import List, Dict, Any, Optional
import numpy as np


class MockVectorStore:
    """模拟向量存储实现，用于开发测试
    
    生产环境中应替换为实际的向量数据库，如FAISS、Chroma等
    """
    
    def __init__(self):
        """初始化模拟向量存储"""
        # 模拟机场知识库
        self.documents = [
            {
                "id": "doc1",
                "content": "机场安检规定：旅客不能随身携带超过100ml的液体。所有液体需要装在透明袋子里。",
                "metadata": {"category": "安检", "subcategory": "液体限制"}
            },
            {
                "id": "doc2",
                "content": "刀具限制：折叠刀、水果刀、菜刀等各类刀具禁止随身携带，但可以托运。托运时需要妥善包装，刀尖有保护套。",
                "metadata": {"category": "安检", "subcategory": "刀具", "types": ["折叠刀", "水果刀", "菜刀"]}
            },
            {
                "id": "doc3",
                "content": "机场餐厅位于T3航站楼2层和3层，包括肯德基、星巴克、云海肴等多家餐厅。营业时间一般为早6点至晚10点。",
                "metadata": {"category": "设施", "subcategory": "餐厅", "terminal": "T3"}
            },
            {
                "id": "doc4",
                "content": "航站楼之间可以通过免费摆渡车转换，摆渡车大约每15分钟一班。",
                "metadata": {"category": "交通", "subcategory": "摆渡车"}
            },
            {
                "id": "doc5",
                "content": "机场行李寄存处位于各航站楼的一层，收费标准为每件行李每天50元。",
                "metadata": {"category": "服务", "subcategory": "行李寄存"}
            },
            {
                "id": "doc6",
                "content": "婴儿车、轮椅可以免费托运，不计入行李额。",
                "metadata": {"category": "行李", "subcategory": "特殊物品"}
            },
            {
                "id": "doc7",
                "content": "国内航班值机时间一般在起飞前2小时开始，国际航班值机时间通常在起飞前3小时开始。请至少提前90分钟到达机场办理值机手续。",
                "metadata": {"category": "值机", "subcategory": "时间"}
            },
            {
                "id": "doc8",
                "content": "儿童乘机规定：2周岁以下婴儿可免费搭乘国内航班；2-12周岁儿童需购买儿童票，通常为成人票价的五折。",
                "metadata": {"category": "票务", "subcategory": "儿童票"}
            },
            {
                "id": "doc9",
                "content": "不同类型的刀具有不同规定。厨房刀具如菜刀必须托运；随身携带的指甲刀长度必须小于6cm；户外折叠刀无论大小均禁止随身携带；装饰刀具视情况而定，需安检员判断。",
                "metadata": {"category": "安检", "subcategory": "刀具详细规定", "types": ["菜刀", "指甲刀", "折叠刀", "装饰刀"]}
            },
            {
                "id": "doc10",
                "content": "机场失物招领处位于每个航站楼的一层服务中心。拾获的物品将保存30天，超过期限未认领的将按照相关规定处理。",
                "metadata": {"category": "服务", "subcategory": "失物招领"}
            }
        ]
    
    def search(self, query: str, limit: int = 3) -> List[Dict]:
        """基于查询进行简单的关键词匹配搜索
        
        实际实现中应该使用向量相似度搜索
        """
        results = []
        
        # 使用简单的关键词匹配模拟相似度搜索
        for doc in self.documents:
            # 计算简单的相似度分数（实际应用中应使用余弦相似度等）
            score = self._simple_similarity(query, doc["content"])
            if score > 0:
                results.append({
                    "id": doc["id"],
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "score": score
                })
        
        # 按相似度降序排序并返回前limit个结果
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def _simple_similarity(self, query: str, text: str) -> float:
        """计算简单的相似度分数"""
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        
        # 交集中的词数除以查询词数，简单模拟相关性
        if len(query_words) == 0:
            return 0
        
        # 匹配的词占比
        score = len(query_words.intersection(text_words)) / len(query_words)
        
        # 奖励包含更多查询词的文档
        term_freq_bonus = min(1.0, len(query_words.intersection(text_words)) / 5)
        
        # 组合得分
        combined_score = 0.7 * score + 0.3 * term_freq_bonus
        
        return combined_score


# 创建默认向量存储实例
default_vector_store = MockVectorStore() 