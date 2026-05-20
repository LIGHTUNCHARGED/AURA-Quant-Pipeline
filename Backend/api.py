from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import time
from datetime import datetime

from main import run_quant_pipeline
from data_loader import fetch_tickers_from_txt

app = FastAPI(title="Quant Strategy API")

# 1Hr waiting time before next scan
CACHE_TTL_SECONDS = 3600

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://aura-quant-pipeline-1.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to check the file's timestamp
def get_cache_timestamp():
    file_path = "latest_scan.json"
    if os.path.exists(file_path):
        mtime = os.path.getmtime(file_path)
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %I:%M:%S %p')
    return "No previous scan found"

SCAN_STATUS = {
    "is_scanning": False,
    "message": "Ready",
    "last_updated": "Never"
}

print("Loading NSE universe from text file...")
TARGET_UNIVERSE = fetch_tickers_from_txt('Symbols_NSE.txt')
print(f"Loaded {len(TARGET_UNIVERSE)} stocks.")


def background_scan_task():
    global SCAN_STATUS
    SCAN_STATUS["is_scanning"] = True
    SCAN_STATUS["message"] = f"Crunching {len(TARGET_UNIVERSE)} stocks. This takes time..."

    try:
        run_quant_pipeline(TARGET_UNIVERSE)
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

    file_path = "latest_scan.json"
    if os.path.exists(file_path):
        file_age = time.time() - os.path.getmtime(file_path)

        if file_age < CACHE_TTL_SECONDS:
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
    if not os.path.exists("latest_scan.json"):
        return {"status": "error", "message": "No scan data found."}

    with open("latest_scan.json", "r") as file:
        json_data = json.load(file)

    if len(json_data) == 0:
        return {"status": "no_trades", "data": []}

    return {"status": "success", "data": json_data}
