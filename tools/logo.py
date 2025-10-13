import os
import base64
import mimetypes
import asyncio
import asyncpg
from pathlib import Path
import re
# text2sql配置
# DB_TYPE=postgresql
# DB_HOST=192.168.0.105
# DB_PORT=5432
# DB_USER=hzwl
# DB_PASSWORD=hzwl@12345
# DB_DATABASE=hzwl

# PostgreSQL 连接信息
DB_CONFIG = {
    "user": "hzwl",
    "password": "hzwl@12345",
    "database": "hzwl",
    "host": "192.168.0.105",
    "port": 5432,
}


LOGO_DIR = Path("/Users/hzwl/Documents/logo")  # 修改为你的目录
# =========================

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS airline_logos (
    airline_code CHAR(2) PRIMARY KEY,
    logo_data_uri TEXT NOT NULL
);
"""

INSERT_SQL = """
INSERT INTO airline_logos (airline_code, logo_data_uri)
VALUES ($1, $2)
ON CONFLICT (airline_code) DO UPDATE
SET logo_data_uri = EXCLUDED.logo_data_uri;
"""

# 允许的图片扩展（小写）
ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"}

# 扩展 -> mime 的兜底表（当 mimetypes 无法判断时）
EXT_TO_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
    ".ico": "image/vnd.microsoft.icon",
}

def infer_mime(file_path: Path) -> str | None:
    mime, _ = mimetypes.guess_type(str(file_path))
    if mime:
        return mime
    return EXT_TO_MIME.get(file_path.suffix.lower())

def extract_code(file_name: str) -> str | None:
    """
    尝试以正则从文件名提取两位字母航司码（示例 l_fm.png -> FM）。
    规则：
      1) 优先匹配末尾前的下划线 + 两字母 + 扩展（如 _fm.png）
      2) 若不命中，则首次匹配连续的两字母作为兜底（不推荐但兼容）
    """
    # 优先匹配像 l_fm.png、xx_fm.png 这种：下划线后两字母，紧接着扩展
    m = re.search(r'_([A-Za-z]{2})(?:\.[A-Za-z0-9]+)$', file_name)
    if m:
        return m.group(1).upper()
    # 兜底：寻找第一个连续的两字母
    m2 = re.search(r'([A-Za-z]{2})', file_name)
    if m2:
        return m2.group(1).upper()
    return None

async def read_file_base64(path: Path) -> str:
    def _read_and_b64():
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    return await asyncio.to_thread(_read_and_b64)

async def image_to_data_uri(path: Path) -> str:
    mime = infer_mime(path)
    if mime is None:
        raise ValueError(f"无法识别文件类型: {path}")
    b64 = await read_file_base64(path)
    return f"data:{mime};base64,{b64}"

async def save_logos():
    if not LOGO_DIR.exists() or not LOGO_DIR.is_dir():
        raise SystemExit(f"LOGO_DIR 不存在或不是目录: {LOGO_DIR}")

    pool = await asyncpg.create_pool(**DB_CONFIG)
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLE_SQL)

    try:
        for item in sorted(LOGO_DIR.iterdir()):
            # 跳过非文件、隐藏文件（macOS 的 .DS_Store 等）
            if not item.is_file():
                continue
            if item.name.startswith("."):
                # 跳过隐藏文件
                continue
            if item.suffix.lower() not in ALLOWED_EXTS:
                print(f"跳过非图片文件: {item.name}")
                continue

            code = extract_code(item.name)
            if not code:
                print(f"跳过无法解析二字码的文件: {item.name}")
                continue

            try:
                data_uri = await image_to_data_uri(item)
            except Exception as e:
                print(f"读取/编码失败，跳过 {item.name}：{e}")
                continue

            async with pool.acquire() as conn:
                await conn.execute(INSERT_SQL, code, data_uri)
            print(f"已写入: {code}  ({item.name})")

        print("所有 logo 处理完毕 ✅")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(save_logos())
