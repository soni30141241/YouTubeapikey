import os
import glob
import time
import uuid
import asyncio

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

import yt_dlp
import database


app = FastAPI(
    title="ROYAL Fast API",
    version="1.0.0"
)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


@app.on_event("startup")
async def startup():
    await database.init_db()


def delete_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def find_downloaded_file(base_path: str):
    files = glob.glob(base_path + ".*")

    valid_files = [
        f for f in files
        if not f.endswith(".part")
        and not f.endswith(".ytdl")
    ]

    if not valid_files:
        return None

    return max(valid_files, key=os.path.getsize)


@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Royal Fast API is working!"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }


@app.get("/info")
async def info(api_key: str):
    is_valid, msg = await database.verify_key(api_key)

    if not is_valid:
        raise HTTPException(
            status_code=403,
            detail=msg
        )

    return {
        "status": "valid",
        "message": "API key is valid"
    }


@app.get("/download")
async def download_media(
    url: str,
    type: str,
    api_key: str,
    background_tasks: BackgroundTasks
):

    # =========================
    # API KEY CHECK
    # =========================

    is_valid, msg = await database.verify_key(api_key)

    if not is_valid:
        raise HTTPException(
            status_code=403,
            detail=msg
        )

    # =========================
    # TYPE CHECK
    # =========================

    if type not in ["audio", "video"]:
        raise HTTPException(
            status_code=400,
            detail="type must be audio or video"
        )

    # =========================
    # URL CHECK
    # =========================

    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid YouTube URL"
        )

    # =========================
    # UNIQUE FILE
    # =========================

    file_id = str(uuid.uuid4())

    base_path = os.path.join(
        DOWNLOAD_DIR,
        file_id
    )

    # =========================
    # YT-DLP OPTIONS
    # =========================

    if type == "audio":

        ydl_opts = {
            "format": "bestaudio/best",

            "outtmpl": base_path + ".%(ext)s",

            "quiet": True,
            "noplaylist": True,

            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

    else:

        ydl_opts = {
            "format": "best",

            "outtmpl": base_path + ".%(ext)s",

            "quiet": True,
            "noplaylist": True,
        }

    # =========================
    # OPTIONAL COOKIES
    # =========================

    cookie_file = os.getenv(
        "YOUTUBE_COOKIES_FILE",
        "/data/cookies.txt"
    )

    if os.path.exists(cookie_file):
        ydl_opts["cookiefile"] = cookie_file

    # =========================
    # DOWNLOAD
    # =========================

    start_time = time.perf_counter()

    def extract():

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    try:

        await asyncio.to_thread(extract)

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    # =========================
    # FIND FILE
    # =========================

    filename = find_downloaded_file(base_path)

    if not filename or not os.path.exists(filename):

        raise HTTPException(
            status_code=500,
            detail="Download completed but output file was not found"
        )

    # =========================
    # METRICS
    # =========================

    elapsed = time.perf_counter() - start_time

    file_size_bytes = os.path.getsize(filename)

    file_size_mb = file_size_bytes / (
        1024 * 1024
    )

    speed_mbps = (
        file_size_mb / elapsed
        if elapsed > 0
        else 0
    )

    # =========================
    # AUTO DELETE
    # =========================

    background_tasks.add_task(
        delete_file,
        filename
    )

    # =========================
    # RESPONSE
    # =========================

    headers = {
        "X-File-Size-Bytes": str(file_size_bytes),
        "X-File-Size-MB": f"{file_size_mb:.2f}",
        "X-Download-Time": f"{elapsed:.2f}",
        "X-Speed-MBps": f"{speed_mbps:.2f}",
        "X-Media-Type": type,
    }

    return FileResponse(
        filename,
        media_type="application/octet-stream",
        filename=os.path.basename(filename),
        headers=headers
        )
