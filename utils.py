import time
import json
import os

METRICS_FILE = "metrics.json"

def sanitize_wallet_input(wallet):
    # Basic XRPL wallet input sanitization (case sensitive!)
    wallet = wallet.strip()  # HANYA buang whitespace, jangan tukar case!
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
        "wallet": wallet,
        "score": score,
        "duration": 0.2 # stub duration
    }
    metrics.append(entry)
    metrics = metrics[-50:] # keep last 50
    with open(METRICS_FILE, "w") as f:
        json.dump(metrics, f)

def get_metrics():
    if os.path.exists(METRICS_FILE):
        with open(METRICS_FILE, "r") as f:
            metrics = json.load(f)
    else:
        metrics = []
    total = len(metrics)
    avg_time = sum(m["duration"] for m in metrics) / total if total > 0 else 0
    last_5 = metrics[-5:]
    return {
        "total_validations": total,
        "average_response_time": avg_time,
        "last_5_wallets": last_5
    }

def log_error(msg):
    print(f"[PX-ERROR] {msg}")
