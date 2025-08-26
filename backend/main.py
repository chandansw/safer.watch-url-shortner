from fastapi import FastAPI, HTTPException, Request, Depends, APIRouter
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel
import sqlite3
import string
import random
import time
import os
from starlette.middleware.cors import CORSMiddleware


app = FastAPI()
api_router = APIRouter()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "./urls.db"
ID_LENGTH = 9
ALPHABET = string.ascii_lowercase + string.digits
RATE_LIMIT_SECONDS = 30  # One request per 30 seconds per IP
BASE_URL = os.getenv("BASE_URL", "https://safer.watch")

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS urls (
        id TEXT PRIMARY KEY,
        original_url TEXT NOT NULL,
        created_at REAL NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS ratelimit (
        ip TEXT PRIMARY KEY,
        last_request REAL NOT NULL
    )''')
    conn.commit()
    conn.close()

init_db()

# --- Models ---
class URLRequest(BaseModel):
    url: str

class URLResponse(BaseModel):
    short_url: str

# --- Helper Functions ---
def generate_id():
    return ''.join(random.choices(ALPHABET, k=ID_LENGTH))

def get_client_ip(request: Request):
    return request.client.host

# --- Rate Limiting ---
def check_rate_limit(ip: str):
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
        c.execute("INSERT INTO ratelimit (ip, last_request) VALUES (?, ?)", (ip, now))
    conn.commit()
    conn.close()
    return True

# --- API Endpoints ---

@api_router.post("/shorten", response_model=URLResponse)
def shorten_url(req: URLRequest, request: Request):
    ip = get_client_ip(request)
    if not check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait.")
    # Generate unique ID
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    while True:
        short_id = generate_id()
        c.execute("SELECT 1 FROM urls WHERE id=?", (short_id,))
        if not c.fetchone():
            break
    c.execute("INSERT INTO urls (id, original_url, created_at) VALUES (?, ?, ?)", (short_id, req.url, time.time()))
    conn.commit()
    conn.close()
    return {"short_url": f"{BASE_URL}/{short_id}"}

@app.get("/api/{short_id}")
def api_redirect_url(short_id: str):
    # Optionally, you can provide an API endpoint for redirection info
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT original_url FROM urls WHERE id=?", (short_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"original_url": row[0]}
    raise HTTPException(status_code=404, detail="URL not found.")


# Serve React app at /url-shortner and all subpaths
from fastapi.staticfiles import StaticFiles
import pathlib
from fastapi import Request as FastAPIRequest
static_dir = pathlib.Path(__file__).parent / "static"
app.mount("/url-shortner", StaticFiles(directory=static_dir, html=True), name="url-shortner")

# Serve index.html for all /url-shortner* routes that are not static assets
@app.get("/url-shortner/{full_path:path}")
async def spa_catchall(full_path: str):
    index_path = static_dir / "index.html"
    return FileResponse(index_path)

# Mount API router under /api
app.include_router(api_router, prefix="/api")

# Catch-all for redirection (must be last)
@app.get("/{short_id}")
def redirect_url(short_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT original_url FROM urls WHERE id=?", (short_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return RedirectResponse(row[0])
    raise HTTPException(status_code=404, detail="URL not found.")
