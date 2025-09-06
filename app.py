from __future__ import annotations

import os
import re
from io import BytesIO

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import (
    HTMLResponse,
    FileResponse,
    StreamingResponse,
    JSONResponse,
    Response,
)
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
    description="XRPL Wallet Validation powered by ADC CryptoGuard",
)

# ---- CORS (boleh ketatkan ikut domain kau) ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# ---- Security headers + CSP (allow inline script & same-origin fetch) ----
@app.middleware("http")
async def security_headers_mw(request: Request, call_next):
    resp: Response = await call_next(request)
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; "
        "connect-src 'self';"
    )
    return resp

xrpl_handler = XRPLHandler()

# ---------- Pages & Static ----------
@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(os.path.join("templates", "index.html"))

# hardened static serving
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
      "xrpl": { "ok": bool, "funded": bool, "balance_xrp": float, "balance_drops": int,
                "owner_count": int, "flags": int, "api_used": "..." },
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
    Returns: pain.001 XML as file download (amount = current balance_xrp best-effort)
    """
    data = await request.json()
    wallet_raw = data.get("wallet", "")
    wallet = sanitize_wallet_input(wallet_raw)
    if not wallet:
        raise HTTPException(status_code=400, detail="Invalid XRPL address.")

    # best-effort balance
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

    # safe filename
    safe_wallet = re.sub(r"[^A-Za-z0-9_-]", "_", wallet)[:40]
    filename = f"pain001_${safe_wallet}.xml".replace("$", "")  # extra hardening

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
