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

app = FastAPI(title="Royal Fast Audio API")
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "/tmp/royal_downloads"))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Cookies are intentionally NOT used.

def delete_file(path: str):
    try:
        p = Path(path)
        if p.exists():
            p.unlink()
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

@app.on_event("startup")
async def startup():
    await database.init_db()

@app.get("/")
async def root():
    return {"name": "Royal Fast Audio API", "status": "online", "docs": "/docs", "health": "/health", "audio": "/audio"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/info")
async def info():
    return {"name": "Royal Fast Audio API", "cookies_required": False, "audio_endpoint": "/audio"}

async def make_audio(url: str, api_key: str, background_tasks: BackgroundTasks):
    is_valid, msg = await database.verify_key(api_key)
    if not is_valid:
        raise HTTPException(status_code=403, detail=msg)
    if not valid_youtube_url(url):
        raise HTTPException(status_code=400, detail="Please provide a valid YouTube URL")

    user_id = await database.get_user_id_by_key(api_key)
    if user_id is not None:
        usage = await database.get_usage(user_id)
        if usage["requests"] >= database.DAILY_LIMIT:
            raise HTTPException(status_code=429, detail="Daily API limit reached")

    job_id = uuid.uuid4().hex
    output_base = DOWNLOAD_DIR / job_id
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "outtmpl": str(output_base) + ".%(ext)s",
        "format": "bestaudio/best",
        "retries": 2,
        "fragment_retries": 2,
        "socket_timeout": 30,
        "concurrent_fragment_downloads": 4,
        "extractor_args": {"youtube": {"player_client": ["android_vr", "web"]}},
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    started = time.perf_counter()
    try:
        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        await asyncio.to_thread(extract)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio extraction failed: {e}")

    elapsed = max(time.perf_counter() - started, 0.001)
    output_file = DOWNLOAD_DIR / f"{job_id}.mp3"
    if not output_file.exists():
        output_file = find_output_file(output_base)
    if not output_file:
        raise HTTPException(status_code=500, detail="Audio created but output file was not found.")

    if user_id is not None:
        await database.add_usage(user_id, "request")
        await database.add_usage(user_id, "audio")

    size_bytes = output_file.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    background_tasks.add_task(delete_file, str(output_file))

    return FileResponse(
        path=str(output_file),
        media_type="audio/mpeg",
        filename=output_file.name,
        headers={
            "Cache-Control": "no-store",
            "X-File-Size-Bytes": str(size_bytes),
            "X-File-Size-MB": f"{size_mb:.2f}",
            "X-Processing-Time": f"{elapsed:.2f}s",
            "X-Media-Type": "audio",
        },
    )

@app.get("/audio")
async def audio(url: str, api_key: str, background_tasks: BackgroundTasks):
    return await make_audio(url, api_key, background_tasks)

@app.get("/api/audio")
async def api_audio(url: str, api_key: str, background_tasks: BackgroundTasks):
    return await make_audio(url, api_key, background_tasks)

# Backward-compatible endpoint: audio only.
@app.get("/download")
async def download_media(url: str, type: str, api_key: str, background_tasks: BackgroundTasks):
    if type != "audio":
        raise HTTPException(status_code=400, detail="This cookies-free API currently supports type=audio only")
    return await make_audio(url, api_key, background_tasks)
