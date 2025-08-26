# main.py
from fastapi import FastAPI, HTTPException, Request, APIRouter
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
import sqlite3
import string
import random
import time
import os
import pathlib

# ------------------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------------------
app = FastAPI()
api = APIRouter()

# CORS (adjust allow_origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------
DB_PATH = "./urls.db"
ID_LENGTH = 9
ALPHABET = string.ascii_lowercase + string.digits
RATE_LIMIT_SECONDS = 30  # One request per 30 seconds per IP
BASE_URL = os.getenv("BASE_URL", "https://safer.watch")

# Static/SPA directory (must contain index.html and asset folders from your build)
static_dir = pathlib.Path(__file__).parent / "static"

# ------------------------------------------------------------------------------
# Database Setup
# ------------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS urls (
            id TEXT PRIMARY KEY,
            original_url TEXT NOT NULL,
            created_at REAL NOT NULL
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS ratelimit (
            ip TEXT PRIMARY KEY,
            last_request REAL NOT NULL
        )"""
    )
    conn.commit()
    conn.close()

init_db()

# ------------------------------------------------------------------------------
# Models
# ------------------------------------------------------------------------------
class URLRequest(BaseModel):
    url: str

class URLResponse(BaseModel):
    short_url: str

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def generate_id():
    return "".join(random.choices(ALPHABET, k=ID_LENGTH))

def get_client_ip(request: Request) -> str:
    # Prefer X-Forwarded-For if behind a proxy/CDN
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host

def check_rate_limit(ip: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT last_request FROM ratelimit WHERE ip=?", (ip,))
    row = c.fetchone()
    now = time.time()
    if row:
        last = row[0]
        if now - last < RATE_LIMIT_SECONDS:
            conn.close()
            return False
        c.execute("UPDATE ratelimit SET last_request=? WHERE ip=?", (now, ip))
    else:
        c.execute(
            "INSERT INTO ratelimit (ip, last_request) VALUES (?, ?)", (ip, now)
        )
    conn.commit()
    conn.close()
    return True

# ------------------------------------------------------------------------------
# API Endpoints (mounted under /api)
# ------------------------------------------------------------------------------
@api.post("/shorten", response_model=URLResponse)
def shorten_url(req: URLRequest, request: Request):
    ip = get_client_ip(request)
    if not check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait.")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Generate unique ID
    while True:
        short_id = generate_id()
        c.execute("SELECT 1 FROM urls WHERE id=?", (short_id,))
        if not c.fetchone():
            break

    c.execute(
        "INSERT INTO urls (id, original_url, created_at) VALUES (?, ?, ?)",
        (short_id, req.url, time.time()),
    )
    conn.commit()
    conn.close()

    return {"short_url": f"{BASE_URL}/{short_id}"}

@api.get("/lookup/{short_id}")
def api_lookup(short_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT original_url FROM urls WHERE id=?", (short_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"original_url": row[0]}
    raise HTTPException(status_code=404, detail="URL not found.")

app.include_router(api, prefix="/api")

# ------------------------------------------------------------------------------
# SPA at /url-shortner  (works for deep links like /url-shortner/.../*)
# ------------------------------------------------------------------------------
# Recommended: build your React/Vite app with base "/url-shortner/"
#   CRA: add "homepage": "/url-shortner" in package.json before build
#   Vite: set base: "/url-shortner/" in vite.config.js

# Serve static subfolders explicitly if you have them (adjust as needed):
# e.g., /url-shortner/static/* -> ./static/assets/*
if (static_dir / "static").exists():
    # Mount static inside the SPA subspace to avoid conflicts
    app.mount("/url-shortner/static", StaticFiles(directory=static_dir / "static"), name="spa-static")

# Serve static asset subfolders explicitly if you have them (adjust as needed):
# e.g., /url-shortner/assets/* -> ./static/assets/*
if (static_dir / "assets").exists():
    # Mount assets inside the SPA subspace to avoid conflicts
    app.mount("/url-shortner/assets", StaticFiles(directory=static_dir / "assets"), name="spa-assets")

# Fallback for ANY SPA route: always return index.html
@app.get("/url-shortner")
@app.get("/url-shortner/")
@app.get("/url-shortner/{path:path}")
async def spa_fallback(path: str = ""):
    index_path = static_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=500, detail="index.html not found in ./static")
    return FileResponse(index_path)

# (Optional) If you want to serve other shared static files (not under /url-shortner),
# you can mount them elsewhere, e.g.:
# app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ------------------------------------------------------------------------------
# Catch-all redirect for short IDs at root (must be last)
# ------------------------------------------------------------------------------
@app.get("/{short_id}")
def redirect_short_url(short_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT original_url FROM urls WHERE id=?", (short_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return RedirectResponse(url=row[0])
    raise HTTPException(status_code=404, detail="URL not found.")
