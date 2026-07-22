"""
VideoDL Backend - FastAPI + yt-dlp
Free video link extractor supporting 1752+ platforms
"""
import os
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import yt_dlp

app = FastAPI(title="VideoDL API", version="1.0.0")

# CORS - allow all origins for PWA
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Health Check =====
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# ===== Extract Video Info =====
@app.get("/api/extract")
async def extract(
    url: str = Query(..., description="Video URL to extract"),
    cookie: str = Query("", description="Optional cookie string for platforms that need auth")
):
    if not url or not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "format": "bv*[height<=1080]+ba/b[height<=1080]/best",
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 3,
        "extractor_args": {
            "bilibili": {"prefer_mv": "0"},
            "douyin": {"download": "true"},
        },
    }

    # Build Netscape-format cookie file for platforms that need it (Douyin etc.)
    try:
        import tempfile, time
        cf = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        cf.write('# Netscape HTTP Cookie File\n')
        cf.write('# This is a generated cookie file for yt-dlp\n\n')
        now = int(time.time()) + 86400 * 365
        # Default cookies: ttwid (anonymous session, no login needed)
        cookies_to_add = {
            'ttwid': '1%7CgfmrD88EPY6sG76VvrD8963Yj_nOUsJbA12OsJHsPSs%7C1784731292%7C547f924aa63a8d7fc7cea65b80f5120f6f4484143869ad4dc2256424d1244644'
        }
        if cookie:
            for item in cookie.split('; '):
                if '=' in item:
                    k, v = item.split('=', 1)
                    cookies_to_add[k.strip()] = v.strip()
        for domain in ['.douyin.com', '.iesdouyin.com', 'www.douyin.com']:
            for k, v in cookies_to_add.items():
                cf.write(f'{domain}\tTRUE\t/\tFALSE\t{now}\t{k}\t{v}\n')
        cf.close()
        ydl_opts['cookiefile'] = cf.name
    except Exception:
        pass

    # Try primary extraction, fall back to generic format on failure
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: _extract(url, ydl_opts))
        return JSONResponse(content=info)
    except Exception as e1:
        # Fallback: try with 'best' format for platforms with unique format structures
        try:
            ydl_opts["format"] = "bv*+ba/b"
            info = await loop.run_in_executor(None, lambda: _extract(url, ydl_opts))
            return JSONResponse(content=info)
        except Exception as e2:
            error_msg = str(e2)
            if "cookies" in error_msg.lower() or "cookie" in error_msg.lower():
                raise HTTPException(
                    status_code=403,
                    detail=f"This platform requires cookies. Add ?cookie= to the URL. Original: {error_msg[:150]}"
                )
            elif "HTTP Error 403" in error_msg:
                raise HTTPException(status_code=403, detail="Platform requires authentication or blocks this server IP")
            elif "Unsupported URL" in error_msg:
                raise HTTPException(status_code=400, detail="Unsupported URL")
            elif "not available" in error_msg.lower() or "Video unavailable" in error_msg:
                raise HTTPException(status_code=404, detail="Video not found or removed")
            else:
                raise HTTPException(status_code=500, detail=f"Extraction failed: {error_msg[:200]}")

def _extract(url, opts):
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

        formats = []
        if "formats" in info:
            for f in info["formats"]:
                if not f.get("url"):
                    continue
                ext = f.get("ext", "")
                h = f.get("height") or 0
                # Accept any video format, prefer mp4 but include others
                if f.get("vcodec") and f.get("vcodec") != "none" and h <= 1080:
                    label = f"{f.get('width','?')}x{h}" if h > 0 else f.get("format_note","?")
                    formats.append({
                        "resolution": label,
                        "ext": ext,
                        "size_mb": round(f.get("filesize", 0) / 1024 / 1024, 1) if f.get("filesize") else None,
                        "url": f["url"],
                    })

        # If no video formats found, collect audio+video formats
        if not formats and "formats" in info:
            for f in info["formats"]:
                if not f.get("url"):
                    continue
                formats.append({
                    "resolution": f.get("format_note", "default"),
                    "ext": f.get("ext", "?"),
                    "size_mb": round(f.get("filesize", 0) / 1024 / 1024, 1) if f.get("filesize") else None,
                    "url": f["url"],
                })

        # If still nothing, use info-level url
        if not formats:
            best = info.get("url")
            if best:
                formats.append({
                    "resolution": f"{info.get('width','?')}x{info.get('height','?')}",
                    "ext": info.get("ext", "mp4"),
                    "size_mb": None,
                    "url": best,
                })

        # Deduplicate by url
        seen = set()
        unique_formats = []
        for f in formats:
            if f["url"] not in seen:
                seen.add(f["url"])
                unique_formats.append(f)

        return {
            "success": True,
            "title": info.get("title") or info.get("description") or "Unknown",
            "duration": info.get("duration", 0),
            "thumbnail": info.get("thumbnail", ""),
            "uploader": info.get("uploader", ""),
            "platform": info.get("extractor_key", "unknown"),
            "formats": unique_formats[:6],
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
