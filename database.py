import os
import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import aiosqlite


# =========================
# CONFIG
# =========================

DB_DIR = "/data"
DB_NAME = os.path.join(DB_DIR, "ROYAL.db")

KEY_VALID_DAYS = 30
DAILY_LIMIT = 3000


# =========================
# TIME
# =========================

def now_ist():
    return datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).replace(tzinfo=None)


# =========================
# KEY
# =========================

def make_key():
    return "ROYAL_" + secrets.token_hex(8)


def make_dates():
    created = now_ist()
    expires = created + timedelta(days=KEY_VALID_DAYS)
    return created, expires


# =========================
# DATABASE INIT
# =========================

async def init_db():

    os.makedirs(DB_DIR, exist_ok=True)

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                api_key TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                created_date TEXT
            )
        """)

        cursor = await db.execute(
            "PRAGMA table_info(users)"
        )

        columns = {
            row[1]
            for row in await cursor.fetchall()
        }

        if "expiry_date" not in columns:

            await db.execute(
                "ALTER TABLE users ADD COLUMN expiry_date TEXT"
            )

        if "created_date" not in columns:

            await db.execute(
                "ALTER TABLE users ADD COLUMN created_date TEXT"
            )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                user_id INTEGER,
                date TEXT,
                requests INTEGER DEFAULT 0,
                audio INTEGER DEFAULT 0,
                video INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, date)
            )
        """)

        await db.commit()


# =========================
# GET / CREATE KEY
# =========================

async def get_or_create_key(user_id: int):

    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT api_key, expiry_date, created_date
            FROM users
            WHERE user_id = ?
        """, (user_id,))

        row = await cursor.fetchone()

        # Existing user
        if row:

            api_key = str(row[0]).strip()

            try:
                expiry = datetime.fromisoformat(
                    str(row[1])
                )
            except Exception:
                expiry = datetime.min

            try:
                if row[2]:
                    created = datetime.fromisoformat(
                        str(row[2])
                    )
                else:
                    created = expiry - timedelta(days=30)

            except Exception:
                created = now_ist()

            # Old RonakBots key
            # OR expired key
            if (
                not api_key.startswith("ROYAL_")
                or expiry <= now_ist()
            ):

                api_key = make_key()
                created, expiry = make_dates()

                await db.execute("""
                    UPDATE users
                    SET api_key = ?,
                        created_date = ?,
                        expiry_date = ?
                    WHERE user_id = ?
                """, (
                    api_key,
                    created.isoformat(),
                    expiry.isoformat(),
                    user_id
                ))

                await db.commit()

                return (
                    api_key,
                    expiry,
                    created,
                    True
                )

            return (
                api_key,
                expiry,
                created,
                False
            )

        # New user
        api_key = make_key()
        created, expiry = make_dates()

        await db.execute("""
            INSERT INTO users (
                user_id,
                api_key,
                created_date,
                expiry_date
            )
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            api_key,
            created.isoformat(),
            expiry.isoformat()
        ))

        await db.commit()

        return (
            api_key,
            expiry,
            created,
            True
        )


# =========================
# RENEW KEY
# =========================

async def renew_key(user_id: int):

    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT api_key
            FROM users
            WHERE user_id = ?
        """, (user_id,))

        row = await cursor.fetchone()

        if row and str(row[0]).startswith("ROYAL_"):

            api_key = str(row[0]).strip()

        else:

            api_key = make_key()

        created, expiry = make_dates()

        await db.execute("""
            UPDATE users
            SET api_key = ?,
                created_date = ?,
                expiry_date = ?
            WHERE user_id = ?
        """, (
            api_key,
            created.isoformat(),
            expiry.isoformat(),
            user_id
        ))

        await db.commit()

        return (
            api_key,
            expiry,
            created
        )


# =========================
# REVOKE + NEW KEY
# =========================

async def revoke_and_get_new_key(user_id: int):

    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:

        new_key = make_key()

        created, expiry = make_dates()

        await db.execute("""
            INSERT OR REPLACE INTO users (
                user_id,
                api_key,
                created_date,
                expiry_date
            )
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            new_key,
            created.isoformat(),
            expiry.isoformat()
        ))

        await db.commit()

        return (
            new_key,
            expiry,
            created
        )


# =========================
# VERIFY API KEY
# =========================

async def verify_key(api_key: str):

    if not api_key:

        return False, "API Key is required"

    api_key = (
        str(api_key)
        .strip()
        .strip("`\"'")
    )

    if not api_key.startswith("ROYAL_"):

        return False, "Invalid API Key"

    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT expiry_date
            FROM users
            WHERE api_key = ?
        """, (api_key,))

        row = await cursor.fetchone()

        if not row:

            return False, "Invalid API Key"

        try:

            expiry = datetime.fromisoformat(
                str(row[0])
            )

        except Exception:

            return False, "Invalid API Key expiry"

        if expiry <= now_ist():

            return (
                False,
                "API Key expired. Please generate a new key."
            )

        return True, "Valid"


# =========================
# USAGE
# =========================

async def get_usage(user_id: int):

    await init_db()

    today = now_ist().strftime("%Y-%m-%d")

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT requests, audio, video
            FROM usage
            WHERE user_id = ?
            AND date = ?
        """, (
            user_id,
            today
        ))

        row = await cursor.fetchone()

        if row:

            today_requests = row[0]
            today_audio = row[1]
            today_video = row[2]

        else:

            today_requests = 0
            today_audio = 0
            today_video = 0

        cursor = await db.execute("""
            SELECT
                COALESCE(SUM(requests), 0),
                COALESCE(SUM(audio), 0),
                COALESCE(SUM(video), 0)
            FROM usage
            WHERE user_id = ?
        """, (user_id,))

        total = await cursor.fetchone()

        return {
            "requests": today_requests,
            "audio": today_audio,
            "video": today_video,
            "total_requests": total[0],
            "total_audio": total[1],
            "total_video": total[2]
        }


# =========================
# ADD USAGE
# =========================

async def add_usage(
    user_id: int,
    usage_type: str
):

    await init_db()

    today = now_ist().strftime("%Y-%m-%d")

    if usage_type not in {
        "request",
        "audio",
        "video"
    }:

        return False

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            INSERT OR IGNORE INTO usage (
                user_id,
                date,
                requests,
                audio,
                video
            )
            VALUES (?, ?, 0, 0, 0)
        """, (
            user_id,
            today
        ))

        if usage_type == "request":

            await db.execute("""
                UPDATE usage
                SET requests = requests + 1
                WHERE user_id = ?
                AND date = ?
            """, (
                user_id,
                today
            ))

        elif usage_type == "audio":

            await db.execute("""
                UPDATE usage
                SET requests = requests + 1,
                    audio = audio + 1
                WHERE user_id = ?
                AND date = ?
            """, (
                user_id,
                today
            ))

        elif usage_type == "video":

            await db.execute("""
                UPDATE usage
                SET requests = requests + 1,
                    video = video + 1
                WHERE user_id = ?
                AND date = ?
            """, (
                user_id,
                today
            ))

        await db.commit()

    return True


# =========================
# DAILY LIMIT
# =========================

async def check_daily_limit
