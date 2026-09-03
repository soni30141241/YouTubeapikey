import os
import asyncio
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import yt_dlp
import database

app = FastAPI(title="Royal Fast API")
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "/tmp/royal_downloads"))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
COOKIE_FILE = os.getenv("YOUTUBE_COOKIES_FILE", "/data/cookies.txt")

@app.on_event("startup")
async def startup():
    await database.init_db()

def delete_file(path: str):
    try:
        p = Path(path)
        if p.exists(): p.unlink()
    except Exception:
        pass

def valid_youtube_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
        return host in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtube-nocookie.com"}
    except Exception:
        return False

def find_output_file(prefix: Path):
    files = [p for p in DOWNLOAD_DIR.glob(f"{prefix.name}.*") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

@app.get("/")
async def root():
    return {"name": "Royal Fast API", "status": "online", "docs": "/docs", "health": "/health"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/info")
async def info():
    return {"name": "Royal Fast API", "youtube_cookies_configured": os.path.isfile(COOKIE_FILE)}

@app.get("/download")
async def download_media(url: str, type: str, api_key: str, background_tasks: BackgroundTasks):
    is_valid, msg = await database.verify_key(api_key)
    if not is_valid:
        raise HTTPException(status_code=403, detail=msg)
    if type not in {"audio", "video"}:
        raise HTTPException(status_code=400, detail="type must be audio or video")
    if not valid_youtube_url(url):
        raise HTTPException(status_code=400, detail="Please provide a valid YouTube URL")

    job_id = uuid.uuid4().hex
    output_base = DOWNLOAD_DIR / job_id
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "outtmpl": str(output_base) + ".%(ext)s",
        "retries": 2,
        "fragment_retries": 2,
        "socket_timeout": 30,
    }
    if os.path.isfile(COOKIE_FILE):
        ydl_opts["cookiefile"] = COOKIE_FILE

    if type == "audio":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
        })
    else:
        ydl_opts.update({"format": "bestvideo*+bestaudio/best", "merge_output_format": "mp4"})

    started = time.perf_counter()
    try:
        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        await asyncio.to_thread(extract)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ERROR: {e}")

    elapsed = max(time.perf_counter() - started, 0.001)
    output_file = find_output_file(output_base)
    if not output_file:
        raise HTTPException(status_code=500, detail="Download completed but output file was not found.")

    size_bytes = output_file.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    speed_mbps = size_mb / elapsed
    background_tasks.add_task(delete_file, str(output_file))

    return FileResponse(
        path=str(output_file),
        media_type="audio/mpeg" if type == "audio" else "video/mp4",
        filename=output_file.name,
        headers={
            "X-File-Size-Bytes": str(size_bytes),
            "X-File-Size-MB": f"{size_mb:.2f}",
            "X-Download-Time": f"{elapsed:.2f}s",
            "X-Speed-MBps": f"{speed_mbps:.2f}",
            "X-Media-Type": type,
        },
    )
    
