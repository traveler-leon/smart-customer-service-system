"""
Text2SQL 训练 API

提供 Text2SQL 模块的训练和数据管理接口
"""

import asyncio
import json
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Response
from fastapi.responses import JSONResponse

from models.schemas import (
    TrainingRequest, TrainingResponse, 
    ClearDataRequest, ClearDataResponse,
    TrainingDataItem
)
from text2sql import create_text2sql
from config.utils import config_manager
from common.logging import get_logger

# 获取Text2SQL训练API专用日志记录器
logger = get_logger("api.text2sql_training")

router = APIRouter(prefix="/text2sql/v1", tags=["Text2SQL训练"])

# 全局text2sql实例缓存
_text2sql_instance = None

async def get_text2sql_instance():
    """获取或创建text2sql实例"""
    global _text2sql_instance
    
    if _text2sql_instance is None:
        try:
            logger.info("开始初始化text2sql实例")
            # 获取text2sql配置
            text2sql_config = config_manager.get_text2sql_config()
            
            # 检查配置是否完整
            db_config = text2sql_config.get("db", {})
            if not db_config.get("type"):
                logger.warning("数据库类型未设置，设置为postgresql")
                if "db" not in text2sql_config:
                    text2sql_config["db"] = {}
                text2sql_config["db"]["type"] = "postgresql"
            
            # 从环境变量补充缺失的数据库参数
            required_db_params = ["host", "port", "user", "password", "database"]
            for param in required_db_params:
                if param not in db_config:
                    env_var = f"DB_{param.upper()}"
                    if os.environ.get(env_var):
                        text2sql_config["db"][param] = os.environ.get(env_var)
                        if param == "port":
                            text2sql_config["db"][param] = int(text2sql_config["db"][param])
            
            _text2sql_instance = await create_text2sql(text2sql_config)
            logger.info("text2sql实例初始化成功")
        except Exception as e:
            logger.error(f"初始化text2sql实例时出错: {str(e)}")
            raise HTTPException(status_code=500, detail=f"初始化text2sql实例失败: {str(e)}")
    
    return _text2sql_instance

@router.post("/train", response_model=TrainingResponse)
async def train_text2sql(training_request: TrainingRequest, request: Request, response: Response):
    """
    训练Text2SQL模型
    
    Args:
        training_request: 训练请求，包含训练数据和配置
        
    Returns:
        训练结果
    """
    logger.info(f"收到训练请求 - 数据条数: {len(training_request.training_data)}, 清除现有数据: {training_request.clear_existing}")
    
    try:
        # 获取text2sql实例
        smart_sql = await get_text2sql_instance()
        
        # 清除现有数据（如果需要）
        if training_request.clear_existing:
            logger.warning("正在清除现有训练数据...")
            if hasattr(smart_sql.vector_store, 'remove_collection'):
                collections = ["sql-sql", "sql-documentation", "sql-ddl"]
                for collection in collections:
                    try:
                        await smart_sql.vector_store.remove_collection(collection)
                        logger.info(f"已清除集合: {collection}")
                    except Exception as e:
                        logger.warning(f"清除集合{collection}时出错: {str(e)}")
        
        # 准备训练数据
        training_data = []
        for item in training_request.training_data:
            data_dict = {}
            
            # 添加DDL数据
            if item.ddl:
                data_dict['ddl'] = item.ddl
                if item.description:
                    data_dict['description'] = item.description
            
            # 添加文档数据
            if item.documentation:
                data_dict['documentation'] = item.documentation
            
            # 添加问答数据
            if item.question and item.sql:
                data_dict['question'] = item.question
                data_dict['sql'] = item.sql
                if item.tags:
                    data_dict['tags'] = item.tags
            
            if data_dict:
                training_data.append(data_dict)
        
        if not training_data:
            logger.warning("没有有效的训练数据")
            return TrainingResponse(
                success=False,
                message="没有有效的训练数据",
                total_count=0
            )
        
        # 执行训练
        logger.info(f"开始训练，共有{len(training_data)}条数据...")
        result = await smart_sql.train(training_data)
        
        # 统计训练结果
        success_count = len(result.get('success', []))
        failed_count = len(result.get('failed', []))
        
        logger.info(f"训练完成: {success_count}条成功, {failed_count}条失败")
        
        return TrainingResponse(
            success=True,
            message=f"训练完成: {success_count}条成功, {failed_count}条失败",
            success_count=success_count,
            failed_count=failed_count,
            total_count=len(training_data)
        )
        
    except Exception as e:
        logger.error(f"训练过程中出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"训练失败: {str(e)}")

@router.post("/clear", response_model=ClearDataResponse)
async def clear_training_data(clear_request: ClearDataRequest, request: Request, response: Response):
    """
    清除训练数据
    
    Args:
        clear_request: 清除请求，指定要清除的集合
        
    Returns:
        清除结果
    """
    logger.info(f"收到清除数据请求 - 集合: {clear_request.collections}")
    
    try:
        # 获取text2sql实例
        smart_sql = await get_text2sql_instance()
        
        # 确定要清除的集合
        collections_to_clear = clear_request.collections or ["sql-sql", "sql-documentation", "sql-ddl"]
        cleared_collections = []
        
        if hasattr(smart_sql.vector_store, 'remove_collection'):
            for collection in collections_to_clear:
                try:
                    await smart_sql.vector_store.remove_collection(collection)
                    cleared_collections.append(collection)
                    logger.info(f"已清除集合: {collection}")
                except Exception as e:
                    logger.warning(f"清除集合{collection}时出错: {str(e)}")
        else:
            logger.warning("向量存储不支持清除集合操作")
            return ClearDataResponse(
                success=False,
                message="向量存储不支持清除集合操作"
            )
        
        return ClearDataResponse(
            success=True,
            message=f"成功清除{len(cleared_collections)}个集合",
            cleared_collections=cleared_collections
        )

    except Exception as e:
        logger.error(f"清除数据时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清除数据失败: {str(e)}")

async def load_excel_training_data(file_path: str, smart_sql):
    """
    从Excel文件加载训练数据

    Excel文件应包含三个sheet:
    - ddl: 包含DDL语句，必须有一列名为'ddl'，可选择性包含'description'列
    - documentation: 包含文档信息，至少有一列名为'documentation'
    - qa: 包含问题和SQL，至少有两列，分别名为'question'和'sql'，可选择性包含'tags'列

    Args:
        file_path: Excel文件路径
        smart_sql: text2sql实例

    Returns:
        训练结果
    """
    try:
        import pandas as pd
    except ImportError:
        logger.error("无法加载Excel文件: 未安装pandas库")
        raise HTTPException(status_code=400, detail="服务器未安装pandas库，无法处理Excel文件")

    try:
        # 准备训练数据列表
        training_data = []

        # 读取DDL sheet
        try:
            ddl_df = pd.read_excel(file_path, sheet_name='ddl')
            if 'ddl' in ddl_df.columns:
                logger.info(f"从Excel文件加载DDL数据...")
                for _, row in ddl_df.iterrows():
                    ddl = row.get('ddl')
                    if ddl and len(str(ddl).strip()) > 0:
                        ddl_item = {'ddl': str(ddl)}
                        # 检查是否有description列
                        if 'description' in ddl_df.columns:
                            description = row.get('description')
                            if description and len(str(description).strip()) > 0:
                                ddl_item['description'] = str(description)
                        training_data.append(ddl_item)
                logger.info(f"已解析{len(ddl_df['ddl'].dropna())}条DDL语句")
        except ValueError:
            logger.warning("Excel文件中没有'ddl'表格或表格格式不正确")

        # 读取documents sheet
        try:
            docs_df = pd.read_excel(file_path, sheet_name='documentation')
            if 'documentation' in docs_df.columns:
                logger.info(f"从Excel文件加载文档数据...")
                for doc in docs_df['documentation'].dropna():
                    if doc and len(str(doc).strip()) > 0:
                        training_data.append({'documentation': str(doc)})
                logger.info(f"已解析{len(docs_df['documentation'].dropna())}条文档信息")
        except ValueError:
            logger.warning("Excel文件中没有'documentation'表格或表格格式不正确")

        # 读取qa sheet
        try:
            qa_df = pd.read_excel(file_path, sheet_name='qa')
            if 'question' in qa_df.columns and 'sql' in qa_df.columns:
                logger.info(f"从Excel文件加载问题和SQL数据...")
                # 删除任一列为空的行
                qa_df = qa_df.dropna(subset=['question', 'sql'])
                for _, row in qa_df.iterrows():
                    question = str(row['question']).strip()
                    sql = str(row['sql']).strip()
                    if question and sql:
                        # 检查是否有tags列
                        tags = row.get('tags', '') if 'tags' in qa_df.columns else ''
                        qa_item = {
                            'question': question,
                            'sql': sql
                        }
                        if tags and str(tags).strip():
                            qa_item['tags'] = str(tags).strip()
                        training_data.append(qa_item)
                logger.info(f"已解析{len(qa_df)}个示例问题和SQL")
        except ValueError:
            logger.warning("Excel文件中没有'qa'表格或表格格式不正确")

        # 使用train方法进行训练
        if training_data:
            logger.info(f"开始训练，共有{len(training_data)}条数据...")
            result = await smart_sql.train(training_data)

            # 统计训练结果
            success_count = len(result.get('success', []))
            failed_count = len(result.get('failed', []))

            logger.info(f"训练完成: {success_count}条成功, {failed_count}条失败")
            return {
                'success': True,
                'message': f"训练完成: {success_count}条成功, {failed_count}条失败",
                'success_count': success_count,
                'failed_count': failed_count,
                'total_count': len(training_data)
            }
        else:
            logger.warning("没有解析到有效的训练数据")
            return {
                'success': False,
                'message': "没有解析到有效的训练数据",
                'total_count': 0
            }

    except FileNotFoundError:
        logger.error(f"找不到文件: {file_path}")
        raise HTTPException(status_code=404, detail=f"找不到文件: {file_path}")
    except Exception as e:
        logger.error(f"加载Excel训练数据时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"加载Excel训练数据失败: {str(e)}")

@router.post("/train/excel", response_model=TrainingResponse)
async def train_from_excel(
    file: UploadFile = File(..., description="Excel训练数据文件"),
    clear_existing: bool = False,
    request: Request = None,
    response: Response = None
):
    """
    从Excel文件训练Text2SQL模型

    Excel文件应包含三个sheet:
    - ddl: DDL语句和描述
    - documentation: 文档信息
    - qa: 问题和SQL对

    Args:
        file: Excel文件
        clear_existing: 是否清除现有数据

    Returns:
        训练结果
    """
    logger.info(f"收到Excel文件训练请求 - 文件名: {file.filename}, 清除现有数据: {clear_existing}")

    # 检查文件类型
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="只支持Excel文件格式 (.xlsx, .xls)")

    try:
        # 获取text2sql实例
        smart_sql = await get_text2sql_instance()

        # 清除现有数据（如果需要）
        if clear_existing:
            logger.warning("正在清除现有训练数据...")
            if hasattr(smart_sql.vector_store, 'remove_collection'):
                collections = ["sql-sql", "sql-documentation", "sql-ddl"]
                for collection in collections:
                    try:
                        await smart_sql.vector_store.remove_collection(collection)
                        logger.info(f"已清除集合: {collection}")
                    except Exception as e:
                        logger.warning(f"清除集合{collection}时出错: {str(e)}")

        # 保存上传的文件到临时目录
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # 从Excel文件加载并训练数据
            result = await load_excel_training_data(temp_file_path, smart_sql)

            return TrainingResponse(
                success=result['success'],
                message=result['message'],
                success_count=result.get('success_count', 0),
                failed_count=result.get('failed_count', 0),
                total_count=result.get('total_count', 0)
            )

        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {str(e)}")

    except Exception as e:
        logger.error(f"Excel文件训练过程中出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Excel文件训练失败: {str(e)}")

@router.get("/status")
async def get_training_status():
    """
    获取Text2SQL训练状态

    Returns:
        训练状态信息
    """
    logger.info("收到训练状态查询请求")

    try:
        # 获取text2sql实例
        smart_sql = await get_text2sql_instance()

        # 获取向量存储状态信息
        status_info = {
            "text2sql_initialized": smart_sql is not None,
            "vector_store_type": type(smart_sql.vector_store).__name__ if smart_sql else None,
            "collections": []
        }

        # 尝试获取集合信息
        if hasattr(smart_sql.vector_store, 'list_collections'):
            try:
                collections = await smart_sql.vector_store.list_collections()
                status_info["collections"] = collections
            except Exception as e:
                logger.warning(f"获取集合列表失败: {str(e)}")
                status_info["collections"] = ["无法获取集合信息"]

        logger.info(f"返回训练状态: {status_info}")
        return JSONResponse(content=status_info)

    except Exception as e:
        logger.error(f"获取训练状态时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取训练状态失败: {str(e)}")

@router.get("/health")
async def health_check():
    """
    健康检查接口

    Returns:
        服务健康状态
    """
    try:
        # 检查text2sql实例是否可用
        smart_sql = await get_text2sql_instance()

        return JSONResponse(content={
            "status": "healthy",
            "message": "Text2SQL训练服务运行正常",
            "text2sql_available": smart_sql is not None
        })

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": f"Text2SQL训练服务异常: {str(e)}",
                "text2sql_available": False
            }
        )
