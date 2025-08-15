import os
from mem0 import AsyncMemory
import asyncio
from mem0.configs.base import MemoryConfig
from mem0.vector_stores.configs import VectorStoreConfig
from mem0.llms.configs import LlmConfig
from mem0.embeddings.configs import EmbedderConfig
from langchain_openai import OpenAIEmbeddings

from langchain_openai import ChatOpenAI


"""Wrapper around Xinference embedding models."""

from typing import Any, Dict, List, Optional

import requests
from langchain_core.embeddings import Embeddings


from xinference.client import AsyncRESTfulClient as _OrigAsync

class SafeAsyncClient(_OrigAsync):
    async def close(self):
        try:
            await super().close()
        except Exception:
            pass

    def __del__(self):
        # 覆盖原始 __del__，避免访问不存在的 session
        session = getattr(self, "session", None)
        if session:
            try:
                loop = asyncio.get_event_loop()
                # 创建任务安全关闭
                loop.create_task(self.close())
            except Exception:
                pass

class XinferenceEmbeddings(Embeddings):
    client: Any
    async_client: Any
    server_url: Optional[str]
    """URL of the xinference server"""
    model_uid: Optional[str]
    """UID of the launched model"""

    def __init__(
        self,
        server_url: Optional[str] = None,
        model_uid: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        try:
            from xinference.client import AsyncRESTfulClient, RESTfulClient
        except ImportError:
            try:
                from xinference_client import AsyncRESTfulClient, RESTfulClient
            except ImportError as e:
                raise ImportError(
                    "Could not import RESTfulClient from xinference. Please install it"
                    " with `pip install xinference` or `pip install xinference_client`."
                ) from e

        super().__init__()

        if server_url is None:
            raise ValueError("Please provide server URL")

        if model_uid is None:
            raise ValueError("Please provide the model UID")

        self.server_url = server_url

        self.model_uid = model_uid

        self._headers: Dict[str, str] = {}
        self._cluster_authed = False
        self._check_cluster_authenticated()
        if api_key is not None and self._cluster_authed:
            self._headers["Authorization"] = f"Bearer {api_key}"

        self.client = RESTfulClient(server_url, api_key)
        try:
            self.async_client = SafeAsyncClient(server_url, api_key)
        except RuntimeError:
            self.async_client = None

    def _check_cluster_authenticated(self) -> None:
        url = f"{self.server_url}/v1/cluster/auth"
        response = requests.get(url)
        if response.status_code == 404:
            self._cluster_authed = False
        else:
            if response.status_code != 200:
                raise RuntimeError(f"Failed to get cluster information, detail: {response.json()['detail']}")
            response_data = response.json()

            self._cluster_authed = bool(response_data["auth"])

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents using Xinference.
        Args:
            texts: The list of texts to embed.
        Returns:
            List of embeddings, one for each text.
        """

        model = self.client.get_model(self.model_uid)

        embeddings = [model.create_embedding(text)["data"][0]["embedding"] for text in texts]
        return [list(map(float, e)) for e in embeddings]

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents using Xinference.
        Args:
            texts: The list of texts to embed.
        Returns:
            List of embeddings, one for each text.
        """

        model = await self.async_client.get_model(self.model_uid)

        embeddings = [(await model.create_embedding(text))["data"][0]["embedding"] for text in texts]
        return [list(map(float, e)) for e in embeddings]

    def embed_query(self, text: str) -> List[float]:
        """Embed a query of documents using Xinference.
        Args:
            text: The text to embed.
        Returns:
            Embeddings for the text.
        """

        model = self.client.get_model(self.model_uid)

        embedding_res = model.create_embedding(text)

        embedding = embedding_res["data"][0]["embedding"]

        return list(map(float, embedding))

    async def aembed_query(self, text: str) -> List[float]:
        """Embed a query of documents using Xinference.
        Args:
            text: The text to embed.
        Returns:
            Embeddings for the text.
        """

        model = await self.async_client.get_model(self.model_uid)

        embedding_res = await model.create_embedding(text)

        embedding = embedding_res["data"][0]["embedding"]

        return list(map(float, embedding))
    
    async def close_async(self):
        if self.async_client:
            await self.async_client.close()
            self.async_client = None

    def __del__(self):
        # 防止原版析构逻辑意外执行
        try:
            del self.async_client
        except Exception:
            pass

os.environ["OPENAI_API_KEY"] = "6617719eb7df4c53a86670003c6.asoHZRafhFNhiA6o"
model = ChatOpenAI(
    model="glm-4.5",
    temperature=0.2,
    api_key="6617719eb7df4c53a8693a7b603c6.asoHZRafhFNhiA6o",
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

embedding = XinferenceEmbeddings(
    server_url="http://192.168.0.200:9997",
    model_uid="bge-large-zh-v1.5"
)

embedder = OpenAIEmbeddings(
    model="embedding-3",
    openai_api_type="6617719eb7df4c53a86c6.asoHZRafhFNhiA6o",
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)


config = MemoryConfig(
    llm=LlmConfig(
        provider="langchain",
        config={
            "model": model
        }
    ),
    vector_store=VectorStoreConfig(
        provider="chroma",
        config={
            "collection_name": "test",
            "host":"192.168.0.200",
            "port":"7996"
        }
    ),
    embedder=EmbedderConfig(
        provider="langchain",
        config={
        "model": embedding
        }
    ),
)

m = AsyncMemory(config=config)
# messages = [
#     {"role": "user", "content": "I'm planning to watch a movie tonight. Any recommendations?"},
#     {"role": "assistant", "content": "How about a thriller movies? They can be quite engaging."},
#     {"role": "user", "content": "I’m not a big fan of thriller movies but I love sci-fi movies."},
#     {"role": "assistant", "content": "Got it! I'll avoid thriller recommendations and suggest sci-fi movies in the future."}
# ]

from collections.abc import Coroutine

async def safe_get_all(memory, **kwargs):
    """
    安全获取所有记忆，兼容返回协程的旧版本 mem0。
    """
    result = await memory.get_all(**kwargs)
    
    # 检查 result["results"] 是否是一个协程对象（不创建新协程，避免警告）
    if isinstance(result.get("results"), Coroutine):
        result["results"] = await result["results"]
    
    return result


# 定义异步主函数
async def main():
    try:
        res = await m.add("坐飞机可以带刀吗？", user_id="alice", metadata={"category": "movies"},infer=False)
        # res = await m.search(query="What do you know about me?", user_id="alice")
        # res = await safe_get_all(m, user_id="alice")
        print("Memory added:", res)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        pass

if __name__ == "__main__":
    asyncio.run(main())