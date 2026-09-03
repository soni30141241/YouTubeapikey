import os
import io
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

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


@app.on_message(
    filters.command("start") & filters.private
)
async def start_cmd(client, message):

    user_id = message.from_user.id

    await database.get_or_create_key(user_id)

    text = (
        f"👋 **Welcome "
        f"{message.from_user.mention}!**\n\n"
        "**Main Menu**"
    )

    await message.reply_text(
        text,
        reply_markup=get_main_menu_keyboard()
    )


async def render_key_page(query, user_id):

    api_key, expiry_date, _ = (
        await database.get_or_create_key(user_id)
    )

    now = datetime.now()

    days_left = max(
        (expiry_date - now).days,
        0
    )

    expiry_str = expiry_date.strftime(
        "%d %b %Y, %I:%M %p IST"
    )

    created_date = expiry_date - timedelta(days=30)

    created_str = created_date.strftime(
        "%d %b %Y, %I:%M %p IST"
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

    elif data == "view_key":

        await render_key_page(
            query,
            user_id
        )

    elif data == "api_docs":

        text = (
            "**📚 Royal Fast API Documentation**\n\n"

            "**Base URL:**\n"
            "`https://youtubeapikey-production-701a.up.railway.app`\n\n"

            "**Endpoint:**\n"
            "`GET /download`\n\n"

            "**Parameters:**\n"
            "`url` = YouTube URL\n"
            "`type` = audio / video\n"
            "`api_key` = Your API key\n\n"

            "**Example:**\n"
            "`GET /download?url=YOUTUBE_URL&type=audio&api_key=YOUR_KEY`"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🌐 Open API Docs",
                    url="https://youtubeapikey-production-701a.up.railway.app/docs"
                )
            ],
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
                "✅ नई API Key generate कर दी गई है!",
                show_alert=True
            )

            await render_key_page(
                query,
                user_id
            )

    elif data == "dl_file":

        await query.answer(
            "Generating Youtube.py...",
            show_alert=False
        )

        youtube_code = r'''import os
import aiohttp
import yt_dlp

from youtubesearchpython import VideosSearch, Playlist


API_URL = os.environ.get(
    "ROYAL_API_URL",
    "https://youtubeapikey-production-701a.up.railway.app"
).rstrip("/")

API_KEY = os.environ.get(
    "ROYAL_API_KEY",
    "YOUR_API_KEY_HERE"
)

DOWNLOAD_DIR = "downloads"


def youtube_full_url(link: str) -> str:

    link = str(link).strip()

    if "youtube.com/" in link or "youtu.be/" in link:
        return link

    return f"https://www.youtube.com/watch?v={link}"


def get_video_id(link: str) -> str:

    link = str(link).strip()

    if "youtu.be/" in link:
        return link.split("youtu.be/")[1].split("?")[0].split("&")[0]

    if "v=" in link:
        return link.split("v=")[1].split("&")[0]

    return link


async def api_download(
    link: str,
    media_type: str,
    timeout: int
):

    full_url = youtube_full_url(link)

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

    if (
        os.path.exists(file_path)
        and os.path.getsize(file_path) > 0
    ):
        return file_path

    try:

        timeout_config = aiohttp.ClientTimeout(
            total=timeout
        )

        async with aiohttp.ClientSession(
            timeout=timeout_config
        ) as session:

            async with session.get(
                f"{API_URL}/download",
                params={
                    "url": full_url,
                    "type": media_type,
                    "api_key": API_KEY
                }
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
        300
    )


async def download_video(link: str):

    return await api_download(
        link,
        "video",
        600
    )


class YouTubeAPI:

    def __init__(self):

        self.base = (
            "https://www.youtube.com/watch?v="
        )

        self.listbase = (
            "https://youtube.com/playlist?list="
        )


    async def exists(
        self,
        link: str,
        videoid=False
    ):

        if videoid:
            link = self.base + link

        return (
            "youtube.com" in link
            or "youtu.be" in link
        )


    async def details(
        self,
        link: str,
        videoid=False
    ):

        if videoid:
            link = self.base + link

        results = VideosSearch(
            link,
            limit=1
        )

        data = await results.next()

        result = data["result"][0]

        title = result["title"]

        duration = result.get(
            "duration"
        )

        thumbnail = result["thumbnails"][0]["url"]

        vidid = result["id"]

        return (
            title,
            duration,
            0,
            thumbnail,
            vidid
        )


    async def title(
        self,
        link: str,
        videoid=False
    ):

        if videoid:
            link = self.base + link

        results = VideosSearch(
            link,
            limit=1
        )

        data = await results.next()

        return data["result"][0]["title"]


    async def duration(
        self,
        link: str,
        videoid=False
    ):

        if videoid:
            link = self.base + link

        results = VideosSearch(
            link,
            limit=1
        )

        data = await results.next()

        return data["result"][0].get(
            "duration"
        )


    async def thumbnail(
        self,
        link: str,
        videoid=False
    ):

        if videoid:
            link = self.base + link

        results = VideosSearch(
            link,
            limit=1
        )

        data = await results.next()

        return data["result"][0]["thumbnails"][0]["url"]


    async def video(
        self,
        link: str,
        videoid=False
    ):

        if videoid:
            link = self.base + link

        file_path = await download_video(
            link
        )

        if file_path:
            return 1, file_path

        return 0, "Video download failed"


    async def playlist(
        self,
        link,
        limit,
        user_id,
        videoid=False
    ):

        if videoid:
            link = self.listbase + link

        try:

            playlist = await Playlist.get(
                link
            )

            videos = playlist.get(
                "videos",
                []
            )

            return [
                item["id"]
                for item in videos[:limit]
                if item.get("id")
            ]

        except Exception:

            return []


    async def track(
        self,
        link: str,
        videoid=False
    ):

        if videoid:
            link = self.base + link

        results = VideosSearch(
            link,
            limit=1
        )

        data = await results.next()

        result = data["result"][0]

        details = {
            "title": result["title"],
            "link": result["link"],
            "vidid": result["id"],
            "duration_min": result.get("duration"),
            "thumb": result["thumbnails"][0]["url"]
        }

        return details, result["id"]


    async def formats(
        self,
        link: str,
        videoid=False
    ):

        if videoid:
            link = self.base + link

        ydl_opts = {
            "quiet": True
        }

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            info = ydl.extract_info(
                link,
                download=False
            )

            formats = []

            for fmt in info.get(
                "formats",
                []
            ):

                formats.append({
                    "format": fmt.get("format"),
                    "filesize": fmt.get("filesize"),
                    "format_id": fmt.get("format_id"),
                    "ext": fmt.get("ext"),
                    "format_note": fmt.get("format_note"),
                    "yturl": link
                })

        return formats, link


    async def download(
        self,
        link,
        mystic,
        video=False,
        videoid=False,
        songaudio=False,
        songvideo=False,
        format_id=False,
        title=False
    ):

        if videoid:
            link = self.base + link

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
                "✅ **Corrected Youtube.py**\n\n"
                "Set `ROYAL_API_KEY` in your environment "
                "or replace `YOUR_API_KEY_HERE`."
            )
        )


if __name__ == "__main__":

    print(
        "ROYAL Key Bot starting..."
    )

    app.run()
