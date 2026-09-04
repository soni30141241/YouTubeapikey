import os
import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import aiosqlite

DB_DIR = "/data"
DB_NAME = os.path.join(DB_DIR, "ROYAL.db")
KEY_VALID_DAYS = 30
DAILY_LIMIT = 3000

def now_ist():
    return datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)

def make_key():
    return "ROYAL_" + secrets.token_hex(8)

def make_dates():
    created = now_ist()
    return created, created + timedelta(days=KEY_VALID_DAYS)

async def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, api_key TEXT NOT NULL, expiry_date TEXT NOT NULL, created_date TEXT)""")
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "expiry_date" not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN expiry_date TEXT")
        if "created_date" not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN created_date TEXT")
        await db.execute("""CREATE TABLE IF NOT EXISTS usage (user_id INTEGER NOT NULL, date TEXT NOT NULL, requests INTEGER DEFAULT 0, audio INTEGER DEFAULT 0, video INTEGER DEFAULT 0, PRIMARY KEY (user_id, date))""")
        await db.commit()

async def get_or_create_key(user_id: int):
    await init_db()
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT api_key, expiry_date, created_date FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            api_key = str(row[0]).strip()
            try:
                expiry_date = datetime.fromisoformat(str(row[1]))
            except Exception:
                expiry_date = datetime.min
            try:
                created_date = datetime.fromisoformat(str(row[2])) if row[2] else expiry_date - timedelta(days=30)
            except Exception:
                created_date = now_ist()
            if (not api_key.startswith("ROYAL_") or expiry_date <= now_ist() or expiry_date.year >= 2099):
                api_key = make_key()
                created_date, expiry_date = make_dates()
                await db.execute("UPDATE users SET api_key=?, created_date=?, expiry_date=? WHERE user_id=?", (api_key, created_date.isoformat(), expiry_date.isoformat(), user_id))
                await db.commit()
                return api_key, expiry_date, created_date, True
            return api_key, expiry_date, created_date, False
        api_key = make_key()
        created_date, expiry_date = make_dates()
        await db.execute("INSERT INTO users (user_id, api_key, expiry_date, created_date) VALUES (?, ?, ?, ?)", (user_id, api_key, expiry_date.isoformat(), created_date.isoformat()))
        await db.commit()
        return api_key, expiry_date, created_date, True

async def renew_key(user_id: int):
    await init_db()
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT api_key FROM users WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        api_key = str(row[0]).strip() if row and str(row[0]).strip().startswith("ROYAL_") else make_key()
        created_date, expiry_date = make_dates()
        await db.execute("UPDATE users SET api_key=?, created_date=?, expiry_date=? WHERE user_id=?", (api_key, created_date.isoformat(), expiry_date.isoformat(), user_id))
        await db.commit()
        return api_key, expiry_date, created_date

async def revoke_and_get_new_key(user_id: int):
    await init_db()
    async with aiosqlite.connect(DB_NAME) as db:
        new_key = make_key()
        created_date, expiry_date = make_dates()
        await db.execute("INSERT OR REPLACE INTO users (user_id, api_key, expiry_date, created_date) VALUES (?, ?, ?, ?)", (user_id, new_key, expiry_date.isoformat(), created_date.isoformat()))
        await db.commit()
        return new_key, expiry_date, created_date

async def verify_key(api_key: str):
    if not api_key:
        return False, "API Key is required"
    api_key = str(api_key).strip().strip("`\"'")
    if not api_key.startswith("ROYAL_"):
        return False, "Invalid API Key"
    await init_db()
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT expiry_date FROM users WHERE api_key=?", (api_key,))
        row = await cursor.fetchone()
        if not row:
            return False, "Invalid API Key"
        try:
            expiry_date = datetime.fromisoformat(str(row[0]))
        except Exception:
            return False, "Invalid API Key expiry"
        if expiry_date <= now_ist():
            return False, "API Key expired. Please generate a new key."
        return True, "Valid"

async def get_user_id_by_key(api_key: str):
    if not api_key:
        return None
    api_key = str(api_key).strip().strip("`\"'")
    await init_db()
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE api_key=?", (api_key,))
        row = await cursor.fetchone()
        return row[0] if row else None

async def get_usage(user_id: int):
    await init_db()
    today = now_ist().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT requests, audio, video FROM usage WHERE user_id=? AND date=?", (user_id, today))
        row = await cursor.fetchone()
        requests, audio, video = row if row else (0, 0, 0)
        cursor = await db.execute("SELECT COALESCE(SUM(requests),0), COALESCE(SUM(audio),0), COALESCE(SUM(video),0) FROM usage WHERE user_id=?", (user_id,))
        total = await cursor.fetchone()
        return {"requests": requests, "audio": audio, "video": video, "total_requests": total[0], "total_audio": total[1], "total_video": total[2]}

async def add_usage(user_id: int, usage_type: str):
    if usage_type not in {"request", "audio", "video"}:
        return False
    await init_db()
    today = now_ist().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO usage (user_id,date,requests,audio,video) VALUES (?, ?, 0, 0, 0)", (user_id, today))
        if usage_type == "request":
            await db.execute("UPDATE usage SET requests=requests+1 WHERE user_id=? AND date=?", (user_id, today))
        elif usage_type == "audio":
            await db.execute("UPDATE usage SET requests=requests+1, audio=audio+1 WHERE user_id=? AND date=?", (user_id, today))
        else:
            await db.execute("UPDATE usage SET requests=requests+1, video=video+1 WHERE user_id=? AND date=?", (user_id, today))
        await db.commit()
    return True

async def check_daily_limit(user_id: int):
    usage = await get_usage(user_id)
    return usage["requests"] < DAILY_LIMIT

async def delete_key(api_key: str):
    await init_db()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM users WHERE api_key=?", (api_key,))
        await db.commit()

async def get_all_users():
    await init_db()
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT user_id, api_key, expiry_date, created_date FROM users ORDER BY user_id DESC")
        return await cursor.fetchall()
                
