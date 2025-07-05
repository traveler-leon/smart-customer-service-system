# 图片处理工具类使用指南

## 概述

`ImageHandler` 是一个用于处理图片上传、保存和URL生成的工具类。它提供了统一的图片处理接口，可以在项目的任何地方复用。

## 主要功能

- 图片数据验证（格式、大小、类型）
- 图片保存到本地存储
- 生成唯一的文件名防止冲突
- 生成可访问的图片URL
- 图片删除功能

## 快速开始

### 1. 导入工具类

```python
from common.image_handler import default_image_handler
```

### 2. 基本使用

```python
# 图片数据格式
image_data = {
    "filename": "example.jpg",
    "content_type": "image/jpeg",
    "data": "base64_encoded_image_data..."
}

# 处理图片
try:
    result = default_image_handler.process_image(image_data, "http://localhost:8081/")
    print(f"图片URL: {result['image_url']}")
    print(f"文件路径: {result['file_path']}")
    print(f"文件名: {result['filename']}")
except ValueError as e:
    print(f"图片处理失败: {str(e)}")
```

## 详细API

### ImageHandler 类

#### 初始化参数

```python
handler = ImageHandler(
    upload_dir="static/uploads",      # 上传目录
    allowed_types=[                   # 允许的图片类型
        'image/jpeg', 'image/jpg', 
        'image/png', 'image/gif', 
        'image/webp'
    ],
    max_size=10 * 1024 * 1024        # 最大文件大小（字节）
)
```

#### 主要方法

##### `process_image(image_data, base_url)`

处理图片上传的一站式方法。

**参数：**
- `image_data`: 图片数据字典
- `base_url`: 服务器基础URL

**返回：**
```python
{
    'file_path': 'static/uploads/1234567890_abc123_image.jpg',
    'image_url': 'http://localhost:8081/static/uploads/1234567890_abc123_image.jpg',
    'filename': '1234567890_abc123_image.jpg'
}
```

##### `validate_image_data(image_data)`

验证图片数据格式。

**参数：**
- `image_data`: 图片数据字典

**返回：**
- `bool`: 验证结果

##### `save_image(image_data)`

保存图片到本地。

**参数：**
- `image_data`: 图片数据字典

**返回：**
- `str`: 保存的文件路径

##### `generate_url(file_path, base_url)`

生成图片访问URL。

**参数：**
- `file_path`: 文件路径
- `base_url`: 基础URL

**返回：**
- `str`: 图片访问URL

##### `delete_image(file_path)`

删除图片文件。

**参数：**
- `file_path`: 文件路径

**返回：**
- `bool`: 删除结果

## 使用示例

### 在 WebSocket 中使用

```python
from common.image_handler import default_image_handler

@router.websocket("/chat/ws")
async def websocket_endpoint(websocket: WebSocket):
    image_data = message_data.get("image", None)
    if image_data:
        try:
            result = default_image_handler.process_image(image_data, base_url)
            image_url = result['image_url']
            # 继续处理...
        except ValueError as e:
            # 处理错误...
```

### 在 HTTP 接口中使用

```python
from common.image_handler import default_image_handler

@router.post("/upload")
async def upload_image(request: Request, file: UploadFile = File(...)):
    # 转换为统一格式
    image_data = {
        "filename": file.filename,
        "content_type": file.content_type,
        "data": base64.b64encode(await file.read()).decode('utf-8')
    }
    
    try:
        result = default_image_handler.process_image(image_data, str(request.base_url))
        return {"url": result['image_url']}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### 自定义配置

```python
from common.image_handler import ImageHandler

# 创建自定义配置的处理器
custom_handler = ImageHandler(
    upload_dir="custom/upload/path",
    allowed_types=['image/jpeg', 'image/png'],
    max_size=5 * 1024 * 1024  # 5MB
)

# 使用自定义处理器
result = custom_handler.process_image(image_data, base_url)
```

## 图片数据格式

### 标准格式

```python
{
    "filename": "example.jpg",           # 文件名
    "content_type": "image/jpeg",        # MIME类型
    "data": "base64_encoded_data..."     # Base64编码的图片数据
}
```

### 支持的图片类型

- `image/jpeg`
- `image/jpg`
- `image/png`
- `image/gif`
- `image/webp`

## 错误处理

工具类会抛出以下异常：

- `ValueError`: 图片数据验证失败
- `IOError`: 文件保存失败

建议在使用时进行适当的异常处理：

```python
try:
    result = default_image_handler.process_image(image_data, base_url)
except ValueError as e:
    # 处理验证错误
    logger.error(f"图片验证失败: {str(e)}")
except IOError as e:
    # 处理文件保存错误
    logger.error(f"文件保存失败: {str(e)}")
```

## 安全考虑

1. **文件类型验证**：只允许指定的图片类型
2. **文件大小限制**：防止上传过大的文件
3. **文件名安全**：自动生成唯一文件名，防止路径遍历攻击
4. **目录限制**：文件只能保存在指定的上传目录中

## 注意事项

1. 确保 `static/uploads` 目录存在且可写
2. 配置好静态文件服务以提供图片访问
3. 定期清理不再需要的图片文件
4. 考虑使用云存储服务处理大量图片上传 