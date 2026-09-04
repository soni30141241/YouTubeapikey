import os
import io
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import database

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

API_URL = os.environ.get(
    "ROYAL_API_URL",
    "https://youtubeapikey-production-701a.up.railway.app"
)

app = Client(
    "ROYALKeyBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

DAILY_LIMIT = 3000


# =========================
# MAIN MENU
# =========================

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
                callback_data="usage"
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


# =========================
# START
# =========================

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


# =========================
# KEY PAGE
# =========================

async def render_key_page(query, user_id):

    api_key, expiry_date, created_date, _ = \
        await database.get_or_create_key(user_id)

    now = database.now_ist()

    if expiry_date > now:

        status = "🟢 Active"

        days_left = max(
            0,
            (expiry_date.date() - now.date()).days
        )

    else:

        status = "🔴 Expired"
        days_left = 0

    created_text = created_date.strftime(
        "%d %b %Y, %I:%M %p IST"
    )

    expiry_text = expiry_date.strftime(
        "%d %b %Y, %I:%M %p IST"
    )

    text = (
        "🔑 **Your API Key**\n\n"

        "**API Key:**\n"
        f"`{api_key}`\n\n"

        f"**Status:** {status}\n"
        f"**Daily Limit:** {DAILY_LIMIT:,}\n\n"

        "**Today's Usage:**\n"
        "📊 Requests: 0\n"
        "🎵 Audio: 0\n"
        "🎬 Video: 0\n\n"

        "**All-Time Usage:**\n"
        "📊 Total Requests: 0\n"
        "🎵 Total Audio: 0\n"
        "🎬 Total Video: 0\n\n"

        f"**Created:** {created_text}\n"
        f"**Expires:** {expiry_text}\n"
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


# =========================
# USAGE PAGE
# =========================

async def render_usage_page(query, user_id):

    try:
        usage = await database.get_usage(user_id)
    except Exception:
        usage = {
            "requests": 0,
            "audio": 0,
            "video": 0,
            "total_requests": 0,
            "total_audio": 0,
            "total_video": 0
        }

    text = (
        "📊 **Usage**\n\n"

        "**Today's Usage:**\n"
        f"📊 Requests: {usage.get('requests', 0)}\n"
        f"🎵 Audio: {usage.get('audio', 0)}\n"
        f"🎬 Video: {usage.get('video', 0)}\n\n"

        "**All-Time Usage:**\n"
        f"📊 Total Requests: "
        f"{usage.get('total_requests', 0)}\n"
        f"🎵 Total Audio: "
        f"{usage.get('total_audio', 0)}\n"
        f"🎬 Total Video: "
        f"{usage.get('total_video', 0)}\n\n"

        f"**Daily Limit:** {DAILY_LIMIT:,}"
    )

    keyboard = InlineKeyboardMarkup([
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


# =========================
# API DOCS
# =========================

async def render_api_docs(query):

    text = (
        "📚 **API Documentation**\n\n"

        f"**Base URL:**\n"
        f"`{API_URL}`\n\n"

        "**Audio Endpoint:**\n"
        f"`{API_URL}/audio`\n\n"

        "**Method:** `GET`\n\n"

        "**Parameters:**\n"
        "• `url` — YouTube URL\n"
        "• `type` — `audio` or `video`\n"
        "• `api_key` — Your ROYAL API key\n\n"

        "**Example:**\n"
        f"`{API_URL}/download?url=YOUTUBE_URL"
        f"&type=audio&api_key=YOUR_ROYAL_KEY`"
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
                "🌐 Swagger Docs",
                url=f"{API_URL}/docs"
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


# =========================
# CALLBACKS
# =========================

@app.on_callback_query()
async def on_callback(client, query):

    user_id = query.from_user.id
    data = query.data

    await query.answer()

    # MAIN MENU
    if data == "main_menu":

        text = (
            f"👋 **Welcome "
            f"{query.from_user.mention}!**\n\n"
            "**Main Menu**"
        )

        await query.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard()
        )

    # VIEW KEY
    elif data == "view_key":

        await render_key_page(
            query,
            user_id
        )

    # USAGE
    elif data == "usage":

        await render_usage_page(
            query,
            user_id
        )

    # API DOCS
    elif data == "api_docs":

        await render_api_docs(query)

    # RENEW
    elif data == "action_renew":

        await database.renew_key(user_id)

        await query.answer(
            "✅ Key renewed for 30 days.",
            show_alert=True
        )

        await render_key_page(
            query,
            user_id
        )

    # REVOKE
    elif data == "action_revoke":

        await database.revoke_and_get_new_key(
            user_id
        )

        await query.answer(
            "✅ New ROYAL key created for 30 days.",
            show_alert=True
        )

        await render_key_page(
            query,
            user_id
        )

    # DOWNLOAD YOUTUBE.PY
    elif data == "dl_file":

        await query.answer(
            "⏳ Preparing Youtube.py..."
        )

        current_api_key, _, _, _ = \
            await database.get_or_create_key(
                user_id
            )

        youtube_code = f'''import os
import aiohttp

API_URL = os.environ.get(
    "ROYAL_API_URL",
    "{API_URL}"
)

API_KEY = {current_api_key!r}

DOWNLOAD_DIR = "downloads"


async def download_song(link: str):

    os.makedirs(
        DOWNLOAD_DIR,
        exist_ok=True
    )

    file_name = "audio.mp3"

    file_path = os.path.join(
        DOWNLOAD_DIR,
        file_name
    )

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(
                f"{{API_URL}}/download",
                params={{
                    "url": link,
                    "type": "audio",
                    "api_key": API_KEY
                }},
                timeout=aiohttp.ClientTimeout(
                    total=300
                )
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

        return file_path

    except Exception:

        if os.path.exists(file_path):

            try:
                os.remove(file_path)
            except Exception:
                pass

        return None


async def download_video(link: str):

    os.makedirs(
        DOWNLOAD_DIR,
        exist_ok=True
    )

    file_name = "video.mp4"

    file_path = os.path.join(
        DOWNLOAD_DIR,
        file_name
    )

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(
                f"{{API_URL}}/download",
                params={{
                    "url": link,
                    "type": "video",
                    "api_key": API_KEY
                }},
                timeout=aiohttp.ClientTimeout(
                    total=600
                )
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

        return file_path

    except Exception:

        if os.path.exists(file_path):

            try:
                os.remove(file_path)
            except Exception:
                pass

        return None


class YouTubeAPI:

    async def video(
        self,
        link,
        *args,
        **kwargs
    ):

        file_path = await download_video(
            link
        )

        if file_path:
            return 1, file_path

        return 0, "Video download failed"


    async def download(
        self,
        link,
        mystic=None,
        video=None,
        *args,
        **kwargs
    ):

        if video:

            file_path = await download_video(
                link
            )

        else:

            file_path = await download_song(
                link
            )

        if file_path:

            return file_path, True

        return None, False


YouTube = YouTubeAPI()
'''

        file_bytes = io.BytesIO(
            youtube_code.encode("utf-8")
        )

        file_bytes.name = "Youtube.py"

        await client.send_document(
            chat_id=query.message.chat.id,
            document=file_bytes,
            caption=(
                "✅ **Youtube.py Ready**\n\n"
                "🔑 Your current ROYAL API key "
                "is already included.\n"
                "📅 Key validity: 30 days."
            )
        )


# =========================
# RUN
# =========================

if __name__ == "__main__":

    print(
        "👑 ROYAL API Bot Started"
    )

    app.run()
