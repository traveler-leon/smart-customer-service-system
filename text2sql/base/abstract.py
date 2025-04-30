import asyncio
from typing import List, Dict, Any, Optional, Union

import pandas as pd
from common.logging import get_logger
from .interfaces import AsyncLLMProvider, AsyncVectorStore, AsyncDBConnector, AsyncMiddleware, AsyncEmbeddingProvider
import time
from datetime import datetime, date
from decimal import Decimal

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
        self.max_tokens = self.config.get("llm", {}).get("max_tokens", 20000)
        
        logger.info(f"初始化AsyncSmartSqlBase，配置信息：dialect={self.dialect}, language={self.language}, max_tokens={self.max_tokens}")
    
    async def initialize(self) -> None:
        """异步初始化组件"""
        logger.info("开始初始化AsyncSmartSqlBase组件")
        # 创建连接池和初始化其他资源
        if self.db_connector:
            await self.db_connector.connect()
        if self.vector_store:
            await self.vector_store.initialize()
        logger.info("AsyncSmartSqlBase组件初始化完成")
    
    async def shutdown(self) -> None:
        """异步关闭资源"""
        logger.info("开始关闭AsyncSmartSqlBase资源")
        if self.db_connector:
            await self.db_connector.close()
        logger.info("AsyncSmartSqlBase资源关闭完成")
    
    async def generate_embedding(self, data: str, **kwargs) -> List[float]:
        """使用嵌入提供者生成嵌入向量"""
        if not self.embedding_provider:
            raise ValueError("未配置嵌入提供者，无法生成嵌入向量")
        res = await self.embedding_provider.generate_embedding(data, **kwargs)
        return res["embedding"]
    
    async def generate_sql(self, question: str, allow_llm_to_see_data=False, **kwargs) -> str:
        """异步生成SQL查询"""
        logger.info(f"开始生成SQL，问题：{question}")
        
        # 应用请求中间件
        request = {'question': question, 'kwargs': kwargs}
        for middleware in self.middlewares:
            request = await middleware.process_request(request)
        
        # 检查中间件是否返回了缓存结果
        if '__cached_result' in request:
            cached_result = request['__cached_result']
            # 返回SQL和缓存状态
            if isinstance(cached_result, dict) and 'sql' in cached_result:
                return cached_result['sql'], True  # True表示来自缓存
            return cached_result, True
        
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
            # logger.debug("构建SQL提示") 
            prompt = await self._get_sql_prompt(
                question=question,
                question_sql_list=question_sql_list,
                ddl_list=ddl_list,
                doc_list=doc_list,
                **kwargs
            )
            logger.info(f"构建SQL提示结束: {prompt}")
            # 调用异步LLM
            logger.info("调用LLM生成回答")
            llm_response = await self.llm_provider.submit_prompt(prompt, **kwargs)
            logger.info(f"LLM回答: {llm_response}")
            
            # 处理中间SQL(如果需要数据库内省)
            if 'intermediate_sql' in llm_response and allow_llm_to_see_data:
                intermediate_sql = await self._extract_sql(llm_response)
                logger.info(f"执行中间SQL进行数据探索: {intermediate_sql}")
                try:
                    result = await self.db_connector.run_sql(intermediate_sql)
                    if isinstance(result, dict) and result.get('error'):
                        # 处理错误情况
                        error_msg = result.get('message', '未知错误')
                        logger.error(f"执行中间SQL失败: {error_msg}")
                        result =  f"运行 intermediate SQL出错: {error_msg}"

                    # 确认是DataFrame后再使用
                    df = result
                    if isinstance(df, pd.DataFrame):
                        updated_doc_list = doc_list + [
                            f"下面是intermediate SQL查询结果: \n" + df.to_markdown()
                        ]
                    else:
                        updated_doc_list = doc_list + [
                            f"下面是intermediate SQL查询结果: \n" + df
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
            
            # 准备响应对象，包含原始问题和参数以便中间件处理
            response = sql
            
            # 为中间件添加必要信息
            if isinstance(response, dict):
                response['__original_question'] = question
                response['__original_kwargs'] = kwargs
            elif isinstance(response, str):
                # 如果是字符串结果，我们需要包装它
                response = {
                    'sql': response,
                    '__original_question': question,
                    '__original_kwargs': kwargs
                }
            
            # 应用响应中间件
            for middleware in self.middlewares:
                response = await middleware.process_response(response)
            
            # 如果结果被包装成了字典，但原始期望是字符串，需要解包
            if isinstance(response, dict) and 'sql' in response and not isinstance(sql, dict):
                return response['sql'], False
            
            # 返回生成的SQL和缓存状态(非缓存)
            return sql, False
        except Exception as e:
            # 异步处理异常
            logger.error(f"SQL生成失败: {str(e)}", exc_info=True)
            for plugin in getattr(self, 'plugins', []):
                await plugin.on_error(e, question=question, **kwargs)
            raise
    
    async def _get_sql_prompt(self, question, question_sql_list, ddl_list, doc_list, **kwargs):
        # 初始提示设置
        initial_prompt = self.config.get("initial_prompt", None)
        if initial_prompt is None:
            initial_prompt = f"""你是一个{self.dialect}专家。专门将自然语言问题翻译成可执行的SQL查询。
                                您的主要任务是基于提供的数据库上下文（`<database_context>`）、SQL方言（`<sql_dialect>`）、对话历史和用户的当前问题（`<question>`），生成一个单一的、语法正确的SQL查询。

                                **输出要求：**
                                - 您的**整个**输出必须是**以下之一**：
                                    1. 生成的SQL查询字符串。
                                - **不要**包含**任何**其他文本、解释、道歉、注释（除非是SQL本身的一部分）或超出单个SQL查询或 `INVALID_QUERY` 字符串的格式。
                                """
        # 按区段添加内容
        prompt = initial_prompt
        
        # 添加DDL信息（限制token）
        if ddl_list:
            tmp_ddl = ""
            for ddl in ddl_list:
                tmp_ddl += f"{ddl}\n\n"
            if self._estimate_tokens(prompt) + self._estimate_tokens(tmp_ddl) < self.max_tokens:
                prompt += f"""**输入：**
                        1. **数据库上下文 (<database_context>):** 包含表和列的模式（DDL）以及重要的描述/注释。
                        ```
                        <database_context>
                            <schema>{tmp_ddl}</schema>
                        </database_context>
                        """
        
        # 添加文档信息（限制token）
        if doc_list:
            tmp_doc = ""
            for doc in doc_list:
                tmp_doc += f"{doc}\n\n"
            if self._estimate_tokens(prompt) + self._estimate_tokens(tmp_doc) < self.max_tokens:
                prompt += f"<descriptions>{tmp_doc}</descriptions>"
        # 添加响应指南
        prompt += f"""
        2. **SQL方言 (<sql_dialect>):** 目标SQL方言。
            <sql_dialect>{self.dialect}</sql_dialect>

        **核心规则与逻辑：**

        1.  **上下文一致性：** 严格使用 `<database_context>` 中定义的元素（表、列）。参考 `<descriptions>` 以了解正确的使用方法、关系和语义含义。不要创建不存在的元素。
        2.  **方言兼容性：** 确保生成的SQL语法对于指定的 `<sql_dialect>` 是有效的。
        3.  **历史利用：** 分析历史对话，查找与本次问题有用的信息。
        4.  **意图解释：** 准确生成反映用户从 `<question>`、对话历史 和 `<descriptions>` 中推导出的意图的SQL。
        5.  **单一查询：** 生成一个单一的、有效的SQL语句。
        6.  **查询优化与精确性：** **优先选择回答用户问题所需的最少列。除非用户明确要求获取所有信息（例如，"显示该航班的所有细节"），否则应避免使用 `SELECT *`。**

        **处理说明：**

        1.  **分析所有输入：** 仔细检查 `<question>`、`<database_context>`（模式 + 描述）、`<sql_dialect>` 和 `<dialogue_history>`。
        2.  **将意图映射到上下文：** 确定用户的核心意图，使用历史记录和描述进行澄清，将其映射到数据库元素。
        3.  **构建SQL：** 如果没有满足失败条件，则构建SQL查询。确保正确性（连接、过滤、聚合、语法），以反映意图并遵守方言，**同时遵循查询优化与精确性规则**。
        4.  **最终输出：** **仅**输出生成的SQL字符串。
        **最终输出（SQL查询）：**

    """
        
        # 创建消息格式
        messages = [{"role": "system", "content": prompt}]
        
        # 添加示例问答对
        for example in question_sql_list:
            if isinstance(example, dict) and "question" in example and "sql" in example:
                messages.append({"role": "user", "content": example["question"]})
                messages.append({"role": "assistant", "content": example["sql"]})
        
        # 添加当前问题
        messages.append({"role": "user", "content": question})
        
        return messages
    
    async def _extract_sql(self, llm_response):
        """异步从LLM响应中提取SQL"""
        import re
        
        # 处理不同格式的LLM响应
        if isinstance(llm_response, dict) and "content" in llm_response:
            llm_response_text = llm_response["content"]
        elif isinstance(llm_response, str):
            llm_response_text = llm_response
        else:
            logger.warning(f"无法识别的LLM响应格式: {type(llm_response)}")
            return llm_response  # 返回原始响应
        # 尝试各种模式提取SQL
        # 1. WITH CTE模式
        sqls = re.findall(r"\bWITH\b .*?;", llm_response_text, re.DOTALL | re.IGNORECASE)
        if sqls:
            logger.debug(f"从WITH CTE模式提取SQL: {sqls[-1]}")
            return sqls[-1]
        
        # 2. SELECT语句
        sqls = re.findall(r"SELECT.*?;", llm_response_text, re.DOTALL | re.IGNORECASE)
        if sqls:
            logger.debug(f"从SELECT语句提取SQL: {sqls[-1]}")
            return sqls[-1]
        
        # 3. 代码块(带SQL标签)
        sqls = re.findall(r"```sql\n(.*?)```", llm_response_text, re.DOTALL | re.IGNORECASE)
        if sqls:
            logger.debug("从SQL代码块提取SQL")
            return sqls[-1].strip()
        
        # 4. 一般代码块
        sqls = re.findall(r"```(.*?)```", llm_response_text, re.DOTALL)
        if sqls:
            logger.debug("从一般代码块提取SQL")
            return sqls[-1].strip()
        
        # 5. 如果没有匹配，返回原始响应
        logger.warning("无法从LLM响应中提取SQL，返回原始响应")
        return llm_response
    
    async def run_sql(self, sql: str, **kwargs):
        """异步执行SQL查询"""
        result = await self.db_connector.run_sql(sql, **kwargs)
        return serialize_result(result)

    def _estimate_tokens(self, text):
        """估算文本的token数量"""
        return len(text) / 2  # 简单估算
    
    def split_data(self, text):
        """分割数据"""
        tmp = []
        for item in text:
            if self._estimate_tokens(str(item))+self._estimate_tokens(str(tmp)) > self.max_tokens:
                break
            tmp.append(item)
        return tmp.copy()

    async def ask(self, question: str, **kwargs) -> Dict[str, Any]:
        # 标记是否使用了缓存结果
        used_cache = False
        
        try:
            # 使用generate_sql获取SQL (可能来自缓存)
            sql, used_cache = await self.generate_sql(question=question, **kwargs)
            
            sql_result = {
                'sql': sql,
                'data': None
            }
            
            # 执行SQL
            result = await self.db_connector.run_sql(sql)
            result = serialize_result(result)
            
            if self._estimate_tokens(str(result)) > self.max_tokens:
                
                sql_result['data'] = self.split_data(result)
                return sql_result
            
            # 检查SQL执行结果
            if isinstance(result, dict) and result.get('error'):
                # SQL执行错误，如果是缓存结果则清除
                if used_cache:
                    # 调用缓存清理方法
                    await self._clear_cache_for_question(question)
                    logger.warning(f"清除问题的错误SQL缓存: {question}")
                
                sql_result['data'] = result
            else:
                # 在这里应用序列化函数
                sql_result['data'] = result
            return sql_result
        except Exception as e:
            logger.error(f"问答处理失败: {str(e)}", exc_info=True)
            return {
                'error': str(e),
                'sql': None,
                'data': None,
            }

    async def train(
        self,
        training_data: Union[Dict[str, Any], List[Dict[str, Any]]] = None,
        mode: str = "incremental",  # 差异化训练模式
        source: str = "user",      # 标记训练数据来源
        feedback_data: Dict[str, Any] = None,  # 用户反馈数据
        **kwargs
    ) -> Dict[str, Any]:
        """增强的异步训练接口
        Args:
            training_data: 单条或多条训练数据 
        Returns:
            训练结果信息
        """
        results = {'success': [], 'failed': [], 'status': 'completed'}
    
        # 确保training_data是列表
        if not isinstance(training_data, list):
            training_data = [training_data]
        
        for item in training_data:
            try:
                if 'documentation' in item:
                    doc_id = await self.vector_store.add_documentation(
                        item['documentation'], 
                        metadata={'source': source, 'timestamp': time.time()}
                    )
                    results['success'].append({'type': 'documentation', 'id': doc_id})
                    
                elif 'ddl' in item:
                    ddl_id = await self.vector_store.add_ddl(
                        item['ddl'],
                        metadata={'source': source, 'timestamp': time.time()}
                    )
                    results['success'].append({'type': 'ddl', 'id': ddl_id})
                    
                elif 'question' in item and 'sql' in item:
                    # 保存问题-SQL对和向量嵌入
                    pair_id = await self.vector_store.add_question_sql(
                        question=item['question'],
                        sql=item['sql'],
                        metadata={
                            'source': source, 
                            'timestamp': time.time(),
                            'tags': item.get('tags', [])
                        }
                    )
                    results['success'].append({'type': 'question_sql', 'id': pair_id})
                    
                else:
                    results['failed'].append({
                        'item': item,
                        'reason': '未识别的训练数据类型'
                    })
            except Exception as e:
                logger.error(f"训练项目失败: {str(e)}", exc_info=True)
                results['failed'].append({
                    'item': item,
                    'reason': str(e)
                })
        
        return results

    async def _clear_cache_for_question(self, question: str):
        """清除指定问题的缓存"""
        for middleware in self.middlewares:
            if hasattr(middleware, 'clear_cache'):
                await middleware.clear_cache(question)

def serialize_result(obj):
    """
    递归处理结果对象，将不可序列化的类型转换为可序列化类型
    """
    if isinstance(obj, dict):
        return {k: serialize_result(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_result(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(serialize_result(item) for item in obj)
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif pd.isna(obj):  # 处理NaN和None
        return None
    elif hasattr(obj, 'to_dict'):  # 处理Pandas DataFrame或Series
        return serialize_result(obj.to_dict(orient='records'))
    else:
        return obj
