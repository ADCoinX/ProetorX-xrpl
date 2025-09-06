# utils.py
from __future__ import annotations
import os, json, time, tempfile, traceback

# === storage dir (Render-friendly) ===
DATA_DIR = os.getenv("PX_DATA_DIR", "/tmp/proetorx")
os.makedirs(DATA_DIR, exist_ok=True)
METRICS_FILE = os.path.join(DATA_DIR, "metrics.json")
START_TIME_FILE = os.path.join(DATA_DIR, "uptime.txt")

def _atomic_write(path: str, data: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=DATA_DIR, prefix="pxm_", suffix=".json")
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
        return {"total": 0, "sum_ms": 0.0, "recent": []}
    try:
        with open(METRICS_FILE, "r") as f:
            raw = json.load(f)
    except Exception:
        # corrupt file → reset
        return {"total": 0, "sum_ms": 0.0, "recent": []}

    if isinstance(raw, dict) and "total" in raw:
        raw.setdefault("sum_ms", 0.0); raw.setdefault("recent", [])
        return raw

    # legacy list → migrate
    if isinstance(raw, list):
        total = len(raw)
        sum_ms = sum(float(e.get("duration", 0.0)) * 1000.0 for e in raw)
        recent = [{
            "ts": float(e.get("timestamp", time.time())),
            "score": int((e.get("score", 0) if not isinstance(e.get("score"), dict)
                          else e["score"].get("score", 0)) or 0)
        } for e in raw[-100:]]
        return {"total": total, "sum_ms": sum_ms, "recent": recent}

    return {"total": 0, "sum_ms": 0.0, "recent": []}

def sanitize_wallet_input(wallet: str | None):
    if not wallet: return None
    w = wallet.strip()
    return w if w.startswith("r") and 25 <= len(w) <= 35 else None

def rotate_fallback(index, total):
    return (index + 1) % max(1, int(total or 1))

def log_event(wallet, score, duration_ms: float = 200.0):
    """Cumulative total (∞), keep recent=100; no wallet stored."""
    try:
        m = _load_metrics()
        m["total"] = int(m.get("total", 0)) + 1
        m["sum_ms"] = float(m.get("sum_ms", 0.0)) + float(duration_ms or 0.0)
        s = score.get("score") if isinstance(score, dict) else score
        m["recent"] = (m.get("recent", []) + [{
            "ts": time.time(),
            "score": int(s or 0),
        }])[-100:]
        _atomic_write(METRICS_FILE, m)
        print(f"[PX-METRICS] wrote total={m['total']} avg_ms={m['sum_ms']/m['total']:.1f} -> {METRICS_FILE}")
    except Exception as e:
        print("[PX-METRICS][ERROR]", e)
        traceback.print_exc()

def _get_uptime_sec() -> int:
    try:
        if os.path.exists(START_TIME_FILE):
            with open(START_TIME_FILE, "r") as f:
                start = float(f.read().strip())
        else:
            start = time.time()
            with open(START_TIME_FILE, "w") as f:
                f.write(str(start))
        return int(time.time() - start)
    except Exception:
        return 0

def get_metrics():
    m = _load_metrics()
    total = int(m.get("total", 0))
    avg_ms = (m.get("sum_ms", 0.0) / total) if total else 0.0
    last5 = [{"ts": e.get("ts"), "score": e.get("score")} for e in m.get("recent", [])[-5:]]
    return {
        "status": "online",
        "uptime_sec": _get_uptime_sec(),
        "total": total,                 # new
        "avg_response_ms": avg_ms,      # new
        "last": last5,                  # new
        "total_validations": total,                # legacy
        "average_response_time": avg_ms / 1000.0,  # legacy (sec)
        "file": METRICS_FILE,                       # debug (ok to keep)
    }

def log_error(msg): print(f"[PX-ERROR] {msg}")
