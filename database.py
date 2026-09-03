import aiosqlite
from datetime import datetime, timedelta
import secrets

DB_NAME = "ROYAL.db"


# ==============================
# DATABASE INITIALIZE
# ==============================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                api_key TEXT,
                expiry_date TIMESTAMP
            )
        """)

        await db.commit()


# ==============================
# CREATE / GET API KEY
# ==============================
async def get_or_create_key(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            "SELECT api_key, expiry_date FROM users WHERE user_id = ?",
            (user_id,)
        )

        row = await cursor.fetchone()

        now = datetime.now()

        # ==============================
        # EXISTING USER
        # ==============================
        if row:
            api_key, expiry_str = row

            try:
                expiry_date = datetime.fromisoformat(str(expiry_str))
            except Exception:
                expiry_date = now

            # ==============================
            # KEY EXPIRED
            # ==============================
            if now > expiry_date:

                new_key = f"ROYAL_{secrets.token_hex(8)}"
                new_expiry = now + timedelta(days=30)

                await db.execute(
                    """
                    UPDATE users
                    SET api_key = ?, expiry_date = ?
                    WHERE user_id = ?
                    """,
                    (
                        new_key,
                        new_expiry.isoformat(),
                        user_id
                    )
                )

                await db.commit()

                return new_key, new_expiry, True

            # ==============================
            # KEY STILL VALID
            # ==============================
            return api_key, expiry_date, False

        # ==============================
        # NEW USER
        # ==============================
        new_key = f"ROYAL_{secrets.token_hex(8)}"
        new_expiry = now + timedelta(days=30)

        await db.execute(
            """
            INSERT INTO users
            (user_id, api_key, expiry_date)
            VALUES (?, ?, ?)
            """,
            (
                user_id,
                new_key,
                new_expiry.isoformat()
            )
        )

        await db.commit()

        return new_key, new_expiry, True


# ==============================
# VERIFY API KEY
# ==============================
async def verify_key(api_key: str):

    if not api_key:
        return False, "API Key is required"

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

        # ==============================
        # KEY NOT FOUND
        # ==============================
        if not row:
            return False, "Invalid API Key"

        try:
            expiry_date = datetime.fromisoformat(str(row[0]))
        except Exception:
            return False, "Invalid API Key expiry date"

        # ==============================
        # KEY EXPIRED
        # ==============================
        if datetime.now() > expiry_date:
            return False, "API Key Expired! Please go to bot and get a new one."

        # ==============================
        # VALID KEY
        # ==============================
        return True, "Valid"


# ==============================
# DELETE API KEY
# ==============================
async def delete_key(api_key: str):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            "DELETE FROM users WHERE api_key = ?",
            (api_key,)
        )

        await db.commit()


# ==============================
# GET ALL USERS
# ==============================
async def get_all_users():

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT user_id, api_key, expiry_date
            FROM users
            ORDER BY user_id DESC
            """
        )

        return await cursor.fetchall()
