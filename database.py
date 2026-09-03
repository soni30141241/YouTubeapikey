import os
import secrets
from datetime import datetime

import aiosqlite

DB_DIR = "/data"
DB_NAME = os.path.join(DB_DIR, "ROYAL.db")
PERMANENT_DATE = datetime(2099, 12, 31)


async def init_db():
    os.makedirs(DB_DIR, exist_ok=True)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                api_key TEXT NOT NULL,
                expiry_date TEXT NOT NULL
            )
        """)

        # Old database migration
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = {row[1] for row in await cursor.fetchall()}

        if "expiry_date" not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN expiry_date TEXT")
            await db.execute(
                "UPDATE users SET expiry_date = ? WHERE expiry_date IS NULL",
                (PERMANENT_DATE.isoformat(),)
            )

        await db.commit()


def make_key():
    return "ROYAL_" + secrets.token_hex(8)


async def get_or_create_key(user_id: int):
    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT api_key, expiry_date FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()

        # Existing user = ALWAYS return the same key.
        if row and row[0]:
            api_key = row[0]

            try:
                expiry_date = datetime.fromisoformat(str(row[1]))
            except Exception:
                expiry_date = PERMANENT_DATE
                await db.execute(
                    "UPDATE users SET expiry_date = ? WHERE user_id = ?",
                    (expiry_date.isoformat(), user_id)
                )
                await db.commit()

            return api_key, expiry_date, False

        # New user = create exactly one key.
        api_key = make_key()
        expiry_date = PERMANENT_DATE

        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, api_key, expiry_date) VALUES (?, ?, ?)",
            (user_id, api_key, expiry_date.isoformat())
        )
        await db.commit()

        return api_key, expiry_date, True


async def revoke_and_get_new_key(user_id: int):
    """Only an explicit user revoke action creates a new key."""
    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:
        new_key = make_key()
        expiry_date = PERMANENT_DATE

        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, api_key, expiry_date) VALUES (?, ?, ?)",
            (user_id, new_key, expiry_date.isoformat())
        )
        await db.commit()

        return new_key, expiry_date


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

        # Permanent until explicitly revoked.
        return True, "Valid"


async def delete_key(api_key: str):
    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM users WHERE api_key = ?", (api_key,))
        await db.commit()


async def get_all_users():
    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT user_id, api_key, expiry_date FROM users ORDER BY user_id DESC"
        )
        return await cursor.fetchall()
            
