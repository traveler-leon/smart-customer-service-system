import pandas as pd
import requests
import json
import time
import base64
import os
from pathlib import Path

# API配置
API_BASE_URL = "http://localhost:8081"  # 根据实际服务器地址调整
BATCH_SIZE = 50  # 每批次处理的数量

# 图片目录配置
EXCEL_PATH = "/Users/hzwl/Documents/coding/smart-customer-service-system/tools/data/常见问题汇总-图片改文字版（未标注颜色）.xlsx"
IMAGE_DIR = Path(EXCEL_PATH).parent / "常见问题图片"

def load_image_as_base64(image_name, image_dir):
    """
    加载图片文件并转换为base64格式
    
    Args:
        image_name: 图片文件名（不含扩展名）
        image_dir: 图片目录路径
        
    Returns:
        dict: 包含图片数据的字典，如果文件不存在则返回None
    """
    if not image_name or pd.isna(image_name) or str(image_name).strip() == "":
        return None
    
    # 构建图片文件路径
    image_path = image_dir / f"{str(image_name).strip()}.png"
    
    if not image_path.exists():
        print(f"  警告: 图片文件不存在: {image_path}")
        return None
    
    try:
        # 读取图片文件
        with open(image_path, 'rb') as f:
            image_binary = f.read()
        
        # 转换为base64
        base64_data = base64.b64encode(image_binary).decode('utf-8')
        
        return {
            "filename": f"{image_name}.png",
            "content_type": "image/png",
            "data": base64_data
        }
    except Exception as e:
        print(f"  错误: 读取图片文件失败 {image_path}: {str(e)}")
        return None

def call_batch_api(qa_pairs):
    """调用批量添加QA API"""
    url = f"{API_BASE_URL}/text2qa/qa/batch"
    
    # 构造请求数据
    payload = {
        "qa_pairs": qa_pairs
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10000)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API调用失败: {response.status_code}, {response.text}")
            return {"success": False, "message": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        print(f"API调用异常: {str(e)}")
        return {"success": False, "message": f"连接错误: {str(e)}"}

print("开始导入Excel数据到Redis...")
print(f"API地址: {API_BASE_URL}")
print(f"Excel文件: {EXCEL_PATH}")
print(f"图片目录: {IMAGE_DIR}")

# 检查文件和目录是否存在
if not Path(EXCEL_PATH).exists():
    print(f"错误: Excel文件不存在: {EXCEL_PATH}")
    exit(1)

if not IMAGE_DIR.exists():
    print(f"警告: 图片目录不存在: {IMAGE_DIR}")
    print("将跳过所有图片处理")
else:
    print(f"图片目录存在，包含 {len(list(IMAGE_DIR.glob('*.png')))} 个PNG文件")

# 测试API连接
try:
    ping_response = requests.get(f"{API_BASE_URL}/text2qa/ping", timeout=10)
    if ping_response.status_code == 200:
        print("API连接测试成功!")
    else:
        print(f"API连接测试失败: {ping_response.status_code}")
        exit(1)
except Exception as e:
    print(f"API连接测试异常: {str(e)}")
    exit(1)

total_success = 0
total_failed = 0
total_images_processed = 0
total_images_failed = 0
start_time = time.time()

sheet_names = ["安检问题","航空公司业务","派出所","机场交通","联检单位","FAQ知识库"]
# sheet_names = ["FAQ知识库"]
for sheet_name in sheet_names:
    print(f"\n开始处理工作表: {sheet_name}")
    
    df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name)
    print(f"原始数据条数: {len(df)}")
    
    df.dropna(inplace=True,how="all")
    print(f"清理后数据条数: {len(df)}")
    # 准备批量数据
    qa_pairs = []
    
    for idx, item in df.iterrows():
        try:
            question = str(item['问题']).strip() if pd.notna(item.get('问题', '')) else ""
            answer = str(item['答案']).strip() if pd.notna(item.get('答案', '')) else ""
            
            if question and answer and question != "nan" and answer != "nan":
                # 处理图片数据
                images = []
                image_name = item.get('图片', '')
                if image_name and pd.notna(image_name) and str(image_name).strip():
                    print(f"  处理图片: {image_name}")
                    image_data = load_image_as_base64(image_name, IMAGE_DIR)
                    if image_data:
                        images.append(image_data)
                        total_images_processed += 1
                        print(f"  图片加载成功: {image_name}.png")
                    else:
                        total_images_failed += 1
                        print(f"  图片加载失败: {image_name}")
                
                qa_pair = {
                    "question": question,
                    "answer": answer,
                    "tags": [sheet_name],
                    "images": images,
                    "services": [],
                    "extra_fields": {
                        "expert_id": "airport_qa_import",
                        "application_id": "主智能客服",
                        "sheet_name": sheet_name,
                        "row_index": int(idx),
                        "has_image": len(images) > 0
                    }
                }
                qa_pairs.append(qa_pair)
                
                # 达到批次大小或是最后一批时，调用API
                if len(qa_pairs) >= BATCH_SIZE:
                    print(f"  调用API批量添加 {len(qa_pairs)} 条数据...")
                    result = call_batch_api(qa_pairs)
                    
                    if result.get("success"):
                        batch_success = result.get("data", {}).get("success_count", 0)
                        batch_failed = result.get("data", {}).get("failed_count", 0)
                        total_success += batch_success
                        total_failed += batch_failed
                        print(f"  批次完成: 成功 {batch_success}, 失败 {batch_failed}")
                    else:
                        total_failed += len(qa_pairs)
                        print(f"  批次失败: {result.get('message', '未知错误')}")
                    
                    qa_pairs = []  # 清空批次数据
                    time.sleep(0.5)  # 避免请求过于频繁
                    
        except Exception as e:
            print(f"  处理第{idx}行数据时出错: {str(e)}")
            continue
    
    # 处理剩余的数据
    if qa_pairs:
        print(f"  调用API批量添加剩余 {len(qa_pairs)} 条数据...")
        result = call_batch_api(qa_pairs)
        
        if result.get("success"):
            batch_success = result.get("data", {}).get("success_count", 0)
            batch_failed = result.get("data", {}).get("failed_count", 0)
            total_success += batch_success
            total_failed += batch_failed
            print(f"  最后批次完成: 成功 {batch_success}, 失败 {batch_failed}")
        else:
            total_failed += len(qa_pairs)
            print(f"  最后批次失败: {result.get('message', '未知错误')}")
    
    print(f"工作表 {sheet_name} 处理完成")

end_time = time.time()
duration = end_time - start_time

print(f"\n=== 导入完成 ===")
print(f"总耗时: {duration:.2f} 秒")
print(f"QA数据 - 总成功: {total_success} 条")
print(f"QA数据 - 总失败: {total_failed} 条")
print(f"QA数据 - 成功率: {(total_success / (total_success + total_failed) * 100):.1f}%" if (total_success + total_failed) > 0 else "无数据")
print(f"图片处理 - 成功: {total_images_processed} 张")
print(f"图片处理 - 失败: {total_images_failed} 张")
print(f"图片处理 - 成功率: {(total_images_processed / (total_images_processed + total_images_failed) * 100):.1f}%" if (total_images_processed + total_images_failed) > 0 else "无图片数据")