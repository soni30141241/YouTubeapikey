import os
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import yt_dlp
import database

app = FastAPI(title="Royal Fast API")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


@app.on_event("startup")
async def startup():
    await database.init_db()


def delete_file(path: str):
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


# Home route
@app.get("/")
async def home():
    return {
        "status": "online",
        "message": "Royal Fast API is working!"
    }


# Health check route
@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


# API documentation/info
@app.get("/info")
async def info():
    return {
        "name": "Royal Fast API",
        "status": "online",
        "endpoints": [
            "/",
            "/health",
            "/download"
        ]
    }


@app.get("/download")
async def download_media(
    url: str,
    type: str,
    api_key: str,
    background_tasks: BackgroundTasks
):
    # API Key check
    is_valid, msg = await database.verify_key(api_key)

    if not is_valid:
        raise HTTPException(
            status_code=403,
            detail=msg
        )

    video_id = (
        url.split("v=")[-1].split("&")[0]
        if "v=" in url
        else url
    )

    if type not in ["video", "audio"]:
        raise HTTPException(
            status_code=400,
            detail="type must be 'video' or 'audio'"
        )

    if type == "video":
        ydl_opts = {
            "format": "best",
            "outtmpl": f"{DOWNLOAD_DIR}/{video_id}.%(ext)s",
            "quiet": True
        }
    else:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{DOWNLOAD_DIR}/{video_id}.%(ext)s",
            "quiet": True
        }

    def extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    try:
        filename = await asyncio.to_thread(extract)

        if not os.path.exists(filename):
            raise HTTPException(
                status_code=500,
                detail="Downloaded file not found"
            )

        background_tasks.add_task(
            delete_file,
            filename
        )

        return FileResponse(
            filename,
            media_type="application/octet-stream",
            filename=os.path.basename(filename)
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
