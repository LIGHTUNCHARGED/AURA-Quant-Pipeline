from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import json
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from main import run_quant_pipeline
from data_loader import fetch_tickers_from_txt

app = FastAPI(title="Quant Strategy API")

# 1Hr waiting time before next scan
CACHE_TTL_SECONDS = 3600
LATEST_SCAN_PATH = BASE_DIR / "latest_scan.json"
SYMBOLS_PATH = BASE_DIR / "Symbols_NSE.txt"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://aura-quant-pipeline-1.onrender.com",
        "https://aura-quant-pipeline.onrender.com",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "null",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to check the file's timestamp
def get_cache_timestamp():
    if LATEST_SCAN_PATH.exists():
        mtime = LATEST_SCAN_PATH.stat().st_mtime
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %I:%M:%S %p')
    return "No previous scan found"


def cache_has_current_schema():
    if not LATEST_SCAN_PATH.exists():
        return False

    try:
        with open(LATEST_SCAN_PATH, "r", encoding="utf-8") as file:
            cached_rows = json.load(file)
    except (json.JSONDecodeError, OSError):
        return False

    if not cached_rows:
        return True

    return all("Win_Probability" in row for row in cached_rows)

SCAN_STATUS = {
    "is_scanning": False,
    "message": "Ready",
    "last_updated": "Never"
}

print("Loading NSE universe from text file...")
TARGET_UNIVERSE = fetch_tickers_from_txt(SYMBOLS_PATH)
print(f"Loaded {len(TARGET_UNIVERSE)} stocks.")


@app.get("/")
def read_root():
    return {"message": "Quant API is running", "docs": "/docs"}


@app.get("/api/health")
def health_check():
    return {"status": "ok", "universe_size": len(TARGET_UNIVERSE)}


def background_scan_task():
    global SCAN_STATUS
    SCAN_STATUS["is_scanning"] = True
    SCAN_STATUS["message"] = f"Crunching {len(TARGET_UNIVERSE)} stocks. This takes time..."

    try:
        run_quant_pipeline(TARGET_UNIVERSE, output_path=LATEST_SCAN_PATH)
        SCAN_STATUS["message"] = "Scan complete!"
    except Exception as e:
        print(f"Error during scan: {e}")
        SCAN_STATUS["message"] = "Scan failed due to an error."
    finally:
        SCAN_STATUS["is_scanning"] = False
        SCAN_STATUS["last_updated"] = get_cache_timestamp()


@app.post("/api/trigger-scan")
def trigger_scan(background_tasks: BackgroundTasks):
    global SCAN_STATUS

    if SCAN_STATUS["is_scanning"]:
        return {"status": "ignored", "message": "A scan is already running."}

    if LATEST_SCAN_PATH.exists():
        file_age = time.time() - LATEST_SCAN_PATH.stat().st_mtime

        if file_age < CACHE_TTL_SECONDS and cache_has_current_schema():
            minutes_old = int(file_age / 60)
            timestamp = get_cache_timestamp()
            SCAN_STATUS["last_updated"] = timestamp
            return {
                "status": "cached",
                "message": f"Using cached scan from {minutes_old} minutes ago.",
                "last_updated": timestamp
            }

    background_tasks.add_task(background_scan_task)
    return {"status": "started", "message": "Cache expired. Igniting Quant Engine."}


@app.get("/api/status")
def get_status():
    if not SCAN_STATUS["is_scanning"] and SCAN_STATUS["last_updated"] == "Never":
        SCAN_STATUS["last_updated"] = get_cache_timestamp()
    return SCAN_STATUS


@app.get("/api/screener")
def get_daily_allocations():
    if not LATEST_SCAN_PATH.exists():
        return {"status": "error", "message": "No scan data found."}

    with open(LATEST_SCAN_PATH, "r", encoding="utf-8") as file:
        json_data = json.load(file)

    if len(json_data) == 0:
        return {"status": "no_trades", "data": []}

    return {"status": "success", "data": json_data}
