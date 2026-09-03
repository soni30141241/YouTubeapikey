import sqlite3
import os
import secrets
from datetime import datetime, timedelta

DB_FILE = os.environ.get("DATABASE_FILE", "royal.db")


def _connect():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            user_id INTEGER PRIMARY KEY,
            api_key TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            requests INTEGER DEFAULT 0,
            audio_requests INTEGER DEFAULT 0,
            video_requests INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


async def get_or_create_key(user_id):
    import asyncio
    return await asyncio.to_thread(_get_or_create_key, user_id)


def _get_or_create_key(user_id):
    conn = _connect()

    row = conn.execute(
        "SELECT api_key, expiry_date FROM api_keys WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    now = datetime.now()

    if row:
        api_key, expiry_str = row
        expiry_date = datetime.fromisoformat(expiry_str)

        if expiry_date > now:
            conn.close()
            return api_key, expiry_date, False

    api_key = "Royal_" + secrets.token_urlsafe(24)
    created_at = now
    expiry_date = now + timedelta(days=30)

    conn.execute("""
        INSERT OR REPLACE INTO api_keys
        (user_id, api_key, created_at, expiry_date, requests, audio_requests, video_requests)
        VALUES (?, ?, ?, ?, 0, 0, 0)
    """, (
        user_id,
        api_key,
        created_at.isoformat(),
        expiry_date.isoformat()
    ))

    conn.commit()
    conn.close()

    return api_key, expiry_date, True


def verify_key(api_key):
    conn = _connect()

    row = conn.execute(
        "SELECT expiry_date FROM api_keys WHERE api_key = ?",
        (api_key,)
    ).fetchone()

    conn.close()

    if not row:
        return False

    try:
        expiry_date = datetime.fromisoformat(row[0])
        return expiry_date > datetime.now()
    except Exception:
        return False


def record_usage(api_key, media_type):
    conn = _connect()

    conn.execute(
        "UPDATE api_keys SET requests = requests + 1 WHERE api_key = ?",
        (api_key,)
    )

    if media_type == "audio":
        conn.execute(
            "UPDATE api_keys SET audio_requests = audio_requests + 1 WHERE api_key = ?",
            (api_key,)
        )

    elif media_type == "video":
        conn.execute(
            "UPDATE api_keys SET video_requests = video_requests + 1 WHERE api_key = ?",
            (api_key,)
        )

    conn.commit()
    conn.close()
