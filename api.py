import os
import asyncio
import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

import yt_dlp
import database


app = FastAPI(title="Royal Fast API", version="1.0.0")

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
# HEALTH CHECK
# =========================

@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


# =========================
# API INFO
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
    # API key verify
    is_valid, msg = await database.verify_key(api_key)

    if not is_valid:
        raise HTTPException(
            status_code=403,
            detail=msg
        )

    # Type validation
    if type not in ("video", "audio"):
        raise HTTPException(
            status_code=400,
            detail="type must be 'video' or 'audio'"
        )

    # Unique filename
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
            "noplaylist": True
        }

    def extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    try:
        filename = await asyncio.to_thread(extract)

        if not os.path.exists(filename):
            raise Exception("Downloaded file not found")

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
