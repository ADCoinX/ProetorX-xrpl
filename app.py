# app.py
from __future__ import annotations

import os
import re
from io import BytesIO

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from xrpl_handler import XRPLHandler
from risk_engine import score_wallet_risk
from iso_export import generate_iso20022_xml
from rwa_handler import rwa_check
from utils import log_event, get_metrics, sanitize_wallet_input

import uvicorn

app = FastAPI(
    title="PX – ProetorX Wallet Validator",
    description="XRPL Wallet Validation powered by ADC CryptoGuard"
)

# ---- CORS (tighten if you have known origins) ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# ---- Minimal security headers ----
@app.middleware("http")
async def security_headers_mw(request: Request, call_next):
    resp: Response = await call_next(request)
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    # loosen CSP if you load external resources
    resp.headers.setdefault("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline';")
    return resp

xrpl_handler = XRPLHandler()

# ---------- Pages & Static ----------
# Serve index (constant path; not user-controlled)
@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(os.path.join("templates", "index.html"))

# Hardened static serving (prevents path traversal)
app.mount("/static", StaticFiles(directory="static", html=False), name="static")

@app.get("/healthz")
def healthz():
    return {"ok": True}

# ---------- API ----------
@app.post("/validate")
async def validate_wallet(request: Request):
    """
    Input:  { "wallet": "r..." }
    Output: {
      "wallet": "...",
      "xrpl": {
         "ok": bool, "funded": bool, "balance_xrp": float, "balance_drops": int,
         "owner_count": int, "flags": int, "api_used": "..."
      },
      "risk_score": { "score": int, "level": str, "reasons": [...] },
      "rwa_status": { "status": "in-development" }
    }
    """
    data = await request.json()
    wallet_raw = data.get("wallet", "")
    wallet = sanitize_wallet_input(wallet_raw)
    if not wallet:
        raise HTTPException(status_code=400, detail="Invalid wallet address.")

    xrpl_data = xrpl_handler.validate_wallet(wallet)
    risk = score_wallet_risk(xrpl_data)
    rwa_status = rwa_check(wallet)

    try:
        log_event(wallet, risk)
    except Exception:
        pass

    return {
        "wallet": wallet,
        "xrpl": xrpl_data,
        "risk_score": risk,
        "rwa_status": rwa_status,
    }

@app.post("/export_iso")
async def export_iso(request: Request):
    """
    Input:  { "wallet": "r..." }
    Returns a downloadable ISO20022 pain.001 XML file.
    """
    data = await request.json()
    wallet_raw = data.get("wallet", "")
    wallet = sanitize_wallet_input(wallet_raw)
    if not wallet:
        raise HTTPException(status_code=400, detail="Invalid XRPL address.")

    # Get balance (best-effort)
    try:
        xrpl = xrpl_handler.validate_wallet(wallet)
        balance_xrp = float(xrpl.get("balance_xrp", 0.0))
    except Exception:
        balance_xrp = 0.0

    try:
        xml_str = generate_iso20022_xml(wallet, balance_xrp)
    except TypeError:
        xml_str = generate_iso20022_xml(wallet)

    buf = BytesIO(xml_str.encode("utf-8"))

    # Safe filename (whitelist)
    safe_wallet = re.sub(r"[^A-Za-z0-9_-]", "_", wallet)[:40]
    filename = f"pain001_{safe_wallet}.xml"

    return StreamingResponse(
        buf,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.get("/metrics")
def metrics():
    try:
        return JSONResponse(get_metrics())
    except Exception as e:
        return JSONResponse({"total": 0, "avg_response_ms": 0, "last": [], "error": str(e)})

# ---------- Entrypoint ----------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
