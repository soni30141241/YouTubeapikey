import os
import glob
import time
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
import yt_dlp
import database

app = FastAPI(
    title="Royal Fast API",
    version="2.0.0"
)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def cleanup_file(file_path: str):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass


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
    try:
        result = database.verify_key(api_key)

        if not result:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )

        return {
            "status": "valid",
            "message": "API key is valid"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )


@app.get("/download")
async def download(
    url: str,
    type: str,
    api_key: str
):
    start_time = time.perf_counter()

    # -------------------------
    # API KEY CHECK
    # -------------------------
    try:
        valid = database.verify_key(api_key)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    # -------------------------
    # TYPE CHECK
    # -------------------------
    if type not in ["audio", "video"]:
        raise HTTPException(
            status_code=400,
            detail="type must be audio or video"
        )

    # -------------------------
    # UNIQUE FILE NAME
    # -------------------------
    file_id = str(uuid.uuid4())
    output_base = os.path.join(
        DOWNLOAD_DIR,
        file_id
    )

    # -------------------------
    # YT-DLP OPTIONS
    # -------------------------
    if type == "audio":

        output_template = output_base + ".%(ext)s"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,

            "format": "bestaudio/best",

            "outtmpl": output_template,

            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],

            "retries": 3,
            "fragment_retries": 3,
        }

    else:

        output_template = output_base + ".%(ext)s"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,

            "format": "best",

            "outtmpl": output_template,

            "retries": 3,
            "fragment_retries": 3,
        }

    # -------------------------
    # DOWNLOAD
    # -------------------------
    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    except Exception as e:

        # Delete partial files
        for file in glob.glob(output_base + "*"):
            cleanup_file(file)

        raise HTTPException(
            status_code=500,
            detail=f"Download failed: {str(e)}"
        )

    # -------------------------
    # FIND DOWNLOADED FILE
    # -------------------------
    possible_files = glob.glob(
        output_base + "*"
    )

    possible_files = [
        f for f in possible_files
        if not f.endswith(".part")
        and not f.endswith(".ytdl")
    ]

    if not possible_files:

        raise HTTPException(
            status_code=500,
            detail="Downloaded file was not found"
        )

    # Prefer final file
    file_path = max(
        possible_files,
        key=os.path.getsize
    )

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=500,
            detail="File does not exist"
        )

    # -------------------------
    # STATISTICS
    # -------------------------
    end_time = time.perf_counter()

    download_time = end_time - start_time

    file_size_bytes = os.path.getsize(file_path)

    file_size_mb = file_size_bytes / (
        1024 * 1024
    )

    if download_time > 0:
        speed_mbps = file_size_mb / download_time
    else:
        speed_mbps = 0

    # Round values
    download_time = round(
        download_time,
        2
    )

    file_size_mb = round(
        file_size_mb,
        2
    )

    speed_mbps = round(
        speed_mbps,
        2
    )

    # -------------------------
    # RESPONSE HEADERS
    # -------------------------
    headers = {
        "X-Download-Time": str(
            download_time
        ),

        "X-File-Size-MB": str(
            file_size_mb
        ),

        "X-Speed-MBps": str(
            speed_mbps
        ),

        "X-File-Size-Bytes": str(
            file_size_bytes
        ),

        "X-Download-Stats": (
            f"Time={download_time}s; "
            f"Size={file_size_mb}MB; "
            f"Speed={speed_mbps}MB/s"
        ),

        "Access-Control-Expose-Headers": (
            "X-Download-Time, "
            "X-File-Size-MB, "
            "X-Speed-MBps, "
            "X-File-Size-Bytes, "
            "X-Download-Stats"
        ),
    }

    # -------------------------
    # RETURN FILE
    # -------------------------
    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/octet-stream",
        headers=headers,
        background=BackgroundTask(
            cleanup_file,
            file_path
        )
        )
