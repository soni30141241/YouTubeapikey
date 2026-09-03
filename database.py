import os
import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import aiosqlite

DB_DIR = "/data"
DB_NAME = os.path.join(DB_DIR, "ROYAL.db")

KEY_VALID_DAYS = 30


def now_ist():
    return datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).replace(tzinfo=None)


def make_key():
    return "ROYAL_" + secrets.token_hex(8)


def make_dates():
    created = now_ist()
    expires = created + timedelta(days=KEY_VALID_DAYS)
    return created, expires


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

        cursor = await db.execute("PRAGMA table_info(users)")
        columns = {row[1] for row in await cursor.fetchall()}

        if "expiry_date" not in columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN expiry_date TEXT"
            )

        if "created_date" not in columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN created_date TEXT"
            )

        # पुराने RonakBots / Permanent / 2099 keys को हटाकर
        # नया ROYAL 30-days system लागू करें
        cursor = await db.execute("""
            SELECT user_id, api_key, expiry_date, created_date
            FROM users
        """)

        rows = await cursor.fetchall()

        for user_id, api_key, expiry, created in rows:

            old_key = (
                not api_key
                or not str(api_key).startswith("ROYAL_")
            )

            old_expiry = False

            try:
                expiry_dt = datetime.fromisoformat(str(expiry))
                if expiry_dt.year >= 2099:
                    old_expiry = True
            except Exception:
                old_expiry = True

            if old_key or old_expiry:

                new_key = make_key()
                new_created, new_expiry = make_dates()

                await db.execute("""
                    UPDATE users
                    SET api_key = ?,
                        created_date = ?,
                        expiry_date = ?
                    WHERE user_id = ?
                """, (
                    new_key,
                    new_created.isoformat(),
                    new_expiry.isoformat(),
                    user_id
                ))

            elif not created:

                try:
                    expiry_dt = datetime.fromisoformat(str(expiry))
                    created_dt = expiry_dt - timedelta(days=30)

                    await db.execute("""
                        UPDATE users
                        SET created_date = ?
                        WHERE user_id = ?
                    """, (
                        created_dt.isoformat(),
                        user_id
                    ))

                except Exception:
                    pass

        await db.commit()


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
                expiry = datetime.fromisoformat(str(row[1]))
            except Exception:
                expiry = datetime.min

            try:
                created = (
                    datetime.fromisoformat(str(row[2]))
                    if row[2]
                    else None
                )
            except Exception:
                created = None

            # Invalid / old / expired key
            if (
                not api_key.startswith("ROYAL_")
                or expiry <= now_ist()
                or expiry.year >= 2099
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

                return api_key, expiry, created, True

            return api_key, expiry, created, False

        # New user
        api_key = make_key()
        created, expiry = make_dates()

        await db.execute("""
            INSERT INTO users
            (user_id, api_key, expiry_date, created_date)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            api_key,
            expiry.isoformat(),
            created.isoformat()
        ))

        await db.commit()

        return api_key, expiry, created, True


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

        return api_key, expiry, created


async def revoke_and_get_new_key(user_id: int):

    await init_db()

    async with aiosqlite.connect(DB_NAME) as db:

        new_key = make_key()
        created, expiry = make_dates()

        await db.execute("""
            INSERT OR REPLACE INTO users
            (user_id, api_key, created_date, expiry_date)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            new_key,
            created.isoformat(),
            expiry.isoformat()
        ))

        await db.commit()

        return new_key, expiry, created


async def verify_key(api_key: str):

   
