import os
import uuid
import asyncio

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
    if not database.verify_key(api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key"
        )

    return {
        "status": "success",
        "message": "API key is valid",
        "daily_limit": 3000
    }


def delete_file(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


@app.get("/download")
async def download(
    background_tasks: BackgroundTasks,
    url: str,
    type: str,
    api_key: str
):

    if not database.verify_key(api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key"
        )

    if type not in ["audio", "video"]:
        raise HTTPException(
            status_code=400,
            detail="type must be audio or video"
        )

    file_id = str(uuid.uuid4())

    if type == "audio":
        output_template = os.path.join(
            DOWNLOAD_DIR,
            f"{file_id}.%(ext)s"
        )

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
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

    else:
        output_template = os.path.join(
            DOWNLOAD_DIR,
            f"{file_id}.%(ext)s"
        )

        ydl_opts = {
            "format": "best",
            "outtmpl": output_template,
            "quiet": True,
            "noplaylist": True
        }

    try:
        def run_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        await asyncio.to_thread(run_download)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Download failed: {str(e)}"
        )

    if type == "audio":
        file_path = os.path.join(
            DOWNLOAD_DIR,
            f"{file_id}.mp3"
        )
        media_type = "audio/mpeg"
        filename = "royal_audio.mp3"

    else:
        possible_files = []

        for filename in os.listdir(DOWNLOAD_DIR):
            if filename.startswith(file_id + "."):
                possible_files.append(filename)

        if not possible_files:
            raise HTTPException(
                status_code=500,
                detail="Downloaded file not found"
            )

        file_path = os.path.join(
            DOWNLOAD_DIR,
            possible_files[0]
        )

        media_type = "video/mp4"
        filename = "royal_video.mp4"

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=500,
            detail="Downloaded file not found"
        )

    database.record_usage(api_key, type)

    background_tasks.add_task(
        delete_file,
        file_path
    )

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
        background=background_tasks
        )
