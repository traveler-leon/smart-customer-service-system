import asyncio
from typing import List, Dict, Any, Optional, Union
from common.logging import get_logger
from .interfaces import AsyncLLMProvider, AsyncVectorStore, AsyncDBConnector, AsyncMiddleware, AsyncEmbeddingProvider

# 获取日志记录器
logger = get_logger("text2sql.base")

class AsyncSmartSqlBase:
    """异步Text2SQL基础类"""
    
    def __init__(self, 
                 llm_provider: Optional[AsyncLLMProvider] = None,
                 embedding_provider: Optional[AsyncEmbeddingProvider] = None,
                 vector_store: Optional[AsyncVectorStore] = None,
                 db_connector: Optional[AsyncDBConnector] = None,
                 middlewares: List[AsyncMiddleware] = None,
                 config: Dict[str, Any] = None):
        
        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.db_connector = db_connector
        self.middlewares = middlewares or []
        self.config = config or {}
        self.dialect = self.config.get("dialect", "SQL")
        self.language = self.config.get("language", None)
        self.max_tokens = self.config.get("max_tokens", 14000)
        
        logger.info(f"初始化AsyncSmartSqlBase，配置信息：dialect={self.dialect}, language={self.language}, max_tokens={self.max_tokens}")
    
    async def initialize(self) -> None:
        """异步初始化组件"""
        logger.info("开始初始化AsyncSmartSqlBase组件")
        # 创建连接池和初始化其他资源
        if self.db_connector:
            await self.db_connector.connect()
        logger.info("AsyncSmartSqlBase组件初始化完成")
    
    async def shutdown(self) -> None:
        """异步关闭资源"""
        logger.info("开始关闭AsyncSmartSqlBase资源")
        if self.db_connector:
            await self.db_connector.close()
        logger.info("AsyncSmartSqlBase资源关闭完成")
    
    async def generate_embedding(self, text: str, **kwargs) -> List[float]:
        """异步生成文本嵌入向量"""
        return await self.embedding_provider.generate_embedding(text, **kwargs)
    
    async def generate_sql(self, question: str, allow_llm_to_see_data=False, **kwargs) -> str:
        """异步生成SQL查询"""
        logger.info(f"开始生成SQL，问题：{question}")
        
        # 应用请求中间件
        request = {'question': question, 'kwargs': kwargs}
        for middleware in self.middlewares:
            request = await middleware.process_request(request)
        
        question = request['question']
        kwargs = request['kwargs']
        
        try:
            # 并行获取相关信息
            logger.debug("并行获取相关信息")
            question_sql_task = self.vector_store.get_similar_question_sql(question, **kwargs)
            ddl_task = self.vector_store.get_related_ddl(question, **kwargs)
            doc_task = self.vector_store.get_related_documentation(question, **kwargs)
            
            # 等待所有异步任务完成
            question_sql_list, ddl_list, doc_list = await asyncio.gather(
                question_sql_task, ddl_task, doc_task
            )
            
            # 构建提示
            logger.debug("构建SQL提示")
            prompt = await self._get_sql_prompt(
                question=question,
                question_sql_list=question_sql_list,
                ddl_list=ddl_list,
                doc_list=doc_list,
                **kwargs
            )
            
            # 调用异步LLM
            logger.debug("调用LLM生成回答")
            llm_response = await self.llm_provider.submit_prompt(prompt, **kwargs)
            logger.debug(f"LLM回答: {llm_response}")
            
            # 处理中间SQL(如果需要数据库内省)
            if 'intermediate_sql' in llm_response and allow_llm_to_see_data:
                intermediate_sql = await self._extract_sql(llm_response)
                logger.info(f"执行中间SQL进行数据探索: {intermediate_sql}")
                try:
                    df = await self.db_connector.run_sql(intermediate_sql)
                    # 构建新提示包含数据结果
                    updated_doc_list = doc_list + [
                        f"The following is a pandas DataFrame with the results of the intermediate SQL query {intermediate_sql}: \n" + df.to_markdown()
                    ]
                    prompt = await self._get_sql_prompt(
                        question=question,
                        question_sql_list=question_sql_list,
                        ddl_list=ddl_list,
                        doc_list=updated_doc_list,
                        **kwargs
                    )
                    llm_response = await self.llm_provider.submit_prompt(prompt, **kwargs)
                except Exception as e:
                    logger.error(f"执行中间SQL失败: {str(e)}")
                    return f"Error running intermediate SQL: {e}"
            
            # 异步提取最终SQL
            sql = await self._extract_sql(llm_response)
            logger.info(f"提取的最终SQL: {sql}")
            
            # 应用响应中间件
            response = sql
            for middleware in self.middlewares:
                response = await middleware.process_response(response)
            
            return response
        except Exception as e:
            # 异步处理异常
            logger.error(f"SQL生成失败: {str(e)}", exc_info=True)
            for plugin in getattr(self, 'plugins', []):
                await plugin.on_error(e, question=question, **kwargs)
            raise
    
    async def _get_sql_prompt(self, question, question_sql_list, ddl_list, doc_list, **kwargs):
        """异步构建SQL生成提示"""
        # 根据配置构建系统提示
        initial_prompt = self.config.get("initial_prompt", None)
        system_prompt = []
        
        if initial_prompt:
            system_prompt.append(initial_prompt)
        
        system_prompt.append(f"你是一个SQL专家，精通{self.dialect}方言。")
        
        if self.language:
            system_prompt.append(f"请使用{self.language}语言回答。")
        
        # 构建用户提示
        user_prompt = [f"问题: {question}\n\n"]
        
        # 添加类似问题的SQL
        if question_sql_list:
            user_prompt.append("这里是一些类似问题及其SQL:\n")
            for item in question_sql_list:
                if isinstance(item, dict) and 'question' in item and 'sql' in item:
                    user_prompt.append(f"问题: {item['question']}\nSQL: {item['sql']}\n")
                elif isinstance(item, str):
                    user_prompt.append(f"{item}\n")
        
        # 添加相关DDL
        if ddl_list:
            user_prompt.append("\n数据库模式定义:\n")
            for ddl in ddl_list:
                user_prompt.append(f"{ddl}\n")
        
        # 添加相关文档
        if doc_list:
            user_prompt.append("\n相关文档:\n")
            for doc in doc_list:
                user_prompt.append(f"{doc}\n")
        
        # 添加最终指令
        user_prompt.append("\n请为此问题生成SQL查询。只需返回SQL代码，不要包含解释。")
        
        # 创建消息格式
        messages = [
            {"role": "system", "content": "\n".join(system_prompt)},
            {"role": "user", "content": "\n".join(user_prompt)}
        ]
        
        return messages
    
    async def _extract_sql(self, llm_response):
        """异步从LLM响应中提取SQL"""
        import re
        
        # 尝试各种模式提取SQL
        # 1. WITH CTE模式
        sqls = re.findall(r"\bWITH\b .*?;", llm_response, re.DOTALL)
        if sqls:
            return sqls[-1]
        
        # 2. SELECT语句
        sqls = re.findall(r"SELECT.*?;", llm_response, re.DOTALL)
        if sqls:
            return sqls[-1]
        
        # 3. 代码块(带SQL标签)
        sqls = re.findall(r"```sql\n(.*?)```", llm_response, re.DOTALL)
        if sqls:
            return sqls[-1].strip()
        
        # 4. 一般代码块
        sqls = re.findall(r"```(.*?)```", llm_response, re.DOTALL)
        if sqls:
            return sqls[-1].strip()
        
        # 5. 如果没有匹配，返回原始响应
        return llm_response
    
    async def run_sql(self, sql: str, **kwargs):
        """异步执行SQL查询"""
        return await self.db_connector.run_sql(sql, **kwargs)
