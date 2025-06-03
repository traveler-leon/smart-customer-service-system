#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Text2SQL训练工具

该脚本用于训练text2sql模块，添加航班相关的SQL表结构、示例问题和文档
"""

import asyncio
import argparse
import logging
import sys
import os
import json
from pathlib import Path

# 确保能正确导入项目模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from text2sql import create_text2sql
from config.utils import config_manager
from typing import Dict, List, Any

try:
    import pandas as pd
    PANDAS_INSTALLED = True
except ImportError:
    PANDAS_INSTALLED = False

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("train_text2sql")

async def load_excel_training_data(file_path: str, smart_sql):
    """
    从Excel文件加载训练数据
    
    Excel文件应包含三个sheet:
    - ddl: 包含DDL语句，至少有一列名为'ddl'
    - documents: 包含文档信息，至少有一列名为'document'
    - qa: 包含问题和SQL，至少有两列，分别名为'question'和'sql'
    
    Args:
        file_path: Excel文件路径
        smart_sql: text2sql实例
    
    Returns:
        加载的训练数据项数
    """
    if not PANDAS_INSTALLED:
        logger.error("无法加载Excel文件: 未安装pandas库。请安装pandas: pip install pandas openpyxl")
        return 0
    
    try:
        # 准备训练数据列表
        training_data = []
        
        # 读取DDL sheet
        try:
            ddl_df = pd.read_excel(file_path, sheet_name='ddl')
            if 'ddl' in ddl_df.columns:
                logger.info(f"从Excel文件加载DDL数据...")
                for ddl in ddl_df['ddl'].dropna():
                    if ddl and len(str(ddl).strip()) > 0:
                        training_data.append({'ddl': str(ddl)})
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
            return success_count
        else:
            logger.warning("没有解析到有效的训练数据")
            return 0
        
    except FileNotFoundError:
        logger.error(f"找不到文件: {file_path}")
        return 0
    except Exception as e:
        logger.error(f"加载Excel训练数据时出错: {str(e)}")
        return 0

async def train_text2sql(args):
    """
    训练text2sql模块
    
    Args:
        args: 命令行参数
    """
    try:
        logger.info("正在初始化text2sql实例...")
        # 获取text2sql配置
        text2sql_config = config_manager.get_text2sql_config()
        logger.info(f"加载的Text2SQL配置: {json.dumps(text2sql_config, ensure_ascii=False, indent=2)}")
        
        # 检查配置是否完整
        db_config = text2sql_config.get("db", {})
        if not db_config.get("type"):
            logger.warning("数据库类型未设置，尝试设置为postgresql")
            if "db" not in text2sql_config:
                text2sql_config["db"] = {}
            text2sql_config["db"]["type"] = "postgresql"
            
        if not db_config.get("host") and os.environ.get("DB_HOST"):
            logger.warning("数据库主机未设置，尝试从环境变量设置")
            text2sql_config["db"]["host"] = os.environ.get("DB_HOST")
            
        # 确保必要的数据库参数存在
        required_db_params = ["host", "port", "user", "password", "database"]
        missing_params = [param for param in required_db_params if param not in db_config]
        if missing_params:
            logger.warning(f"缺少数据库参数: {missing_params}，尝试从环境变量加载")
            for param in missing_params:
                env_var = f"DB_{param.upper()}"
                if os.environ.get(env_var):
                    text2sql_config["db"][param] = os.environ.get(env_var)
                    if param == "port":
                        text2sql_config["db"][param] = int(text2sql_config["db"][param])
        
        logger.info(f"最终Text2SQL配置: {json.dumps(text2sql_config, ensure_ascii=False, indent=2)}")
        
        # 创建text2sql实例
        smart_sql = await create_text2sql(text2sql_config)
        
        total_items = 0
        
        # 清除现有数据
        if args.clear:
            logger.warning("正在清除现有训练数据...")
            # 这里假设有clear_collections方法
            if hasattr(smart_sql.vector_store, 'remove_collection'):
                collections = ["sql-sql", "sql-documentation", "sql-ddl"]
                for collection in collections:
                    try:
                        await smart_sql.vector_store.remove_collection(collection)
                        logger.info(f"已清除集合: {collection}")
                    except Exception as e:
                        logger.warning(f"清除集合{collection}时出错: {str(e)}")
            logger.info("现有训练数据已清除")
        
        # 自定义训练数据 - Excel格式
        if args.excel_file or (args.custom_file and args.custom_file.endswith(('.xlsx', '.xls'))):
            file_path = args.excel_file if args.excel_file else args.custom_file
            logger.info(f"正在从Excel文件{file_path}加载自定义训练数据...")
            if not PANDAS_INSTALLED:
                logger.error("未安装pandas库，无法加载Excel文件。请安装pandas: pip install pandas openpyxl")
            else:
                custom_items = await load_excel_training_data(file_path, smart_sql)
                total_items += custom_items
                logger.info(f"从Excel文件加载了{custom_items}条训练数据！")
        
        logger.info(f"训练完成！总共添加了{total_items}条训练数据。")
        # 关闭资源
        await smart_sql.shutdown()
        
    except Exception as e:
        logger.error(f"训练过程中出错: {str(e)}")
        raise

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='训练Text2SQL模块')
    parser.add_argument('--custom-file', type=str, help='自定义训练数据文件路径 (JSON或Excel)')
    parser.add_argument('--excel-file', type=str, help='Excel格式的训练数据文件 (包含ddl,documents,qa三个sheet)')
    parser.add_argument('--clear', action='store_true', help='清除现有训练数据（谨慎使用）')
    args = parser.parse_args()
    
    asyncio.run(train_text2sql(args))

if __name__ == "__main__":
    main() 