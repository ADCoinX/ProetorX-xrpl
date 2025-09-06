# utils.py
from __future__ import annotations
import json, os, time, tempfile

METRICS_FILE = "metrics.json"
START_TIME_FILE = "uptime.txt"

# ---------- Helpers ----------
def _atomic_write(path: str, data: dict) -> None:
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="pxm_", suffix=".json")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

def _load_metrics() -> dict:
    """
    Return shape:
    {
      "total": int,                 # cumulative, unbounded
      "sum_duration": float,        # ms
      "recent": [ { "ts": float, "score": int, "dur": float } ]  # last N only
    }
    """
    if not os.path.exists(METRICS_FILE):
        return {"total": 0, "sum_duration": 0.0, "recent": []}

    with open(METRICS_FILE, "r") as f:
        raw = json.load(f)

    # v2 shape already dict
    if isinstance(raw, dict) and "total" in raw:
        raw.setdefault("sum_duration", 0.0)
        raw.setdefault("recent", [])
        return raw

    # v1 legacy (list of entries capped 50) -> migrate
    if isinstance(raw, list):
        total = len(raw)  # legacy only counted last 50; start from this baseline
        sum_dur = sum(float(e.get("duration", 0.0)) for e in raw)
        recent = [
            {"ts": float(e.get("timestamp", time.time())),
             "score": int(e.get("score", 0)),
             "dur": float(e.get("duration", 0.0))}
            for e in raw[-100:]
        ]
        return {"total": int(total), "sum_duration": float(sum_dur), "recent": recent}

    # fallback safe
    return {"total": 0, "sum_duration": 0.0, "recent": []}

# ---------- Public API ----------
def sanitize_wallet_input(wallet: str | None):
    if not wallet:
        return None
    wallet = wallet.strip()
    # XRPL classic addr biasanya 25–35 aksara, bermula 'r'
    if wallet.startswith("r") and 25 <= len(wallet) <= 35:
        return wallet
    return None

def rotate_fallback(index, total):
    return (index + 1) % max(1, total)

def log_event(wallet, score, duration_ms: float = 200.0):
    """
    Record one validation:
      - total (cumulative, unbounded)
      - sum_duration (ms)
      - keep only last 100 items in 'recent'
    NOTE: we intentionally DO NOT store wallet to avoid leaking addresses.
    """
    m = _load_metrics()
    m["total"] = int(m.get("total", 0)) + 1
    m["sum_duration"] = float(m.get("sum_duration", 0.0)) + float(duration_ms or 0.0)

    recent = m.get("recent", [])
    recent.append({
        "ts": time.time(),
        "score": (score.get("score") if isinstance(score, dict) else score) or 0,
        "dur": float(duration_ms or 0.0),
    })
    # keep window only; DOES NOT affect total
    m["recent"] = recent[-100:]

    _atomic_write(METRICS_FILE, m)

def get_metrics():
    """
    Returns stable snapshot for frontend.
    Shape:
      {
        "status": "online",
        "uptime_sec": int,
        "total": int,
        "avg_response_ms": float,
        "last": [ { "ts": float, "score": int } ]   # last up to 5
      }
    """
    # uptime
    if os.path.exists(START_TIME_FILE):
        try:
            with open(START_TIME_FILE, "r") as f:
                start_time = float(f.read().strip())
        except Exception:
            start_time = time.time()
    else:
        start_time = time.time()
        with open(START_TIME_FILE, "w") as f:
            f.write(str(start_time))

    m = _load_metrics()
    total = int(m.get("total", 0))
    sum_duration = float(m.get("sum_duration", 0.0))
    avg_ms = (sum_duration / total) if total else 0.0

    recent = m.get("recent", [])
    # Only expose last 5 items & no wallet address
    last5 = [{"ts": e.get("ts"), "score": e.get("score")} for e in recent[-5:]]

    return {
        "status": "online",
        "uptime_sec": int(time.time() - start_time),
        "total": total,
        "avg_response_ms": avg_ms,
        "last": last5
    }

def log_error(msg):
    print(f"[PX-ERROR] {msg}")
