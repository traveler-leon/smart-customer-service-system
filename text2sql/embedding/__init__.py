"""
嵌入模型提供者模块

此模块提供了各种嵌入模型的实现，用于生成文本的向量表示。
默认支持基于OpenAI兼容接口的实现，可无缝切换不同供应商。
"""

from .qwen import QwenEmbedding
from .siliconflow import SiliconflowEmbedding

__all__ = ['QwenEmbedding', 'SiliconflowEmbedding'] 