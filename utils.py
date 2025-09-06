# utils.py
from __future__ import annotations
import os, json, time, tempfile

METRICS_FILE = "metrics.json"
START_TIME_FILE = "uptime.txt"

# ---------- helpers ----------
def _atomic_write(path: str, data: dict) -> None:
    fd, tmp = tempfile.mkstemp(prefix="pxm_", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def _load_metrics() -> dict:
    if not os.path.exists(METRICS_FILE):
        return {"total": 0, "sum_duration": 0.0, "recent": []}
    with open(METRICS_FILE, "r") as f:
        raw = json.load(f)

    if isinstance(raw, dict) and "total" in raw:
        raw.setdefault("sum_duration", 0.0)
        raw.setdefault("recent", [])
        return raw

    if isinstance(raw, list):
        total = len(raw)
        sum_dur = sum(float(e.get("duration", 0.0)) for e in raw)
        recent = [
            {
                "ts": float(e.get("timestamp", time.time())),
                "score": int((e.get("score", 0) if not isinstance(e.get("score"), dict)
                              else e["score"].get("score", 0)) or 0),
                "dur": float(e.get("duration", 0.0)),
            }
            for e in raw[-100:]
        ]
        return {"total": int(total), "sum_duration": float(sum_dur), "recent": recent}

    return {"total": 0, "sum_duration": 0.0, "recent": []}

# ---------- public ----------
def sanitize_wallet_input(wallet: str | None):
    if not wallet:
        return None
    wallet = wallet.strip()
    # XRPL classic ~25–35 chars, starts with 'r'
    return wallet if wallet.startswith("r") and 25 <= len(wallet) <= 35 else None

def rotate_fallback(index, total):
    return (index + 1) % max(1, int(total or 1))

def log_event(wallet, score, duration_ms: float = 200.0):
    m = _load_metrics()
    m["total"] = int(m.get("total", 0)) + 1
    m["sum_duration"] = float(m.get("sum_duration", 0.0)) + float(duration_ms or 0.0)
    s = score.get("score") if isinstance(score, dict) else score
    m["recent"] = (m.get("recent", []) + [{
        "ts": time.time(),
        "score": int(s or 0),
        "dur": float(duration_ms or 0.0),
    }])[-100:]
    _atomic_write(METRICS_FILE, m)

def _get_uptime_sec() -> int:
    if os.path.exists(START_TIME_FILE):
        try:
            with open(START_TIME_FILE, "r") as f:
                start = float(f.read().strip())
        except Exception:
            start = time.time()
    else:
        start = time.time()
        with open(START_TIME_FILE, "w") as f:
            f.write(str(start))
    return int(time.time() - start)

def get_metrics():
    m = _load_metrics()
    total = int(m.get("total", 0))
    avg_ms = (float(m.get("sum_duration", 0.0)) / total) if total else 0.0
    last5 = [{"ts": e.get("ts"), "score": e.get("score")} for e in m.get("recent", [])[-5:]]
    return {
        "status": "online",
        "uptime_sec": _get_uptime_sec(),
        "total": total,
        "avg_response_ms": avg_ms,
        "last": last5,
        # backward-compat keys:
        "total_validations": total,
        "average_response_time": avg_ms / 1000.0,
    }

def log_error(msg):
    print(f"[PX-ERROR] {msg}")
