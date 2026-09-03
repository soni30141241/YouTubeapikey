import aiosqlite
from datetime import datetime
import secrets
import os

# ==========================================
# RAILWAY VOLUME DATABASE
# ==========================================

DB_DIR = "/data"
DB_NAME = os.path.join(DB_DIR, "ROYAL.db")


# ==========================================
# INITIALIZE DATABASE
# ==========================================

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


# ==========================================
# GET OR CREATE PERMANENT API KEY
# ==========================================

async def get_or_create_key(user_id: int):

    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT api_key, expiry_date
            FROM users
            WHERE user_id = ?
            """,
            (user_id,)
        )

        row = await cursor.fetchone()

        # ==================================
        # EXISTING USER
        # ==================================

        if row:

            api_key, expiry_str = row

            try:
                expiry_date = datetime.fromisoformat(str(expiry_str))
            except Exception:
                expiry_date = datetime(2099, 12, 31)

            # SAME KEY — NEVER AUTO CHANGE
            return api_key, expiry_date, False

        # ==================================
        # NEW USER
        # ==================================

        new_key = "ROYAL_" + secrets.token_hex(8)

        # Permanent-style expiry
        expiry_date = datetime(2099, 12, 31)

        await db.execute(
            """
            INSERT INTO users
            (user_id, api_key, expiry_date)
            VALUES (?, ?, ?)
            """,
            (
                user_id,
                new_key,
                expiry_date.isoformat()
            )
        )

        await db.commit()

        return new_key, expiry_date, True


# ==========================================
# VERIFY API KEY
# ==========================================

async def verify_key(api_key: str):

    if not api_key:
        return False, "API Key is required"

    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT expiry_date
            FROM users
            WHERE api_key = ?
            """,
            (api_key,)
        )

        row = await cursor.fetchone()

        # Key doesn't exist
        if not row:
            return False, "Invalid API Key"

        try:
            expiry_date = datetime.fromisoformat(str(row[0]))
        except Exception:
            return False, "Invalid API Key expiry date"

        # Check expiry
        if datetime.now() >= expiry_date:
            return False, "API Key Expired"

        return True, "Valid"


# ==========================================
# DELETE / REVOKE KEY
# ==========================================

async def delete_key(api_key: str):

    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            DELETE FROM users
            WHERE api_key = ?
            """,
            (api_key,)
        )

        await db.commit()


# ==========================================
# GET ALL USERS
# ==========================================

async def get_all_users():

    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT user_id, api_key, expiry_date
            FROM users
            ORDER BY user_id DESC
            """
        )

        return await cursor.fetchall()
