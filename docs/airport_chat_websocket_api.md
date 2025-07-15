# 机场智能客服 WebSocket 聊天接口协议

## 1. 接口概述

## 2. 基本信息

- **接口路径**: `/api/v1/airport-assistant/chat/ws`
- **协议类型**: WebSocket
- **连接方式**: 全双工实时通信
- **消息格式**: JSON
- **支持功能**: 文本对话、图片识别、表单交互、多语言支持

## 3. 连接建立

```javascript
const ws = new WebSocket('ws://192.168.0.200/api/v1/airport-assistant/chat/ws');

ws.onopen = function(event) {
    console.log('WebSocket 连接已建立');
};

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('收到消息:', message);
};

ws.onerror = function(error) {
    console.error('WebSocket 错误:', error);
};

ws.onclose = function(event) {
    console.log('WebSocket 连接已关闭');
};
```

## 4. 请求协议

### 4.1 消息结构

```json
{
  "thread_id": "会话ID",
  "user_id": "用户唯一标识",
  "query": "用户输入的文本内容",
  "image": {
    "filename": "图片文件名.jpg",
    "content_type": "image/jpeg",
    "data": "Base64编码的图片数据"
  },
  "metadata": {
    "Is_translate": false,
    "Is_emotion": false
  },
  "token": "认证令牌"
}
```

### 4.2 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| thread_id | string | 是 | 会话标识，LangGraph利用此ID管理会话状态 |
| user_id | string | 是 | 用户唯一标识，用于用户画像关联 |
| query | string | 条件 | 用户当前输入内容，与image至少需要一项 |
| image | object | 条件 | 图片对象，包含文件信息和base64数据，与query至少需要一项 |
| metadata | object | 否 | 可选的上下文信息和系统参数 |
| token | string | 否 | 认证令牌，可选 |

### 4.3 metadata 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| Is_translate | boolean | 是否启用翻译功能 |
| Is_emotion | boolean | 是否启用情感分析 |

### 4.4 image 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| filename | string | 是 | 图片文件名，包含扩展名 |
| content_type | string | 是 | 图片MIME类型，如 image/jpeg、image/png |
| data | string | 是 | Base64编码的图片数据 |

### 4.5 请求示例

#### 4.5.1 纯文本查询

```json
{
  "thread_id": "thread_123456",
  "user_id": "user_789",
  "query": "我想查询今天飞往北京的航班",
  "metadata": {
    "Is_translate": false,
    "Is_emotion": false
  }
}
```

#### 4.5.2 图片查询

```json
{
  "thread_id": "thread_123456",
  "user_id": "user_789",
  "query": "这是我的登机牌，请帮我查看航班信息",
  "image": {
    "filename": "boarding_pass.jpg",
    "content_type": "image/jpeg",
    "data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
  },
  "metadata": {
    "Is_translate": false,
    "Is_emotion": false
  }
}
```

## 5. 响应协议

响应采用结构化JSON消息格式，每个消息包含事件类型和数据内容：

```json
{
  "event": "事件类型",
  "data": {
    "id": "事件唯一标识",
    "sequence": 1,
    "content": {
      // 根据事件类型不同而变化
    }
  }
}
```

## 6. 事件类型说明

| 事件类型 | 说明 | 触发时机 |
|----------|------|----------|
| start | 会话开始标记 | 接收到用户消息后立即发送 |
| text | 文本类响应 | 返回文本内容时 |
| form | 交互式表单 | 需要用户填写信息时 |
| flight_list | 航班号列表展示 | 返回多个航班号，供用户独立订阅 |
| end | 响应结束标记 | 所有处理完成后发送 |
| error | 错误信息 | 处理异常时发送 |

## 7. 事件数据结构

### 7.1 开始事件 (event: start)

```json
{
  "event": "start",
  "thread_id": "thread_123",
  "user_id": "user_456"
}
```

### 7.2 文本响应 (event: text)

```json
{
  "event": "text",
  "data": {
    "id": "text-1672847123456-1",
    "sequence": 1,
    "content": {
      "text": "您好！我是机场智能客服，很高兴为您服务。请问您需要什么帮助？",
      "format": "plain"
    }
  }
}
```

#### 7.2.1 文本格式选项

| 格式选项 | 说明 | 示例 |
|----------|------|------|
| plain | 纯文本格式，不包含任何样式 | "您好！欢迎使用机场服务" |
| markdown | Markdown格式，支持标题、列表、强调等基本格式 | "## 航班信息\n* 航班号: **MU5735**" |

### 7.3 表单响应 (event: form)

```json
{
  "event": "form",
  "data": {
    "id": "form-1672847123456-business",
    "sequence": 2,
    "content": {
      "form_id": "business-1672847123",
      "title": "轮椅租赁申请",
      "description": "请填写以下信息完成轮椅租赁申请",
      "action": "/api/v1/business/wheelchair-rental",
      "fields": [
        {
          "id": "cjr",
          "type": "text",
          "label": "预约人姓名",
          "placeholder": "请输入预约人姓名",
          "required": true,
          "value": "张三"
        },
        {
          "id": "id_number",
          "type": "text",
          "label": "身份证号码",
          "placeholder": "请输入18位身份证号码",
          "required": true,
          "validation": {
            "pattern": "^[0-9]{18}$",
            "error_message": "请输入有效的18位身份证号码"
          }
        },
        {
          "id": "cjrdh",
          "type": "tel",
          "label": "联系电话",
          "placeholder": "请输入11位手机号",
          "required": true,
          "validation": {
            "pattern": "^1[3-9][0-9]{9}$",
            "error_message": "请输入有效的11位手机号码"
          }
        },
        {
          "id": "rq",
          "type": "datetime-local",
          "label": "航班日期",
          "placeholder": "请选择航班日期",
          "required": true
        },
        {
          "id": "hbxx",
          "type": "text",
          "label": "航班号",
          "placeholder": "请输入航班号",
          "required": true
        }
      ],
      "buttons": [
        {
          "id": "submit",
          "label": "提交申请",
          "type": "submit"
        },
        {
          "id": "cancel",
          "label": "取消",
          "type": "cancel"
        }
      ],
      "info": {
        "service_description": "轮椅租赁服务免费提供给行动不便的旅客，仅限机场内使用，可在各航站楼问询台申请。"
      }
    }
  }
}
```

#### 7.3.1 表单字段类型

| 字段类型 | 说明 | 支持属性 |
|----------|------|----------|
| text | 文本输入框 | placeholder, maxlength, required, value, validation |
| number | 数字输入框 | min, max, step, required, value |
| email | 邮箱输入框 | placeholder, required, value, validation |
| tel | 电话输入框 | placeholder, pattern, required, value, validation |
| datetime-local | 日期时间选择器 | placeholder, required, value |
| select | 下拉选择框 | options, required, value |
| radio | 单选框 | options, required, value |
| checkbox | 复选框 | options, value |
| textarea | 多行文本框 | placeholder, rows, maxlength, value |

#### 7.3.2 字段验证 (validation)

表单字段可包含 validation 对象进行输入验证：

```json
{
  "validation": {
    "pattern": "正则表达式",
    "error_message": "验证失败时的错误提示"
  }
}
```

#### 7.3.3 按钮类型

| 按钮类型 | 说明 | 样式 |
|----------|------|------|
| submit | 提交按钮 | 高亮显示，用于表单提交 |
| cancel | 取消按钮 | 普通显示，用于取消操作 |
| primary | 主要按钮 | 高亮显示，用于主要操作 |
| secondary | 次要按钮 | 普通显示，用于次要操作 |
| danger | 危险按钮 | 警告色显示，用于删除等操作 |

#### 7.3.4 表单信息 (info)

表单可包含 info 对象提供额外信息：

```json
{
  "info": {
    "service_description": "服务说明文字"
  }
}
```

### 7.4 航班号列表响应 (event: flight_list)

```json
{
  "event": "flight_list",
  "data": {
    "id": "flight_list-1720593765000-1",
    "sequence": 3,
    "content": {
      "title": "以下是为您找到的航班号：",
      "flights": [
        {
          "flight_number": "CZ1234",
          "subscribe_supported": true
        },
        {
          "flight_number": "MU5678",
          "subscribe_supported": true
        },
        {
          "flight_number": "ZH9999",
          "subscribe_supported": false
        }
      ],
      "action_hint": "点击每个航班右侧的按钮可订阅航班动态"
    }
  }
}

#### 7.4.1 字段说明
| 字段                   | 类型      | 说明            |
| -------------------- | ------- | ------------- |
| title                | string  | 列表标题或提示信息     |
| flights              | array   | 航班对象数组        |
| flight\_number       | string  | 航班号           |
| subscribe\_supported | boolean | 是否支持订阅        |
| action\_hint         | string  | 展示在前端的提示语（可选） |


#### 7.4.2 前端建议
展示航班号列表；

支持在每个航班号后展示“订阅”按钮；

subscribe_supported: false 的航班，按钮应置灰或禁用；



### 7.5 结束事件 (event: end)

```json
{
  "event": "end",
  "data": {
    "id": "end-1672847123456-1",
    "sequence": 10,
    "content": {
      "suggestions": ["查询行李规定", "值机办理", "航班动态"],
      "metadata": {
        "processing_time": "1.2s",
        "results_count": 3
      }
    }
  }
}
```

### 7.6 错误事件 (event: error)

```json
{
  "event": "error",
  "data": {
    "id": "error-service_unavailable-1672847123456",
    "sequence": 1,
    "content": {
      "error_code": "service_unavailable",
      "error_message": "服务暂时不可用，请稍后再试"
    }
  }
}
```

#### 7.6.1 错误代码说明

| 错误代码 | 说明 | 处理建议 |
|----------|------|----------|
| invalid_json | JSON格式错误 | 检查请求格式是否正确 |
| missing_fields | 必要字段缺失 | 确保提供必要的字段信息 |
| service_unavailable | 服务不可用 | 稍后重试或联系客服 |
| authentication_failed | 认证失败 | 检查token是否有效 |
| rate_limit_exceeded | 请求频率超限 | 降低请求频率 |

## 8. 完整对话示例

### 8.1 客户端发送消息

```json
{
  "thread_id": "thread_20241224_001",
  "user_id": "passenger_12345",
  "query": "我想办理值机手续",
  "metadata": {
    "Is_translate": false,
    "Is_emotion": false
  }
}
```

### 8.2 服务端响应序列

#### 响应1: 开始事件
```json
{
  "event": "start",
  "thread_id": "thread_20241224_001",
  "user_id": "passenger_12345"
}
```

#### 响应2: 文本事件
```json
{
  "event": "text",
  "data": {
    "id": "text-1672847123456-1",
    "sequence": 1,
    "content": {
      "text": "您好！我来帮您办理值机手续。为了更好地为您服务，请提供以下信息：",
      "format": "plain"
    }
  }
}
```

#### 响应3: 表单事件
```json
{
  "event": "form",
  "data": {
    "id": "form-1672847123456-checkin",
    "sequence": 2,
    "content": {
      "form_id": "checkin-1672847123",
      "title": "值机办理",
      "description": "请填写您的航班信息",
      "action": "/api/v1/checkin/submit",
      "fields": [
        {
          "id": "booking_reference",
          "label": "订票号/确认号",
          "type": "text",
          "required": true,
          "placeholder": "6位订票号码"
        },
        {
          "id": "passenger_surname",
          "label": "旅客姓氏",
          "type": "text",
          "required": true,
          "placeholder": "请输入姓氏"
        }
      ],
      "buttons": [
        {
          "id": "submit",
          "label": "开始值机",
          "type": "primary",
          "action": "submit"
        }
      ]
    }
  }
}
```

#### 响应4: 结束事件
```json
{
  "event": "end",
  "data": {
    "id": "end-1672847123456-1",
    "sequence": 3,
    "content": {
      "suggestions": ["查询航班状态", "选择座位", "行李托运"],
      "metadata": {
        "processing_time": "0.8s",
        "results_count": 1
      }
    }
  }
}
```

## 9. 错误处理

### 9.1 连接错误

当 WebSocket 连接失败时，客户端应实现重连机制：

```javascript
function connectWebSocket() {
    const ws = new WebSocket('ws://your-domain/api/v1/airport-assistant/chat/ws');
    
    ws.onclose = function(event) {
        console.log('连接关闭，5秒后重连...');
        setTimeout(connectWebSocket, 5000);
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket 错误:', error);
    };
}
```

### 9.2 消息发送失败

确保在连接建立后发送消息：

```javascript
function sendMessage(message) {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
    } else {
        console.error('WebSocket 连接未建立');
    }
}
```

## 12. 版本历史

| 版本        | 日期             | 更新内容                                    |
| --------- | -------------- | --------------------------------------- |
| 1.0.0     | 2024-12-24     | 初始版本，支持基本对话功能                           |
| 1.1.0     | 2024-12-24     | 增加图片识别和表单交互功能                            |
| 1.2.0     | 025-07-10      | 新增 `flight_list` 事件，仅返回航班号，支持独立订阅展示 |
