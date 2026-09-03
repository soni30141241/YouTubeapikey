import os
import io
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

import database


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

ROYAL_API_URL = os.environ.get(
    "ROYAL_API_URL",
    "https://youtubeapikey-production-701a.up.railway.app"
).rstrip("/")

ROYAL_API_KEY = os.environ.get(
    "ROYAL_API_KEY",
    ""
)


# =========================================================
# TELEGRAM CLIENT
# =========================================================

app = Client(
    "ROYALKeyBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# =========================================================
# MAIN MENU
# =========================================================

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


# =========================================================
# /START
# =========================================================

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


# =========================================================
# API KEY PAGE
# =========================================================

async def render_key_page(query, user_id):

    api_key, expiry_date, _ = await database.get_or_create_key(
        user_id
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


# =========================================================
# CALLBACKS
# =========================================================

@app.on_callback_query()
async def on_callback(client, query):

    user_id = query.from_user.id
    data = query.data

    # -----------------------------------------------------
    # MAIN MENU
    # -----------------------------------------------------

    if data == "main_menu":

        text = (
            f"👋 **Welcome {query.from_user.mention}!**\n\n"
            "**Main Menu**"
        )

        await query.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard()
        )

        await query.answer()


    # -----------------------------------------------------
    # VIEW KEY
    # -----------------------------------------------------

    elif data == "view_key":

        await query.answer()

        await render_key_page(
            query,
            user_id
        )


    # -----------------------------------------------------
    # API DOCS
    # -----------------------------------------------------

    elif data == "api_docs":

        text = (
            "**📚 Royal Fast API Documentation**\n\n"

            "**Base URL:**\n"
            f"`{ROYAL_API_URL}`\n\n"

            "**Download Endpoint:**\n"
            f"`{ROYAL_API_URL}/download`\n\n"

            "**Method:** `GET`\n\n"

            "**Parameters:**\n"
            "• `url` — YouTube URL\n"
            "• `type` — `audio` or `video`\n"
            "• `api_key` — Your API key\n\n"

            "**Example:**\n"
            f"`{ROYAL_API_URL}/download?url=YOUTUBE_URL&type=audio&api_key=YOUR_KEY`\n\n"

            "👇 Download the ready-to-use Python client."
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
                    "🌐 Open API Docs",
                    url=f"{ROYAL_API_URL}/docs"
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

        await query.answer()


    # -----------------------------------------------------
    # RENEW / REVOKE
    # -----------------------------------------------------

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
                f"⚠️ आपकी Key अभी वैलिड है!\n"
                f"नई Key {days_left} दिन बाद ही जनरेट की जा सकती है।",
                show_alert=True
            )

        else:

            await query.answer(
                "✅ आपकी पुरानी Key एक्सपायर हो गई थी। "
                "नई Key जनरेट कर दी गई है!",
                show_alert=True
            )

            await render_key_page(
                query,
                user_id
            )


    # -----------------------------------------------------
    # SEND YOUTUBE.PY
    # -----------------------------------------------------

    elif data == "dl_file":

        await query.answer(
            "Generating Youtube.py...",
            show_alert=False
        )

        youtube_code = r'''import os
import re
import aiohttp
import yt_dlp

from typing import Union

from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

from youtubesearchpython import VideosSearch, Playlist


# =========================================================
# API SETTINGS
# =========================================================

API_URL = os.environ.get(
    "ROYAL_API_URL",
    "https://youtubeapikey-production-701a.up.railway.app"
).rstrip("/")

API_KEY = os.environ.get(
    "ROYAL_API_KEY",
    "YOUR_API_KEY_HERE"
)

DOWNLOAD_DIR = "downloads"


# =========================================================
# HELPERS
# =========================================================

def time_to_seconds(time):

    stringt = str(time)

    return sum(
        int(x) * 60 ** i
        for i, x in enumerate(
            reversed(stringt.split(":"))
        )
    )


def youtube_full_url(link):

    link = str(link).strip()

    if "youtube.com/" in link:
        return link

    if "youtu.be/" in link:
        return link

    return (
        "https://www.youtube.com/watch?v="
        + link
    )


def get_video_id(link):

    link = str(link).strip()

    if "youtu.be/" in link:

        video_id = (
            link.split("youtu.be/")[1]
            .split("?")[0]
            .split("&")[0]
            .split("/")[0]
        )

        return video_id

    if "v=" in link:

        return (
            link.split("v=")[1]
            .split("&")[0]
            .split("#")[0]
        )

    return link


# =========================================================
# AUDIO DOWNLOAD
# =========================================================

async def download_song(link: str) -> Union[str, None]:

    full_url = youtube_full_url(link)

    video_id = get_video_id(full_url)

    if not video_id or len(video_id) < 3:
        return None

    os.makedirs(
        DOWNLOAD_DIR,
        exist_ok=True
    )

    file_path = os.path.join(
        DOWNLOAD_DIR,
        f"{video_id}.mp3"
    )

    if (
        os.path.exists(file_path)
        and os.path.getsize(file_path) > 0
    ):
        return file_path

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(
                f"{API_URL}/download",
                params={
                    "url": full_url,
                    "type": "audio",
                    "api_key": API_KEY
                },
                timeout=aiohttp.ClientTimeout(
                    total=600
                )
            ) as resp:

                if resp.status != 200:
                    return None

                with open(
                    file_path,
                    "wb"
                ) as f:

                    async for chunk in resp.content.iter_chunked(
                        131072
                    ):
                        f.write(chunk)

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


# =========================================================
# VIDEO DOWNLOAD
# =========================================================

async def download_video(link: str) -> Union[str, None]:

    full_url = youtube_full_url(link)

    video_id = get_video_id(full_url)

    if not video_id or len(video_id) < 3:
        return None

    os.makedirs(
        DOWNLOAD_DIR,
        exist_ok=True
    )

    file_path = os.path.join(
        DOWNLOAD_DIR,
        f"{video_id}.mp4"
    )

    if (
        os.path.exists(file_path)
        and os.path.getsize(file_path) > 0
    ):
        return file_path

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(
                f"{API_URL}/download",
                params={
                    "url": full_url,
                    "type": "video",
                    "api_key": API_KEY
                },
                timeout=aiohttp.ClientTimeout(
                    total=900
                )
            ) as resp:

                if resp.status != 200:
                    return None

                with open(
                    file_path,
                    "wb"
                ) as f:

                    async for chunk in resp.content.iter_chunked(
                        131072
                    ):
                        f.write(chunk)

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


# =========================================================
# YOUTUBE API CLASS
# =========================================================

class YouTubeAPI:

    def __init__(self):

        self.base = (
            "https://www.youtube.com/watch?v="
        )

        self.regex = (
            r"(?:youtube\.com|youtu\.be)"
        )

        self.status = (
            "https://www.youtube.com/oembed?url="
        )

        self.listbase = (
            "https://youtube.com/playlist?list="
        )

        self.reg = re.compile(
            r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
        )


    # -----------------------------------------------------
    # EXISTS
    # -----------------------------------------------------

    async def exists(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + link

        return bool(
            re.search(
                self.regex,
                link
            )
        )


    # -----------------------------------------------------
    # GET URL FROM MESSAGE
    # -----------------------------------------------------

    async def url(
        self,
        message_1: Message
    ) -> Union[str, None]:

        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(
                message_1.reply_to_message
            )

        for message in messages:

            if message.entities:

                for entity in message.entities:

                    if (
                        entity.type
                        == MessageEntityType.URL
                    ):

                        text = (
                            message.text
                            or message.caption
                            or ""
                        )

                        return text[
                            entity.offset:
                            entity.offset
                            + entity.length
                        ]

            elif message.caption_entities:

                for entity in message.caption_entities:

                    if (
                        entity.type
                        == MessageEntityType.TEXT_LINK
                    ):

                        return entity.url

        return None


    # -----------------------------------------------------
    # DETAILS
    # -----------------------------------------------------

    async def details(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(
            link,
            limit=1
        )

        data = await results.next()

        for result in data["result"]:

            title = result["title"]
            duration_min = result["duration"]

            thumbnail = (
                result["thumbnails"][0]["url"]
                .split("?")[0]
            )

            vidid = result["id"]

            duration_sec = (
                int(time_to_seconds(duration_min))
                if duration_min
                else 0
            )

            return (
                title,
                duration_min,
                duration_sec,
                thumbnail,
                vidid
            )

        return None


    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    async def title(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(
            link,
            limit=1
        )

        data = await results.next()

        for result in data["result"]:
            return result["title"]

        return None


    # -----------------------------------------------------
    # DURATION
    # -----------------------------------------------------

    async def duration(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(
            link,
            limit=1
        )

        data = await results.next()

        for result in data["result"]:
            return result["duration"]

        return None


    # -----------------------------------------------------
    # THUMBNAIL
    # -----------------------------------------------------

    async def thumbnail(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(
            link,
            limit=1
        )

        data = await results.next()

        for result in data["result"]:

            return (
                result["thumbnails"][0]["url"]
                .split("?")[0]
            )

        return None


    # -----------------------------------------------------
    # VIDEO
    # -----------------------------------------------------

    async def video(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + link

        try:

            downloaded_file = (
                await download_video(link)
            )

            if downloaded_file:
                return 1, downloaded_file

            return 0, "Video download failed"

        except Exception as e:

            return 0, f"Video download error: {e}"


    # -----------------------------------------------------
    # PLAYLIST
    # -----------------------------------------------------

    async def playlist(
        self,
        link,
        limit,
        user_id,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.listbase + link

        if "&" in link:
            link = link.split("&")[0]

        try:

            plist = await Playlist.get(link)

        except Exception:

            return []

        videos = plist.get("videos") or []

        ids = []

        for data in videos[:limit]:

            if not data:
                continue

            vid = data.get("id")

            if not vid:
                continue

            ids.append(vid)

        return ids


    # -----------------------------------------------------
    # TRACK
    # -----------------------------------------------------

    async def track(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(
            link,
            limit=1
        )

        data = await results.next()

        for result in data["result"]:

            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]

            thumbnail = (
                result["thumbnails"][0]["url"]
                .split("?")[0]
            )

            track_details = {
                "title": title,
                "link": yturl,
                "vidid": vidid,
                "duration_min": duration_min,
                "thumb": thumbnail,
            }

            return track_details, vidid

        return None, None


    # -----------------------------------------------------
    # FORMATS
    # -----------------------------------------------------

    async def formats(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        ytdl_opts = {
            "quiet": True
        }

        ydl = yt_dlp.YoutubeDL(
            ytdl_opts
        )

        with ydl:

            formats_available = []

            r = ydl.extract_info(
                link,
                download=False
            )

            for fmt in r["formats"]:

                try:

                    if (
                        "dash"
                        not in str(
                            fmt["format"]
                        ).lower()
                    ):

                        formats_available.append({
                            "format": fmt["format"],
                            "filesize": fmt.get("filesize"),
                            "format_id": fmt["format_id"],
                            "ext": fmt["ext"],
                            "format_note": fmt.get("format_note"),
                            "yturl": link,
                        })

                except Exception:
                    continue

        return formats_available, link


    # -----------------------------------------------------
    # SLIDER
    # -----------------------------------------------------

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        a = VideosSearch(
            link,
            limit=10
        )

        result = (
            await a.next()
        ).get("result")

        if not result:
            return None

        item = result[query_type]

        title = item["title"]
        duration_min = item["duration"]
        vidid = item["id"]

        thumbnail = (
            item["thumbnails"][0]["url"]
            .split("?")[0]
        )

        return (
            title,
            duration_min,
            thumbnail,
            vidid
        )


    # -----------------------------------------------------
    # DOWNLOAD
    # -----------------------------------------------------

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        try:

            if video:
                downloaded_file = (
                    await download_video(link)
                )
            else:
                downloaded_file = (
                    await download_song(link)
                )

            if downloaded_file:
                return downloaded_file, True

            return None, False

        except Exception:

            return None, False


# =========================================================
# GLOBAL YOUTUBE OBJECT
# =========================================================

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
                "✅ **Ready-to-use Youtube.py**\n\n"
                "API URL already configured.\n"
                "Set `ROYAL_API_KEY` in your bot/environment "
                "before using it."
            )
        )


# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":

    print(
        "ROYAL API Bot Started!"
    )

    print(
        f"API URL: {ROYAL_API_URL}"
    )

    app.run()
