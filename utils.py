# utils.py
import os, json, time, tempfile

METRICS_FILE = "metrics.json"
START_TIME_FILE = "uptime.txt"

def _atomic_write(path, data):
    fd, tmp = tempfile.mkstemp(prefix="pxm_", suffix=".json")
    with os.fdopen(fd, "w") as f: json.dump(data, f)
    os.replace(tmp, path)

def _load():
    if not os.path.exists(METRICS_FILE):
        return {"total": 0, "sum_ms": 0.0, "recent": []}
    raw = json.load(open(METRICS_FILE))
    # v2 dict
    if isinstance(raw, dict) and "total" in raw:
        raw.setdefault("sum_ms", 0.0); raw.setdefault("recent", [])
        return raw
    # v1 list -> migrate
    if isinstance(raw, list):
        return {
            "total": len(raw),
            "sum_ms": sum(float(e.get("duration", 0.0))*1000 for e in raw),  # legacy in s → ms if perlu
            "recent": [{"ts": float(e.get("timestamp", time.time())),
                        "score": int((e.get("score", 0) if not isinstance(e.get("score"), dict)
                                      else e["score"].get("score", 0)) or 0)} for e in raw[-100:]]
        }
    return {"total": 0, "sum_ms": 0.0, "recent": []}

def sanitize_wallet_input(w):
    if not w: return None
    w = w.strip()
    return w if w.startswith("r") and 25 <= len(w) <= 35 else None

def rotate_fallback(i, n): return (i + 1) % max(1, int(n or 1))

def log_event(wallet, score, duration_ms=200.0):
    m = _load()
    m["total"] = int(m.get("total", 0)) + 1
    m["sum_ms"] = float(m.get("sum_ms", 0.0)) + float(duration_ms or 0.0)
    s = score.get("score") if isinstance(score, dict) else score
    m["recent"] = (m.get("recent", []) + [{"ts": time.time(), "score": int(s or 0)}])[-100:]
    _atomic_write(METRICS_FILE, m)

def _uptime_sec():
    if os.path.exists(START_TIME_FILE):
        try: start = float(open(START_TIME_FILE).read().strip())
        except: start = time.time()
    else:
        start = time.time(); open(START_TIME_FILE, "w").write(str(start))
    return int(time.time() - start)

def get_metrics():
    m = _load()
    total = int(m.get("total", 0))
    avg_ms = (m.get("sum_ms", 0.0) / total) if total else 0.0
    last5 = [{"ts": e["ts"], "score": e["score"]} for e in m.get("recent", [])[-5:]]
    # return both new & legacy keys
    return {
        "status": "online",
        "uptime_sec": _uptime_sec(),
        "total": total,
        "avg_response_ms": avg_ms,
        "last": last5,
        "total_validations": total,                # legacy
        "average_response_time": avg_ms / 1000.0,  # legacy (sec)
    }

def log_error(msg): print(f"[PX-ERROR] {msg}")
