import asyncio
from typing import List, Dict, Any, Optional, Union

import pandas as pd
from common.logging import get_logger
from .interfaces import AsyncLLMProvider, AsyncVectorStore, AsyncDBConnector, AsyncEmbeddingProvider
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
                 config: Dict[str, Any] = None):
        
        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.db_connector = db_connector
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
            
            # 返回生成的SQL
            return sql,ddl_list
        except Exception as e:
            # 异步处理异常
            logger.error(f"SQL生成失败: {str(e)}", exc_info=True)
            for plugin in getattr(self, 'plugins', []):
                await plugin.on_error(e, question=question, **kwargs)
            raise
    
    async def _get_sql_prompt(self, question, question_sql_list, ddl_list, doc_list, **kwargs):
        """构建SQL生成的提示信息"""
        
        # 1. 准备模板变量
        dialect = self.dialect
        database_context = self._build_database_context(ddl_list)
        descriptions = self._build_descriptions(doc_list)
        
        # 2. 获取或构建系统提示模板
        system_prompt_template = self._get_system_prompt_template()
        
        # 3. 填充系统提示
        system_prompt = system_prompt_template.format(
            dialect=dialect,
            database_context=database_context,
            descriptions=descriptions
        )
        
        # 4. 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        
        # 5. 添加示例问答对
        for example in question_sql_list:
            if isinstance(example, dict) and "question" in example and "sql" in example:
                messages.append({"role": "user", "content": example["question"]})
                messages.append({"role": "assistant", "content": example["sql"]})
        
        # 6. 添加当前问题
        messages.append({"role": "user", "content": question})
        
        return messages
    
    def _get_system_prompt_template(self):
        """获取系统提示模板"""
        # 优先使用配置中的自定义提示
        custom_prompt = self.config.get("initial_prompt", None)
        if custom_prompt:
            return custom_prompt
        
        # 基于Anthropic最佳实践的系统提示模板
        template = """<role>
你是一个专业的 {dialect} 数据库查询专家，擅长将自然语言问题准确转换为 SQL 查询。
</role>

<task>
根据用户的自然语言问题，结合提供的数据库上下文和业务描述，生成一个精确、高效的 SQL 查询。
</task>

<context>
{database_context}

{descriptions}

<sql_dialect>{dialect}</sql_dialect>
</context>

<constraints>
1. 严格使用提供的数据库上下文中的表名和列名，不要创造不存在的元素
2. 只能生成查询语句，不能生成插入、更新、删除语句
2. 确保 SQL 语法符合指定的 {dialect} 方言规范
3. 优先选择查询所需的最少列，避免不必要的 SELECT *
4. 生成的查询必须是单一的、完整的、可执行的 SQL 语句
5. 充分利用提供的示例和历史对话信息
6. 确保查询逻辑准确反映用户的真实意图
7. 如果用户查询具体的航班号，生成的 sql 中除了把航班号作为条件外，还需要把航班号作为查询字段。
8. 如果用户当前提供的信息不足以生成SQL，一定不要强行生成SQL（特别不能生成查询所有航班明细的 sql）。而是返回空字符串。
</constraints>

<output_format>
直接输出生成的 SQL 查询语句，不包含任何解释、注释或其他文本。

示例输出格式：
SELECT column1, column2 FROM table_name WHERE condition;
</output_format>

<reasoning_steps>
在生成 SQL 之前，请按以下步骤思考：

1. **问题分析**: 理解用户问题的核心意图和所需信息
2. **表结构映射**: 确定需要查询的表和相关字段
3. **关系识别**: 识别表之间的关联关系（如需要JOIN）
4. **条件提取**: 从问题中提取筛选条件和约束
5. **聚合需求**: 判断是否需要聚合函数（COUNT、SUM等）
6. **查询构建**: 按照SQL语法规范构建查询语句
7. **优化检查**: 确保查询效率和准确性
</reasoning_steps>

现在，请根据用户的问题生成相应的 SQL 查询："""
        
        return template
    
    def _build_database_context(self, ddl_list):
        """构建数据库上下文信息"""
        if not ddl_list:
            return "<database_schema>\n暂无数据库架构信息\n</database_schema>"
        
        ddl_content = ""
        for ddl in ddl_list:
            if isinstance(ddl, dict) and "ddl" in ddl and "description" in ddl:
                # 新格式：包含description和ddl
                ddl_content += f"""<table_info>
                                <description>{ddl['description']}</description>
                                <ddl>{ddl['ddl']}</ddl>
                                </table_info>

                                """
            else:
                # 兼容旧格式
                ddl_content += f"""<table_info>
                                        <ddl>{ddl}</ddl>
                                    </table_info>

                                    """
        
        # 检查token限制
        if self._estimate_tokens(ddl_content) > self.max_tokens * 0.4:  # 最多占用40%的token
            logger.warning("DDL内容过长，将被截断")
            ddl_content = ddl_content[:int(self.max_tokens * 0.4 * 2)]  # 简单截断
            ddl_content += "\n<!-- 内容因长度限制被截断 -->"
        
        return f"""<database_schema>{ddl_content.strip()}</database_schema>"""
    
    def _build_descriptions(self, doc_list):
        """构建描述信息"""
        if not doc_list:
            return "<business_context>\n暂无业务上下文信息\n</business_context>"
        
        doc_content = ""
        for i, doc in enumerate(doc_list, 1):
            doc_content += f"""<context_item id="{i}">{doc}</context_item>"""
        
        # 检查token限制
        if self._estimate_tokens(doc_content) > self.max_tokens * 0.3:  # 最多占用30%的token
            logger.warning("文档内容过长，将被截断")
            doc_content = doc_content[:int(self.max_tokens * 0.3 * 2)]  # 简单截断
            doc_content += "\n<!-- 内容因长度限制被截断 -->"
        
        return f"""<business_context>{doc_content.strip()}</business_context>"""
    
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
        try:
            # 使用generate_sql获取SQL
            sql,ddl_list = await self.generate_sql(question=question, **kwargs)
            
            sql_result = {
                'sql': sql,
                'ddl': ddl_list,
                'data': None,
                'error': None
            }
            
            # 执行SQL
            result = await self.db_connector.run_sql(sql)
            result = serialize_result(result)
            
            if self._estimate_tokens(str(result)) > self.max_tokens:
                
                sql_result['data'] = self.split_data(result)
                return sql_result
            
            # 检查SQL执行结果
            if isinstance(result, dict) and result.get('error'):
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
                'ddl': None,
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
                    # 检查是否有描述字段，如果没有则使用DDL本身作为描述
                    description = item.get('description', item['ddl'])
                    ddl_id = await self.vector_store.add_ddl(
                        item['ddl'],
                        description=description
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


    def get_prompt_config_example(self):
        """获取 prompt 配置示例，帮助用户理解如何自定义 prompt"""
        example_config = {
            "initial_prompt": """<role>
你是一个专业的 {dialect} 数据库分析师，专门为业务用户提供数据查询服务。
</role>

<task>
根据业务问题生成准确的 SQL 查询，重点关注业务价值和数据洞察。
</task>

<context>
{database_context}
{descriptions}
<sql_dialect>{dialect}</sql_dialect>
</context>

<guidelines>
1. 优先理解业务需求背后的真实意图
2. 生成高效、可读性强的 SQL 查询
3. 确保数据准确性和查询性能
4. 尽量查出航班号字段信息。
4. 遵循企业数据安全和隐私规范
</guidelines>

<output_format>
输出格式：纯 SQL 查询语句
</output_format>

请根据用户问题生成相应的 SQL 查询：""",
            
            "dialect": "PostgreSQL",
            "language": "zh-CN",
            "llm": {
                "max_tokens": 20000,
                "temperature": 0.1,
                "model": "claude-3-sonnet"
            }
        }
        
        return example_config
    
    def validate_prompt_template(self, template: str) -> dict:
        """验证 prompt 模板的有效性"""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "required_placeholders": ["{dialect}", "{database_context}", "{descriptions}"]
        }
        
        # 检查必需的占位符
        for placeholder in validation_result["required_placeholders"]:
            if placeholder not in template:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"缺少必需的占位符: {placeholder}")
        
        # 检查模板结构
        recommended_sections = ["<role>", "<task>", "<context>", "<output_format>"]
        missing_sections = [section for section in recommended_sections if section not in template]
        if missing_sections:
            validation_result["warnings"].append(f"建议添加以下结构化标签: {', '.join(missing_sections)}")
        
        # 检查模板长度
        if len(template) > 10000:
            validation_result["warnings"].append("模板过长，可能影响性能")
        elif len(template) < 100:
            validation_result["warnings"].append("模板过短，可能缺少必要信息")
        
        return validation_result

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
