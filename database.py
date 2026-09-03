import aiosqlite
from datetime import datetime, timedelta
import secrets
import os

# Railway Volume
DB_DIR = "/data"
DB_NAME = os.path.join(DB_DIR, "ROYAL.db")


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
        await db.commit()


async def get_or_create_key(user_id: int):
    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT api_key, expiry_date FROM users WHERE user_id = ?",
            (user_id,)
        )

        row = await cursor.fetchone()
        now = datetime.now()

        if row:
            api_key, expiry_str = row

            try:
                expiry_date = datetime.fromisoformat(str(expiry_str))
            except Exception:
                expiry_date = now

            if now >= expiry_date:
                new_key = "ROYAL_" + secrets.token_hex(8)
                new_expiry = now + timedelta(days=30)

                await db.execute(
                    """
                    UPDATE users
                    SET api_key = ?, expiry_date = ?
                    WHERE user_id = ?
                    """,
                    (new_key, new_expiry.isoformat(), user_id)
                )
                await db.commit()

                return new_key, new_expiry, True

            return api_key, expiry_date, False

        new_key = "ROYAL_" + secrets.token_hex(8)
        new_expiry = now + timedelta(days=30)

        await db.execute(
            """
            INSERT INTO users (user_id, api_key, expiry_date)
            VALUES (?, ?, ?)
            """,
            (user_id, new_key, new_expiry.isoformat())
        )

        await db.commit()

        return new_key, new_expiry, True


async def verify_key(api_key: str):
    if not api_key:
        return False, "API Key is required"

    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT expiry_date FROM users WHERE api_key = ?",
            (api_key,)
        )

        row = await cursor.fetchone()

        if not row:
            return False, "Invalid API Key"

        try:
            expiry_date = datetime.fromisoformat(str(row[0]))
        except Exception:
            return False, "Invalid API Key expiry date"

        if datetime.now() >= expiry_date:
            return False, "API Key Expired! Please get a new key."

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
        cursor = await db.execute("""
            SELECT user_id, api_key, expiry_date
            FROM users
            ORDER BY user_id DESC
        """)

        return await cursor.fetchall()
