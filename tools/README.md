# Text2SQL训练工具

这个目录包含了用于训练text2sql模块的工具和数据。

## train_text2sql.py

这是一个命令行工具，用于向text2sql系统添加航班相关的表结构、示例问题和文档。

### 使用方法

```bash
# 添加所有内置训练数据
python tools/train_text2sql.py --all

# 仅添加DDL表结构
python tools/train_text2sql.py --ddl

# 仅添加示例问题和SQL
python tools/train_text2sql.py --questions

# 仅添加文档信息
python tools/train_text2sql.py --docs

# 从自定义JSON文件添加训练数据
python tools/train_text2sql.py --custom-file tools/data/flight_training_data.json

# 从Excel文件添加训练数据
python tools/train_text2sql.py --excel-file tools/data/flight_training_data.xlsx

# 组合使用
python tools/train_text2sql.py --ddl --questions --custom-file tools/data/flight_training_data.json
```

### 命令行参数

- `--all`: 添加所有内置训练数据（DDL、问题和文档）
- `--ddl`: 添加数据表结构
- `--questions`: 添加示例问题和SQL
- `--docs`: 添加文档信息
- `--custom-file`: 指定自定义训练数据的文件路径（JSON或Excel格式）
- `--excel-file`: 指定Excel格式的训练数据文件路径
- `--clear`: 清除现有训练数据（谨慎使用）

## 自定义训练数据

### JSON格式

您可以创建自定义的JSON文件来添加额外的训练数据。JSON文件的格式如下：

```json
{
    "ddl": [
        "CREATE TABLE example (id INTEGER PRIMARY KEY, name TEXT);"
    ],
    "questions": [
        {
            "question": "查询示例问题",
            "sql": "SELECT * FROM example WHERE name = '示例';"
        }
    ],
    "documentation": [
        "这是一条示例文档说明。"
    ]
}
```

### Excel格式

您也可以使用Excel文件来组织训练数据，Excel文件应包含三个sheet：

1. **ddl**: 包含DDL语句
   - 必须有一列名为`ddl`，包含数据表定义语句

2. **documents**: 包含文档信息
   - 必须有一列名为`document`，包含用于训练的文档文本

3. **qa**: 包含问题和SQL
   - 必须有两列，分别名为`question`和`sql`
   - `question`列包含用户问题
   - `sql`列包含对应的SQL查询语句

使用Excel格式需要安装pandas和openpyxl:
```bash
pip install pandas openpyxl
```

自定义训练数据文件应放在`tools/data/`目录下。

## 集成到应用中

在应用启动时，可以确保text2sql已经过训练：

```python
import asyncio
from tools.train_text2sql import train_text2sql
from argparse import Namespace

async def setup_text2sql():
    """确保text2sql已训练"""
    # 创建参数对象
    args = Namespace(
        all=True,
        ddl=False,
        questions=False,
        docs=False,
        custom_file=None,
        excel_file="tools/data/flight_training_data.xlsx",  # 可使用Excel文件
        clear=False
    )
    # 运行训练过程
    await train_text2sql(args)

# 在应用启动时调用
asyncio.run(setup_text2sql())
```

也可以通过Text2SqlService类进行训练：

```python
from agents.airport_service.services.text2sql_service import Text2SqlService

async def initialize_and_train():
    # 获取text2sql实例，并自动训练基础数据
    smart_sql = await Text2SqlService.get_instance()
    
    # 使用Excel文件进行额外训练
    await Text2SqlService.train("tools/data/flight_training_data.xlsx", is_excel=True)
    
    return smart_sql
```

## 训练数据说明

### 表结构

内置训练数据包含以下表：

- `flights`: 航班信息
- `airports`: 机场信息
- `airlines`: 航空公司信息
- `passengers`: 乘客信息
- `bookings`: 订票信息

自定义训练数据文件中添加了：

- `flight_schedules`: 航班时刻表信息

### 示例问题类型

内置的示例问题涵盖了多种查询场景：

1. 航班状态查询
2. 城市间航班查询
3. 延误航班查询
4. 航班预订查询
5. 机型查询
6. 航空公司航班查询
7. 航站楼和登机口查询
8. 统计查询 