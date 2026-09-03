import os
import uuid
import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import yt_dlp


app = FastAPI(
    title="Royal Fast API",
    version="2.0.0"
)

# =========================
# CONFIG
# =========================

API_KEY = os.environ.get("ROYAL_API_KEY", "").strip()

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# CLEANUP
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
        "status": "healthy",
        "api_key_configured": bool(API_KEY)
    }


# =========================
# INFO
# =========================

@app.get("/info")
async def info(api_key: str):
    if not API_KEY or api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key"
        )

    return {
        "status": "success",
        "message": "API Key is valid"
    }


# =========================
# DOWNLOAD
# =========================

@app.get("/download")
async def download(
    background_tasks: BackgroundTasks,
    url: str,
    type: str,
    api_key: str
):

    # API KEY CHECK
    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="API Key is not configured on server"
        )

    if api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key"
        )

    # TYPE CHECK
    if type not in ["video", "audio"]:
        raise HTTPException(
            status_code=400,
            detail="Type must be video or audio"
        )

    # URL CHECK
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL"
        )

    file_id = str(uuid.uuid4())

    try:

        if type == "audio":

            output_template = str(
                DOWNLOAD_DIR / f"{file_id}.%(ext)s"
            )

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": output_template,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }

        else:

            output_template = str(
                DOWNLOAD_DIR / f"{file_id}.%(ext)s"
            )

            ydl_opts = {
                "format": "best",
                "outtmpl": output_template,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
            }

        # DOWNLOAD
        def run_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        await asyncio.to_thread(run_download)

        # FIND GENERATED FILE
        files = list(
            DOWNLOAD_DIR.glob(f"{file_id}.*")
        )

        if not files:
            raise Exception("Downloaded file not found")

        file_path = files[0]

        # DELETE AFTER RESPONSE
        background_tasks.add_task(
            delete_file,
            str(file_path)
        )

        if type == "audio":
            media_type = "audio/mpeg"
        else:
            media_type = "video/mp4"

        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=file_path.name
        )

    except Exception as e:

        # Cleanup on error
        for file in DOWNLOAD_DIR.glob(f"{file_id}.*"):
            delete_file(str(file))

        raise HTTPException(
            status_code=500,
            detail=f"Download failed: {str(e)}"
        )
