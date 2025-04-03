import json
import chromadb
from typing import List, Dict, Any, Optional
from chromadb.config import Settings
import pandas as pd

from ..base.interfaces import AsyncVectorStore, AsyncEmbeddingProvider
from ..utils import deterministic_uuid
from common.logging import get_logger

logger = get_logger("text2sql.storage.chromadb")

class ChromadbStorage(AsyncVectorStore):
    """基于ChromaDB官方异步HTTP客户端的向量存储实现"""
    
    def __init__(self, config=None, embedding_provider: Optional[AsyncEmbeddingProvider] = None):
        self.config = config or {}
        
        # 基本配置
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 8000)
        self.collection_metadata = self.config.get("collection_metadata", {})
        self.n_results_sql = self.config.get("n_results_sql", self.config.get("n_results", 10))
        self.n_results_documentation = self.config.get("n_results_documentation", self.config.get("n_results", 10))
        self.n_results_ddl = self.config.get("n_results_ddl", self.config.get("n_results", 10))
        
        # 向量搜索配置
        hnsw_default = {
            "M": 16,                # 每个节点的最大出边数，增加可提高精度但降低速度
            "construction_ef": 100,  # 建立索引时考虑的邻居数，增加可提高精度但降低建立速度
            "search_ef": 50,         # 查询时考虑的邻居数，增加可提高查询精度但降低查询速度
            "space": "cosine"        # 向量空间距离计算方式，可选: cosine, l2, ip
        } 
        self.hnsw_config = self.config.get("hnsw_config", hnsw_default)
        # 嵌入提供者
        self.embedding_provider = embedding_provider
        
        # 客户端和集合 - 将在initialize中初始化
        self.client = None
        self.documentation_collection = None
        self.ddl_collection = None
        self.sql_collection = None
        
        logger.info(f"初始化ChromaDB异步存储: {self.host}:{self.port}")

    def _get_collection_metadata(self):
        """获取集合元数据 - 辅助方法，同步即可"""
        # 向量搜索配置参数
        return {
            "hnsw:M": self.hnsw_config["M"],
            "hnsw:construction_ef": self.hnsw_config["construction_ef"],
            "hnsw:search_ef": self.hnsw_config["search_ef"],
            "hnsw:space": self.hnsw_config["space"],
            **(self.collection_metadata or {})
        }
    
    async def initialize(self) -> None:
        """异步初始化ChromaDB客户端和集合"""
        logger.info("开始异步初始化ChromaDB客户端和集合")
        # 创建设置对象，只设置匿名遥测
        settings = Settings(anonymized_telemetry=False)
        # 使用参数创建异步HTTP客户端
        self.client = await chromadb.AsyncHttpClient(
            host=self.host,
            port=self.port,
            settings=settings
        )
        
        logger.info(f"ChromaDB异步客户端连接成功: {self.host}:{self.port}")
        # 创建文档集合
        self.documentation_collection = await self.client.get_or_create_collection(
            name="sql-documentation",
            metadata=self._get_collection_metadata()
        )
        
        # 创建DDL集合
        self.ddl_collection = await self.client.get_or_create_collection(
            name="sql-ddl",
            metadata=self._get_collection_metadata()
        )
        
        # 创建SQL集合
        self.sql_collection = await self.client.get_or_create_collection(
            name="sql-sql",
            metadata=self._get_collection_metadata()
        )
        logger.info("ChromaDB客户端和集合初始化完成")
    
    async def close(self) -> None:
        """关闭ChromaDB客户端"""
        if self.client:
            self.client = None
        logger.info("ChromaDB客户端已关闭")
    
    async def generate_embedding(self, data: str, **kwargs) -> List[float]:
        """使用嵌入提供者生成嵌入向量"""
        if not self.embedding_provider:
            raise ValueError("未配置嵌入提供者，无法生成嵌入向量")
        res = await self.embedding_provider.generate_embedding(data, **kwargs)

        return res["embedding"]
    async def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        """异步添加问题和SQL的映射"""
        await self.ensure_connection()  # 确保连接有效
        logger.info(f"添加问题SQL映射: {question[:30]}...")
        
        question_sql_json = json.dumps(
            {
                "question": question,
                "sql": sql,
            },
            ensure_ascii=False,
        )
        # 生成ID
        id = deterministic_uuid(question_sql_json) + "-sql"
        # 添加到集合 - 使用嵌入提供者生成嵌入
        embeddings = await self.generate_embedding(question, **kwargs)
        await self.sql_collection.add(
            documents=[question],
            embeddings=[embeddings],
            ids=[id],
            metadatas=[{"type":"sql-qa","detail": sql}]
        )
        
        logger.info(f"问题SQL映射添加成功, ID: {id}")
        return id
    
    async def add_ddl(self, ddl: str, **kwargs) -> str:
        """异步添加DDL语句"""
        await self.ensure_connection()  # 确保连接有效
        logger.info(f"添加DDL: {ddl[:30]}...")
        
        # 生成ID
        id = deterministic_uuid(ddl) + "-ddl"
        
        # 添加到集合 - 使用嵌入提供者生成嵌入
        embeddings = await self.generate_embedding(ddl, **kwargs)
        await self.ddl_collection.add(
            documents=[ddl],
            embeddings=[embeddings],
            ids=[id],
            metadatas=[{"type": "table-ddl"}]
        )
        
        logger.info(f"DDL添加成功, ID: {id}")
        return id
    
    async def add_documentation(self, documentation: str, **kwargs) -> str:
        """异步添加文档"""
        await self.ensure_connection()  # 确保连接有效
        logger.info(f"添加文档: {documentation[:30]}...")
        
        # 生成ID
        id = deterministic_uuid(documentation) + "-doc"
        
        # 添加到集合 - 使用嵌入提供者生成嵌入
        embeddings = await self.generate_embedding(documentation, **kwargs)
        await self.documentation_collection.add(
            documents=[documentation],
            embeddings=[embeddings],
            ids=[id],
            metadatas=[{"type": "table-documentation"}]
        )
        
        logger.info(f"文档添加成功, ID: {id}")
        return id
    
    async def get_training_data(self, **kwargs) -> pd.DataFrame:
        """异步获取训练数据"""
        await self.ensure_connection()  # 确保连接有效
        logger.info("获取训练数据...")
        df = pd.DataFrame()
        
        # 获取SQL数据
        sql_data = await self.sql_collection.get()
        if sql_data is not None:
            df_sql = pd.DataFrame({
                "id": sql_data["ids"],
                "question": sql_data["documents"],
                "content": [meta["detail"] for meta in sql_data["metadatas"]],
                "training_data_type":[meta["type"] for meta in sql_data["metadatas"]],
            })
            df = pd.concat([df, df_sql])
        # 获取DDL数据
        ddl_data = await self.ddl_collection.get()
        if ddl_data is not None:
            df_ddl = pd.DataFrame({
                "id": ddl_data["ids"],
                "question": [None for doc in ddl_data["documents"]],
                "content": ddl_data["documents"],
                "training_data_type":[meta["type"] for meta in ddl_data["metadatas"]],
            })
            df = pd.concat([df, df_ddl])
        # 获取文档数据
        doc_data = await self.documentation_collection.get()
        if doc_data is not None:
            df_doc = pd.DataFrame({
                "id": doc_data["ids"],
                "question": [None for doc in doc_data["documents"]],
                "content": doc_data["documents"],
                "training_data_type":[meta["type"] for meta in doc_data["metadatas"]],
            })
            df = pd.concat([df, df_doc])
        
        return df

    async def remove_training_data(self, id: str, **kwargs) -> bool:
        """异步移除训练数据"""
        await self.ensure_connection()  # 确保连接有效
        logger.info(f"移除训练数据: {id}")
        
        if id.endswith("-sql"):
            await self.sql_collection.delete(ids=[id])
            return True
            return True
        elif id.endswith("-ddl"):
            await self.ddl_collection.delete(ids=[id])
            return True
        elif id.endswith("-doc"):
            await self.documentation_collection.delete(ids=[id])
            return True
        else:
            return False

    async def remove_collection(self, collection_name: str) -> bool:
        """异步重置集合"""
        await self.ensure_connection()  # 确保连接有效
        logger.info(f"重置集合: {collection_name}")
        
        if collection_name == "sql-sql":
            await self.client.delete_collection(name="sql-sql")
            self.sql_collection = await self.client.get_or_create_collection(
                name="sql-sql", 
                metadata=self._get_collection_metadata()
            )
            return True
        elif collection_name == "sql-ddl":
            await self.client.delete_collection(name="sql-ddl")
            self.ddl_collection = await self.client.get_or_create_collection(
                name="sql-ddl", 
                metadata=self._get_collection_metadata()
            )
            return True
        elif collection_name == "sql-documentation":
            await self.client.delete_collection(name="sql-documentation")
            self.documentation_collection = await self.client.get_or_create_collection(
                name="sql-documentation", 
                metadata=self._get_collection_metadata()
            )
            return True
        else:
            return False

    @staticmethod
    def _extract_documents(query_results) -> list:
        """从查询结果中提取文档 - 纯数据处理，保持同步"""
        if query_results is None:
            return []
        print(f"query_results:{query_results}")
        if "documents" in query_results:
            documents = query_results["documents"][0]
            metadata = query_results["metadatas"][0]
            res = []
            try:
                if metadata[0]["type"]== "sql-qa":
                    res = [{"question":q,"sql":a['detail']} for q,a in zip(documents,metadata)]
                    print("res:",res)
                    return res
            except Exception:
                return documents
        return documents
        return []

    async def get_similar_question_sql(self, question: str, **kwargs) -> list:
        """异步获取类似问题的SQL"""
        await self.ensure_connection()  # 确保连接有效
        logger.info(f"查询类似问题SQL: {question[:30]}...")        
        # 使用嵌入提供者生成嵌入
        embedding = await self.generate_embedding(question, **kwargs)
        
        results = await self.sql_collection.query(
            query_embeddings=[embedding],
            n_results=self.n_results_sql
        )
        
        return self._extract_documents(results)
    
    async def get_related_ddl(self, question: str, **kwargs) -> list:
        """异步获取相关DDL语句"""
        await self.ensure_connection()  # 确保连接有效
        logger.info(f"查询相关DDL: {question[:30]}...")        
        # 使用嵌入提供者生成嵌入
        embeddings = await self.generate_embedding(question, **kwargs)
        
        results = await self.ddl_collection.query(
            query_embeddings=[embeddings],
            n_results=self.n_results_ddl
        )
        
        return self._extract_documents(results)
    
    async def get_related_documentation(self, question: str, **kwargs) -> list:
        """异步获取相关文档"""
        await self.ensure_connection()  # 确保连接有效
        logger.info(f"查询相关文档: {question[:30]}...")
        
        # 使用嵌入提供者生成嵌入
        embeddings = await self.generate_embedding(question, **kwargs)
        
        results = await self.documentation_collection.query(
            query_embeddings=[embeddings],
            n_results=self.n_results_documentation
        )
        
        return self._extract_documents(results)

    async def check_health(self) -> bool:
        """检查ChromaDB连接健康状态"""
        try:
            if self.client:
                res = await self.client.heartbeat()
                logger.debug(f"ChromaDB心跳检测成功: {res}")
                return True
            return False
        except Exception as e:
            logger.error(f"ChromaDB心跳检测失败: {str(e)}")
            return False

    async def ensure_connection(self) -> None:
        """确保连接有效，如果无效则重新连接"""
        if not self.client or not await self.check_health():
            logger.warning("ChromaDB连接不可用，尝试重新连接")
            await self.close()  # 关闭可能的无效连接
            await self.initialize()  # 重新初始化连接
