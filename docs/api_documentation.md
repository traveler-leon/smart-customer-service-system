# 智能推荐接口文档

## 概述

本文档描述了智能客户服务系统中的问题推荐和商业推荐接口。这些接口基于用户的输入（文本或图片）提供智能推荐服务。

## 基础信息

- **基础URL**: `http://localhost:8081`
- **Content-Type**: `application/json`
- **认证方式**: 通过请求头中的 `token` 字段进行认证

## 接口列表

### 1. 问题推荐接口

#### 接口信息
- **接口路径**: `/api/v1/question-recommend/questions`
- **请求方法**: `POST`
- **接口描述**: 基于用户的当前问题和上下文，推荐相关的后续问题

#### 请求参数

**Headers**
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| Content-Type | string | 是 | application/json |
| token | string | 否 | 用户认证令牌 |

**Body 参数**
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| thread_id | string | 是 | 会话标识，用于管理会话状态 |
| user_id | string | 是 | 用户唯一标识 |
| query | string | 否 | 用户当前输入内容（与image至少提供一个） |
| image | ImageData | 否 | 图片数据（与query至少提供一个） |
| metadata | object | 否 | 可选的上下文信息 |

**ImageData 对象**
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| filename | string | 是 | 图片文件名 |
| content_type | string | 是 | 图片MIME类型（如image/jpeg, image/png） |
| data | string | 是 | 图片数据（base64编码） |

**metadata 对象**
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| Is_translate | boolean | 否 | 是否需要翻译，默认false |
| Is_emotion | boolean | 否 | 是否需要情感分析，默认false |

#### 响应格式

**成功响应**
```json
{
  "ret_code": "000000",
  "ret_msg": "操作成功",
  "item": {
    "thread_id": "thread_123",
    "user_id": "user_456",
    "recommended_questions": [
      "是否可以携带液体上飞机？",
      "充电宝的容量限制是多少？",
      "登机时需要提前多久到达机场？"
    ],
    "processing_time": "1.23s"
  }
}
```

**错误响应**
```json
{
  "ret_code": "999999",
  "ret_msg": "问题推荐服务暂时不可用",
  "item": {
    "thread_id": "thread_123",
    "user_id": "user_456",
    "recommended_questions": [
      "是否可以携带小刀上飞机？",
      "充电宝可以放在随身行李里吗？",
      "充电宝的安全检查要求是什么？"
    ],
    "processing_time": "0s"
  }
}
```

#### 请求示例

**1. 纯文本请求**
```bash
curl -X POST "http://localhost:8081/api/v1/question-recommend/questions" \
  -H "Content-Type: application/json" \
  -H "token: your_token_here" \
  -d '{
    "thread_id": "thread_123",
    "user_id": "user_456",
    "query": "我想了解机场安检规定",
    "metadata": {
      "Is_translate": false,
      "Is_emotion": true
    }
  }'
```

**2. 纯图片请求**
```bash
curl -X POST "http://localhost:8081/api/v1/question-recommend/questions" \
  -H "Content-Type: application/json" \
  -H "token: your_token_here" \
  -d '{
    "thread_id": "thread_123",
    "user_id": "user_456",
    "image": {
      "filename": "airport_sign.jpg",
      "content_type": "image/jpeg",
      "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    },
    "metadata": {
      "Is_translate": false,
      "Is_emotion": false
    }
  }'
```

**3. 文本+图片请求**
```bash
curl -X POST "http://localhost:8081/api/v1/question-recommend/questions" \
  -H "Content-Type: application/json" \
  -H "token: your_token_here" \
  -d '{
    "thread_id": "thread_123",
    "user_id": "user_456",
    "query": "这个标志是什么意思？",
    "image": {
      "filename": "sign.png",
      "content_type": "image/png",
      "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    },
    "metadata": {
      "Is_translate": false,
      "Is_emotion": true
    }
  }'
```

---

### 2. 商业推荐接口

#### 接口信息
- **接口路径**: `/api/v1/business-recommend/business`
- **请求方法**: `POST`
- **接口描述**: 基于用户的当前问题和上下文，推荐相关的机场业务服务

#### 请求参数

**Headers**
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| Content-Type | string | 是 | application/json |
| token | string | 否 | 用户认证令牌 |

**Body 参数**
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| thread_id | string | 是 | 会话标识，用于管理会话状态 |
| user_id | string | 是 | 用户唯一标识 |
| query | string | 否 | 用户当前输入内容（与image至少提供一个） |
| image | ImageData | 否 | 图片数据（与query至少提供一个） |
| metadata | object | 否 | 可选的上下文信息 |

**ImageData 对象和 metadata 对象的格式与问题推荐接口相同**

#### 响应格式

**成功响应**
```json
{
  "ret_code": "000000",
  "ret_msg": "操作成功",
  "item": {
    "thread_id": "thread_123",
    "user_id": "user_456",
    "recommended_business": [
      "轮椅租赁服务",
      "无人陪伴儿童服务",
      "特殊餐食申请",
      "行李寄存服务",
      "贵宾休息室服务"
    ],
    "processing_time": "1.45s"
  }
}
```

**错误响应**
```json
{
  "ret_code": "999999",
  "ret_msg": "商业推荐服务暂时不可用",
  "item": {
    "thread_id": "thread_123",
    "user_id": "user_456",
    "recommended_business": [
      "轮椅租赁服务",
      "无人陪伴儿童服务",
      "特殊餐食申请",
      "行李寄存服务",
      "贵宾休息室服务"
    ],
    "processing_time": "0s"
  }
}
```

#### 请求示例

**1. 纯文本请求**
```bash
curl -X POST "http://localhost:8081/api/v1/business-recommend/business" \
  -H "Content-Type: application/json" \
  -H "token: your_token_here" \
  -d '{
    "thread_id": "thread_123",
    "user_id": "user_456",
    "query": "我行动不便，需要帮助",
    "metadata": {
      "Is_translate": false,
      "Is_emotion": true
    }
  }'
```

**2. 纯图片请求**
```bash
curl -X POST "http://localhost:8081/api/v1/business-recommend/business" \
  -H "Content-Type: application/json" \
  -H "token: your_token_here" \
  -d '{
    "thread_id": "thread_123",
    "user_id": "user_456",
    "image": {
      "filename": "service_area.jpg",
      "content_type": "image/jpeg",
      "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    },
    "metadata": {
      "Is_translate": false,
      "Is_emotion": false
    }
  }'
```

---

## 错误码说明

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 000000 | 操作成功 | - |
| 400 | 请求参数错误 | 检查请求参数是否符合要求 |
| 999999 | 服务暂时不可用 | 稍后重试或联系技术支持 |

## 常见问题

### Q1: 如何处理图片数据？
A1: 图片需要转换为base64编码的字符串，并提供正确的文件名和MIME类型。

### Q2: query和image都是可选的，但是需要至少提供一个？
A2: 是的，系统会在模型验证层面检查这个约束。如果两者都不提供，会返回400错误。

### Q3: metadata中有哪些可用的参数？
A3: 目前支持：
- `Is_translate`: 是否需要翻译
- `Is_emotion`: 是否需要情感分析
- 其他自定义参数也可以传递

### Q4: 如何处理并发请求？
A4: 系统支持并发处理，建议使用不同的thread_id来区分不同的会话。

### Q5: 响应时间大概是多少？
A5: 通常在1-3秒之间，具体取决于请求复杂度和服务器负载。

## 注意事项

1. **图片大小限制**: 建议图片大小不超过10MB
2. **支持的图片格式**: JPEG, PNG, GIF, WebP
3. **并发限制**: 建议单个用户的并发请求数不超过10个
4. **缓存机制**: 相同的请求可能会使用缓存结果，提升响应速度
5. **日志记录**: 所有请求都会被记录，用于系统监控和问题排查

## 更新日志

### v1.0.0 (2024-12-29)
- 初始版本发布
- 支持问题推荐和商业推荐功能
- 支持文本、图片和混合输入
- 添加参数验证和错误处理 