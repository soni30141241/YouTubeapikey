import os
import secrets
from datetime import datetime, timedelta

import aiosqlite

DB_DIR = "/data"
DB_NAME = os.path.join(DB_DIR, "ROYAL.db")
KEY_VALID_DAYS = 30

def new_expiry():
    return datetime.now() + timedelta(days=KEY_VALID_DAYS)


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
                (new_expiry().isoformat(),)
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

        # Existing user: keep the ROYAL key while it is within its 30-day validity.
        if row and row[0]:
            api_key = str(row[0]).strip()
            try:
                expiry_date = datetime.fromisoformat(str(row[1]))
            except Exception:
                expiry_date = datetime.min

            if (not api_key.startswith("ROYAL_")) or expiry_date <= datetime.now() or expiry_date.year >= 2099:
                api_key = make_key()
                expiry_date = new_expiry()
                await db.execute(
                    "UPDATE users SET api_key = ?, expiry_date = ? WHERE user_id = ?",
                    (api_key, expiry_date.isoformat(), user_id)
                )
                await db.commit()
                return api_key, expiry_date, True

            return api_key, expiry_date, False

        # New user = create exactly one key.
        api_key = make_key()
        expiry_date = new_expiry()

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
        expiry_date = new_expiry()

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
            "SELECT expiry_date FROM users WHERE api_key = ?",
            (api_key.strip(),)
        )
        row = await cursor.fetchone()
        if not row:
            return False, "Invalid API Key"

        try:
            expiry_date = datetime.fromisoformat(str(row[0]))
        except Exception:
            return False, "Invalid API Key expiry"

        if expiry_date <= datetime.now():
            return False, "API Key expired. Please generate a new key."

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
