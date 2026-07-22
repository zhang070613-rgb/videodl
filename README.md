# VideoDL - Free Video Downloader

Paste link -> one click -> save to Photos. Supports 1752+ platforms via yt-dlp.

## Architecture

```
Frontend (Cloudflare Pages, free)     Backend (Render, free)
┌──────────────────────────┐         ┌─────────────────────────┐
│  index.html              │  HTTP   │  FastAPI + yt-dlp       │
│  PWA + simple UI         │ ◄─────► │  /api/extract?url=...   │
│  navigator.share()       │         │  /api/health            │
│  (save to Photos on iOS) │         │  1752+ extractors       │
└──────────────────────────┘         └─────────────────────────┘
                                              ▲
                                     cron-job.org pings every 10 min
                                     (prevents Render 15-min sleep)
```

## Deploy

### 1. Backend (Render)

1. Go to https://dashboard.render.com
2. New Web Service -> Connect this repo
3. Root Directory: `backend`
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
6. Choose Free plan -> Deploy
7. Note your URL: `https://videodl-api.onrender.com`

### 2. Keepalive (cron-job.org)

1. Go to https://cron-job.org
2. Create cron job: `https://your-app.onrender.com/api/health`
3. Interval: Every 10 minutes
4. This prevents the free Render service from sleeping

### 3. Frontend (Cloudflare Pages)

1. Go to https://dash.cloudflare.com
2. Pages -> Upload assets -> Select `frontend/` folder
3. Or: Connect git repo, set Root Directory: `frontend`
4. Update `API_BASE` in index.html to your Render URL

### 4. Update API_BASE

Edit `frontend/index.html`, change line:
```js
var API_BASE='https://YOUR-APP.onrender.com';
```

## Test Locally

```bash
cd backend
pip install -r requirements.txt
python app.py
# Open http://localhost:8000/api/health
# Test: http://localhost:8000/api/extract?url=YOUR_VIDEO_URL
```

## Tech Stack

- Backend: Python 3.12 + FastAPI + yt-dlp
- Frontend: Vanilla HTML/CSS/JS + PWA
- Hosting: Render (API) + Cloudflare Pages (static) = $0/month

## iOS Save to Photos

On iPhone Safari:
1. Paste video link
2. Tap "Parse" -> video preview appears
3. Tap "Save to Photos" -> iOS share sheet opens
4. Tap "Save Video" -> saved to Camera Roll

Uses `navigator.share({files: [...]})` API (iOS 14+).

## Supported Platforms

1752+ extractors from yt-dlp:
Douyin, Bilibili, YouTube, Xiaohongshu, Kuaishou, Weibo,
Twitter/X, Instagram, Facebook, Reddit, Vimeo, and many more.

## License

MIT - for personal learning use only.
