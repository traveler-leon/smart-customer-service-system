"""
业务API连接器，用于业务办理模块
"""

from typing import Dict, Any, List, Optional


class MockBusinessAPI:
    """模拟业务API
    
    生产环境中应替换为实际的API连接器
    """
    
    def __init__(self):
        """初始化模拟业务API"""
        # 模拟已办理的业务
        self.processed_services = []
        
        # 模拟值机航班信息
        self.check_in_flights = [
            {
                "flight_number": "CA1384",
                "date": "2025-04-08",
                "passenger_name": "张三",
                "available_seats": ["12A", "12B", "14C", "15F", "20D"]
            },
            {
                "flight_number": "MU5735",
                "date": "2025-04-09",
                "passenger_name": "李四",
                "available_seats": ["2A", "5B", "8C", "10F", "25D"]
            }
        ]
    
    def call_service(self, service_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用业务API
        
        Args:
            service_type: 业务类型，如"值机"、"改签"、"退票"等
            params: 业务参数
            
        Returns:
            API响应结果
        """
        # 根据不同业务类型调用不同API
        if service_type == "值机":
            return self._check_in_service(params)
        elif service_type == "改签":
            return self._change_flight_service(params)
        elif service_type == "退票":
            return self._refund_ticket_service(params)
        elif service_type == "行李托运":
            return self._baggage_service(params)
        elif service_type == "遗失物品查询":
            return self._lost_found_service(params)
        else:
            return {
                "success": False,
                "error": "不支持的业务类型",
                "error_code": "UNSUPPORTED_SERVICE"
            }
    
    def _check_in_service(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """值机服务"""
        flight_number = params.get("flight_number")
        passenger_name = params.get("passenger_name")
        seat_preference = params.get("seat_preference", "")
        
        # 验证必要参数
        if not flight_number or not passenger_name:
            return {
                "success": False,
                "error": "缺少必要信息",
                "error_code": "MISSING_PARAMS",
                "missing_fields": [k for k, v in {
                    "flight_number": flight_number,
                    "passenger_name": passenger_name
                }.items() if not v]
            }
        
        # 查找匹配的航班
        flight = None
        for f in self.check_in_flights:
            if f["flight_number"] == flight_number and f["passenger_name"] == passenger_name:
                flight = f
                break
        
        if not flight:
            return {
                "success": False,
                "error": "未找到匹配的航班信息",
                "error_code": "FLIGHT_NOT_FOUND"
            }
        
        # 分配座位
        seat = self._assign_seat(flight, seat_preference)
        
        # 记录值机信息
        check_in_record = {
            "flight_number": flight_number,
            "passenger_name": passenger_name,
            "seat": seat,
            "gate": "C12" if flight_number.startswith("CA") else "D05",
            "boarding_time": "13:30" if flight_number.startswith("CA") else "07:15"
        }
        
        self.processed_services.append({
            "type": "值机",
            "params": params,
            "result": check_in_record
        })
        
        return {
            "success": True,
            "data": check_in_record
        }
    
    def _change_flight_service(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """改签服务"""
        # 模拟改签逻辑
        flight_number = params.get("flight_number")
        new_date = params.get("new_date")
        passenger_name = params.get("passenger_name")
        
        # 验证必要参数
        if not flight_number or not new_date or not passenger_name:
            return {
                "success": False,
                "error": "缺少必要信息",
                "error_code": "MISSING_PARAMS",
                "missing_fields": [k for k, v in {
                    "flight_number": flight_number,
                    "new_date": new_date,
                    "passenger_name": passenger_name
                }.items() if not v]
            }
        
        # 模拟改签成功
        change_record = {
            "flight_number": flight_number,
            "passenger_name": passenger_name,
            "original_date": "2025-04-08",
            "new_date": new_date,
            "change_fee": 200
        }
        
        self.processed_services.append({
            "type": "改签",
            "params": params,
            "result": change_record
        })
        
        return {
            "success": True,
            "data": change_record
        }
    
    def _refund_ticket_service(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """退票服务"""
        # 模拟退票逻辑
        flight_number = params.get("flight_number")
        passenger_name = params.get("passenger_name")
        refund_reason = params.get("refund_reason", "自愿退票")
        
        # 验证必要参数
        if not flight_number or not passenger_name:
            return {
                "success": False,
                "error": "缺少必要信息",
                "error_code": "MISSING_PARAMS",
                "missing_fields": [k for k, v in {
                    "flight_number": flight_number,
                    "passenger_name": passenger_name
                }.items() if not v]
            }
        
        # 模拟退票手续费计算
        is_voluntary = "自愿" in refund_reason
        refund_fee = 300 if is_voluntary else 100
        
        refund_record = {
            "flight_number": flight_number,
            "passenger_name": passenger_name,
            "refund_reason": refund_reason,
            "ticket_price": 1000,
            "refund_fee": refund_fee,
            "actual_refund": 1000 - refund_fee
        }
        
        self.processed_services.append({
            "type": "退票",
            "params": params,
            "result": refund_record
        })
        
        return {
            "success": True,
            "data": refund_record
        }
    
    def _baggage_service(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """行李托运服务"""
        flight_number = params.get("flight_number")
        passenger_name = params.get("passenger_name")
        baggage_weight = params.get("baggage_weight")
        
        # 验证必要参数
        if not flight_number or not passenger_name or not baggage_weight:
            return {
                "success": False,
                "error": "缺少必要信息",
                "error_code": "MISSING_PARAMS",
                "missing_fields": [k for k, v in {
                    "flight_number": flight_number,
                    "passenger_name": passenger_name,
                    "baggage_weight": baggage_weight
                }.items() if not v]
            }
        
        # 计算行李费用
        baggage_weight = float(baggage_weight)
        free_allowance = 23  # 免费行李额
        excess_weight = max(0, baggage_weight - free_allowance)
        excess_fee = excess_weight * 50  # 每公斤超重费50元
        
        baggage_record = {
            "flight_number": flight_number,
            "passenger_name": passenger_name,
            "baggage_weight": baggage_weight,
            "free_allowance": free_allowance,
            "excess_weight": excess_weight,
            "excess_fee": excess_fee,
            "baggage_tag": "BT" + flight_number + "123456"
        }
        
        self.processed_services.append({
            "type": "行李托运",
            "params": params,
            "result": baggage_record
        })
        
        return {
            "success": True,
            "data": baggage_record
        }
    
    def _lost_found_service(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """遗失物品查询服务"""
        item_description = params.get("item_description")
        loss_location = params.get("loss_location")
        loss_time = params.get("loss_time")
        
        # 验证必要参数
        if not item_description:
            return {
                "success": False,
                "error": "缺少必要信息",
                "error_code": "MISSING_PARAMS",
                "missing_fields": ["item_description"]
            }
        
        # 模拟查询结果
        found_items = []
        if "手机" in item_description or "电话" in item_description:
            found_items.append({
                "item_type": "手机",
                "brand": "iPhone",
                "color": "黑色",
                "found_time": "2025-04-07 18:30",
                "found_location": "T3航站楼安检区",
                "claim_location": "T3航站楼失物招领处"
            })
        
        if "钱包" in item_description or "包" in item_description:
            found_items.append({
                "item_type": "钱包",
                "brand": "未知",
                "color": "棕色",
                "found_time": "2025-04-08 09:15",
                "found_location": "T2航站楼登机口附近",
                "claim_location": "T2航站楼失物招领处"
            })
        
        self.processed_services.append({
            "type": "遗失物品查询",
            "params": params,
            "result": {"found_items": found_items}
        })
        
        return {
            "success": True,
            "data": {
                "found_items": found_items,
                "query_info": {
                    "item_description": item_description,
                    "loss_location": loss_location,
                    "loss_time": loss_time
                },
                "lost_found_hotline": "010-12345678"
            }
        }
    
    def _assign_seat(self, flight: Dict[str, Any], preference: str) -> str:
        """为乘客分配座位"""
        available_seats = flight.get("available_seats", [])
        
        if not available_seats:
            return "自动分配"
        
        # 根据偏好分配座位
        if preference:
            preference = preference.lower()
            for seat in available_seats:
                # 窗口座位通常是A或F
                if "窗" in preference and (seat.endswith("A") or seat.endswith("F")):
                    return seat
                # 过道座位通常是C或D
                elif "过道" in preference and (seat.endswith("C") or seat.endswith("D")):
                    return seat
                # 前排座位
                elif "前" in preference and int(seat[:-1]) < 10:
                    return seat
                # 靠近出口的座位
                elif "出口" in preference and (seat.startswith("12") or seat.startswith("13")):
                    return seat
        
        # 如果没有合适的偏好座位或没有指定偏好，返回第一个可用座位
        return available_seats[0]


# 创建默认业务API实例
default_business_api = MockBusinessAPI() 