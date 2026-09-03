import os
import io
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import database


API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

app = Client(
    "ROYALKeyBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


API_URL = "https://youtubeapikey-production-701a.up.railway.app"


def get_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔑 View Your Key",
                callback_data="view_key"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Usage",
                callback_data="view_key"
            )
        ],
        [
            InlineKeyboardButton(
                "📚 API Docs",
                callback_data="api_docs"
            ),
            InlineKeyboardButton(
                "💬 Support ↗",
                url="https://t.me/ll_ROYAL_ABOUT_ll"
            )
        ],
        [
            InlineKeyboardButton(
                "📢 Channel ↗",
                url="https://t.me/ll_ROYAL_ABOUT_ll"
            )
        ]
    ])


@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):

    user_id = message.from_user.id

    await database.get_or_create_key(user_id)

    text = (
        f"👋 **Welcome {message.from_user.mention}!**\n\n"
        "**Main Menu**"
    )

    await message.reply_text(
        text,
        reply_markup=get_main_menu_keyboard()
    )


async def render_key_page(query, user_id):

    api_key, expiry_date, _ = await database.get_or_create_key(user_id)

    now = datetime.now()

    days_left = max(
        (expiry_date - now).days,
        0
    )

    expiry_str = expiry_date.strftime(
        "%d %b %Y, %I:%M %p"
    )

    created_date = expiry_date - timedelta(days=30)

    created_str = created_date.strftime(
        "%d %b %Y, %I:%M %p"
    )

    text = (
        "🔑 **Your API Key**\n\n"

        "**API Key:**\n"
        f"`{api_key}`\n\n"

        "**Status:** 🟢 Active\n"
        "**Daily Limit:** 3,000\n\n"

        "**Today's Usage:**\n"
        "📊 Requests: 0\n"
        "🎵 Audio: 0\n"
        "🎬 Video: 0\n\n"

        "**All-Time Usage:**\n"
        "📊 Total Requests: 0\n"
        "🎵 Total Audio: 0\n"
        "🎬 Total Video: 0\n\n"

        f"**Created:** {created_str}\n"
        f"**Expires:** {expiry_str}\n"
        f"**Days Left:** {days_left} days"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔄 Renew",
                callback_data="action_renew"
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 Revoke & Get New Key",
                callback_data="action_revoke"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="main_menu"
            )
        ]
    ])

    await query.message.edit_text(
        text,
        reply_markup=keyboard
    )


@app.on_callback_query()
async def on_callback(client, query):

    user_id = query.from_user.id
    data = query.data

    await query.answer()

    if data == "main_menu":

        text = (
            f"👋 **Welcome {query.from_user.mention}!**\n\n"
            "**Main Menu**"
        )

        await query.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard()
        )

    elif data == "view_key":

        await render_key_page(
            query,
            user_id
        )

    elif data == "api_docs":

        text = (
            "**📚 API Documentation**\n\n"

            f"**Base URL:**\n"
            f"`{API_URL}`\n\n"

            "**Primary API:**\n"
            f"`{API_URL}/download`\n\n"

            "**Endpoint:** `GET /download`\n\n"

            "**Parameters:**\n"
            "• `url` — YouTube URL\n"
            "• `type` — audio/video\n"
            "• `api_key` — Your API key"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "⬇️ Download Youtube.py",
                    callback_data="dl_file"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data="main_menu"
                )
            ]
        ])

        await query.message.edit_text(
            text,
            reply_markup=keyboard
        )

    elif data in [
        "action_renew",
        "action_revoke"
    ]:

        api_key, expiry_date, is_new = (
            await database.get_or_create_key(user_id)
        )

        if not is_new:

            now = datetime.now()

            days_left = max(
                (expiry_date - now).days,
                0
            )

            await query.answer(
                f"⚠️ आपकी Key अभी valid है!\n"
                f"नई Key {days_left} दिन बाद generate होगी।",
                show_alert=True
            )

        else:

            await query.answer(
                "✅ नई Key generate कर दी गई है!",
                show_alert=True
            )

            await render_key_page(
                query,
                user_id
            )

    elif data == "dl_file":

        await query.answer(
            "Preparing file..."
        )

        # Correct YouTube client code
        youtube_code = r'''
import os
import re
import aiohttp


API_URL = os.environ.get(
    "ROYAL_API_URL",
    "https://youtubeapikey-production-701a.up.railway.app"
).rstrip("/")

API_KEY = os.environ.get(
    "ROYAL_API_KEY",
    "YOUR_API_KEY_HERE"
)


DOWNLOAD_DIR = "downloads"


def get_youtube_url(link: str) -> str:

    link = str(link).strip()

    if "youtube.com/" in link or "youtu.be/" in link:
        return link

    return f"https://www.youtube.com/watch?v={link}"


def get_video_id(link: str) -> str:

    link = str(link).strip()

    if "youtu.be/" in link:
        return link.split("youtu.be/")[-1].split("?")[0]

    if "v=" in link:
        return link.split("v=")[-1].split("&")[0]

    return link


async def api_download(
    link: str,
    media_type: str,
    timeout: int = 600
):

    full_url = get_youtube_url(link)

    video_id = get_video_id(full_url)

    if not video_id:
        return None

    os.makedirs(
        DOWNLOAD_DIR,
        exist_ok=True
    )

    extension = (
        "mp3"
        if media_type == "audio"
        else "mp4"
    )

    file_path = os.path.join(
        DOWNLOAD_DIR,
        f"{video_id}.{extension}"
    )

    try:

        timeout_config = aiohttp.ClientTimeout(
            total=timeout
        )

        async with aiohttp.ClientSession() as session:

            async with session.get(
                f"{API_URL}/download",
                params={
                    "url": full_url,
                    "type": media_type,
                    "api_key": API_KEY
                },
                timeout=timeout_config
            ) as response:

                if response.status != 200:
                    return None

                with open(
                    file_path,
                    "wb"
                ) as file:

                    async for chunk in response.content.iter_chunked(
                        131072
                    ):

                        file.write(chunk)

        if (
            os.path.exists(file_path)
            and os.path.getsize(file_path) > 0
        ):
            return file_path

        return None

    except Exception:

        if os.path.exists(file_path):

            try:
                os.remove(file_path)
            except Exception:
                pass

        return None


async def download_song(link: str):

    return await api_download(
        link,
        "audio",
        600
    )


async def download_video(link: str):

    return await api_download(
        link,
        "video",
        600
    )
'''

        file_bytes = io.BytesIO(
            youtube_code.encode("utf-8")
        )

        file_bytes.name = "Youtube.py"

        await client.send_document(
            chat_id=query.message.chat.id,
            document=file_bytes,
            caption=(
                "✅ **Ready-to-use Youtube.py**\n\n"
                "Set `ROYAL_API_KEY` in your environment variables."
            )
        )


if __name__ == "__main__":

    print(
        "ROYAL Key Bot starting..."
    )

    app.run()
