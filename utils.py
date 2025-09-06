import time
import json
import os

METRICS_FILE = "metrics.json"
START_TIME_FILE = "uptime.txt"

def sanitize_wallet_input(wallet):
    wallet = wallet.strip()
    if len(wallet) == 34 and wallet.startswith("r"):
        return wallet
    return None

def rotate_fallback(index, total):
    return (index + 1) % total

def log_event(wallet, score):
    metrics = []
    if os.path.exists(METRICS_FILE):
        with open(METRICS_FILE, "r") as f:
            try:
                metrics = json.load(f)
            except Exception:
                metrics = []
    entry = {
        "timestamp": time.time(),
        "score": score,
        "duration": 0.2 # stub duration
    }
    metrics.append(entry)
    metrics = metrics[-50:] # keep last 50
    with open(METRICS_FILE, "w") as f:
        json.dump(metrics, f)

def get_metrics():
    health_status = "online"
    uptime = 0
    # Track uptime
    if os.path.exists(START_TIME_FILE):
        with open(START_TIME_FILE, "r") as f:
            try:
                start_time = float(f.read().strip())
                uptime = int(time.time() - start_time)
            except Exception:
                uptime = 0
    else:
        # Save start time on first run
        with open(START_TIME_FILE, "w") as f:
            f.write(str(time.time()))
        uptime = 0

    if os.path.exists(METRICS_FILE):
        with open(METRICS_FILE, "r") as f:
            metrics = json.load(f)
    else:
        metrics = []
    total = len(metrics)
    avg_time = sum(m["duration"] for m in metrics) / total if total > 0 else 0

    # No wallet address exposed
    return {
        "status": health_status,
        "uptime_sec": uptime,
        "total_validations": total,
        "average_response_time": avg_time
    }

def log_error(msg):
    print(f"[PX-ERROR] {msg}")
