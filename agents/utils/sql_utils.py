"""
SQL工具函数，用于航班信息查询
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class MockFlightDatabase:
    """模拟航班数据库
    
    生产环境中应替换为实际的数据库连接器
    """
    
    def __init__(self):
        """初始化模拟航班数据库"""
        # 模拟航班数据
        self.flights = [
            {
                "flight_number": "CA1384",
                "airline": "中国国航",
                "departure_city": "北京",
                "arrival_city": "上海",
                "departure_time": "2025-04-08 14:30:00",
                "arrival_time": "2025-04-08 16:45:00",
                "terminal": "T3",
                "gate": "C12",
                "status": "准点",
                "delay_minutes": 0
            },
            {
                "flight_number": "MU5735",
                "airline": "东方航空",
                "departure_city": "北京",
                "arrival_city": "昆明",
                "departure_time": "2025-04-09 08:15:00",
                "arrival_time": "2025-04-09 11:30:00",
                "terminal": "T2",
                "gate": "D05",
                "status": "准点",
                "delay_minutes": 0
            },
            {
                "flight_number": "CZ3215",
                "airline": "南方航空",
                "departure_city": "广州",
                "arrival_city": "北京",
                "departure_time": "2025-04-08 16:20:00",
                "arrival_time": "2025-04-08 19:10:00",
                "terminal": "T2",
                "gate": "B08",
                "status": "延误",
                "delay_minutes": 45
            },
            {
                "flight_number": "HU7142",
                "airline": "海南航空",
                "departure_city": "北京",
                "arrival_city": "深圳",
                "departure_time": "2025-04-08 13:40:00",
                "arrival_time": "2025-04-08 16:50:00",
                "terminal": "T1",
                "gate": "A22",
                "status": "取消",
                "delay_minutes": 0
            },
            {
                "flight_number": "CA1234",
                "airline": "中国国航",
                "departure_city": "北京",
                "arrival_city": "成都",
                "departure_time": "2025-04-08 18:25:00",
                "arrival_time": "2025-04-08 21:15:00",
                "terminal": "T3",
                "gate": "C05",
                "status": "延误",
                "delay_minutes": 30
            }
        ]
    
    def execute_query(self, sql_query: str) -> List[Dict]:
        """执行SQL查询
        
        注意：这是一个简化的模拟实现，仅支持有限的SQL语法
        """
        # 创建临时内存数据库
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 创建flights表
        cursor.execute('''
        CREATE TABLE flights (
            flight_number TEXT,
            airline TEXT,
            departure_city TEXT,
            arrival_city TEXT,
            departure_time TEXT,
            arrival_time TEXT,
            terminal TEXT,
            gate TEXT,
            status TEXT,
            delay_minutes INTEGER
        )
        ''')
        
        # 插入数据
        for flight in self.flights:
            cursor.execute('''
            INSERT INTO flights VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                flight["flight_number"],
                flight["airline"],
                flight["departure_city"],
                flight["arrival_city"],
                flight["departure_time"],
                flight["arrival_time"],
                flight["terminal"],
                flight["gate"],
                flight["status"],
                flight["delay_minutes"]
            ))
        
        conn.commit()
        
        try:
            # 执行查询
            cursor.execute(sql_query)
            
            # 获取结果
            results = []
            for row in cursor.fetchall():
                results.append({key: row[key] for key in row.keys()})
            
            return results
        except Exception as e:
            # 错误处理
            return [{"error": str(e)}]
        finally:
            conn.close()
    
    def generate_sql(self, query_text: str) -> str:
        """根据自然语言查询生成SQL
        
        实际应用中使用Text2SQL模型或LLM生成SQL
        """
        # 这里直接使用预定义的SQL查询，实际应用中应该使用LLM转换
        if "CA1384" in query_text or "延误" in query_text and "国航" in query_text:
            return "SELECT * FROM flights WHERE flight_number = 'CA1384'"
        elif "MU5735" in query_text:
            return "SELECT * FROM flights WHERE flight_number = 'MU5735'"
        elif "延误" in query_text:
            return "SELECT * FROM flights WHERE status = '延误'"
        elif "取消" in query_text:
            return "SELECT * FROM flights WHERE status = '取消'"
        elif "北京" in query_text and "上海" in query_text:
            return "SELECT * FROM flights WHERE departure_city = '北京' AND arrival_city = '上海'"
        else:
            # 默认返回所有航班
            return "SELECT * FROM flights"


# 创建默认航班数据库实例
default_flight_db = MockFlightDatabase() 