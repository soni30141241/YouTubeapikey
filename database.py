import aiosqlite
import secrets
from datetime import datetime, timedelta

DB_NAME = "ROYAL.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        await db.commit()


async def get_or_create_key(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT api_key, expires_at FROM api_keys WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()

        if row:
            api_key, expires_at = row

            try:
                expiry = datetime.fromisoformat(expires_at)

                if expiry > datetime.utcnow():
                    return api_key

            except Exception:
                pass

        api_key = "ROYAL_" + secrets.token_hex(16)
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(days=30)

        await db.execute(
            """
            INSERT OR REPLACE INTO api_keys
            (id, api_key, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                api_key,
                created_at.isoformat(),
                expires_at.isoformat()
            )
        )

        await db.commit()

        return api_key


async def verify_key(api_key):
    if not api_key:
        return False, "API key is required"

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT expires_at
            FROM api_keys
            WHERE api_key = ?
            """,
            (api_key,)
        )

        row = await cursor.fetchone()

        if not row:
            return False, "Invalid API key"

        expires_at = row[0]

        try:
            expiry = datetime.fromisoformat(expires_at)

            if expiry <= datetime.utcnow():
                return False, "API key expired"

        except Exception:
            return False, "Invalid expiry date"

        return True, "Valid API key"


async def delete_key(api_key):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM api_keys WHERE api_key = ?",
            (api_key,)
        )
        await db.commit()


async def get_all_keys():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT id, api_key, created_at, expires_at
            FROM api_keys
            ORDER BY id DESC
            """
        )

        return await cursor.fetchall()
