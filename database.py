import aiosqlite
import os
import secrets

DB_DIR = "/data"
DB_NAME = os.path.join(DB_DIR, "ROYAL.db")


async def init_db():
    os.makedirs(DB_DIR, exist_ok=True)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                api_key TEXT NOT NULL
            )
        """)
        await db.commit()


async def get_or_create_key(user_id: int):
    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT api_key FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()

        # Purani key already hai → wahi key return
        if row:
            return row[0], None, False

        # First time → ek permanent key create
        new_key = "ROYAL_" + secrets.token_hex(8)

        await db.execute(
            "INSERT INTO users (user_id, api_key) VALUES (?, ?)",
            (user_id, new_key)
        )
        await db.commit()

        return new_key, None, True


async def verify_key(api_key: str):
    if not api_key:
        return False, "API Key is required"

    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT user_id FROM users WHERE api_key = ?",
            (api_key,)
        )
        row = await cursor.fetchone()

        if not row:
            return False, "Invalid API Key"

        return True, "Valid"


async def delete_key(api_key: str):
    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM users WHERE api_key = ?",
            (api_key,)
        )
        await db.commit()


async def get_all_users():
    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT user_id, api_key FROM users ORDER BY user_id DESC"
        )
        return await cursor.fetchall()
