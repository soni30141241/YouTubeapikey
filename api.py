import os
import asyncio
import glob
import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

import yt_dlp
import database


app = FastAPI(
    title="Royal Fast API",
    version="1.0.0"
)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# =========================
# STARTUP
# =========================

@app.on_event("startup")
async def startup():
    await database.init_db()


# =========================
# DELETE FILE
# =========================

def delete_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# =========================
# HOME
# =========================

@app.get("/")
async def home():
    return {
        "status": "online",
        "message": "Royal Fast API is working!"
    }


# =========================
# HEALTH
# =========================

@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


# =========================
# INFO
# =========================

@app.get("/info")
async def info():
    return {
        "name": "Royal Fast API",
        "version": "1.0.0",
        "status": "online",
        "endpoints": [
            "/",
            "/health",
            "/info",
            "/download",
            "/docs"
        ]
    }


# =========================
# DOWNLOAD
# =========================

@app.get("/download")
async def download_media(
    url: str,
    type: str,
    api_key: str,
    background_tasks: BackgroundTasks
):

    # Check API key
    is_valid, msg = await database.verify_key(api_key)

    if not is_valid:
        raise HTTPException(
            status_code=403,
            detail=msg
        )

    # Check type
    if type not in ["video", "audio"]:
        raise HTTPException(
            status_code=400,
            detail="type must be 'video' or 'audio'"
        )

    # Unique file name
    file_id = uuid.uuid4().hex

    if type == "video":

        ydl_opts = {
            "format": "best",
            "outtmpl": f"{DOWNLOAD_DIR}/{file_id}.%(ext)s",
            "quiet": True,
            "noplaylist": True
        }

    else:

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{DOWNLOAD_DIR}/{file_id}.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192"
                }
            ]
        }

    def extract():

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            # FFmpeg may change the final extension (audio -> mp3).
            files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{file_id}.*"))
            files = [p for p in files if os.path.isfile(p)]
            if not files:
                return None

            if type == "audio":
                mp3 = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp3")
                if os.path.isfile(mp3):
                    return mp3

            return files[0]

    try:

        filename = await asyncio.to_thread(extract)

        # Make sure file exists
        if not filename or not os.path.isfile(filename):
            raise Exception("Downloaded file not found")

        # Delete after response
        background_tasks.add_task(
            delete_file,
            filename
        )

        return FileResponse(
            path=filename,
            media_type="application/octet-stream",
            filename=os.path.basename(filename)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
            )
