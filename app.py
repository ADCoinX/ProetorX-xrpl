# app.py
from __future__ import annotations

import os
from io import BytesIO

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from xrpl_handler import XRPLHandler
from risk_engine import score_wallet_risk
from iso_export import generate_iso20022_xml  # expects (wallet[, balance_xrp])
from rwa_handler import rwa_check
from utils import log_event, get_metrics, sanitize_wallet_input

import uvicorn

# ---------- App ----------
app = FastAPI(
    title="PX – ProetorX Wallet Validator",
    description="XRPL Wallet Validation powered by ADC CryptoGuard"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

xrpl_handler = XRPLHandler()


# ---------- Pages & Static ----------
@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse("templates/index.html")


@app.get("/static/{file_path:path}")
def static_files(file_path: str):
    return FileResponse(f"static/{file_path}")


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
      "risk_score": { "score": int } or number,
      "rwa_status": { "status": "in-development" }
    }
    """
    data = await request.json()
    wallet_raw = data.get("wallet", "")
    wallet = sanitize_wallet_input(wallet_raw)

    if not wallet:
        raise HTTPException(status_code=400, detail="Invalid wallet address.")

    # XRPL fetch (read-only)
    xrpl_data = xrpl_handler.validate_wallet(wallet)

    # Risk scoring (pass the XRPL snapshot)
    risk = score_wallet_risk(xrpl_data)

    # RWA stub
    rwa_status = rwa_check(wallet)

    # light metric/event (no sensitive info)
    try:
        log_event(wallet, risk)
    except Exception:
        pass

    # normalize keys for frontend
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

    # Dapatkan balance XRP (jika gagal → 0.0)
    balance_xrp = 0.0
    try:
        xrpl = xrpl_handler.validate_wallet(wallet)
        balance_xrp = float(xrpl.get("balance_xrp", 0.0))
    except Exception:
        balance_xrp = 0.0

    # Hasilkan XML (sokong dua signature: (wallet, balance) atau (wallet))
    try:
        xml_str = generate_iso20022_xml(wallet, balance_xrp)  # versi baru (disyorkan)
    except TypeError:
        xml_str = generate_iso20022_xml(wallet)               # fallback jika function lama

    # Return sebagai file download
    buf = BytesIO(xml_str.encode("utf-8"))
    filename = f"pain001_{wallet}.xml"
    return StreamingResponse(
        buf,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/metrics")
def metrics():
    """
    Returns metrics snapshot from utils.get_metrics()
    Expected shape (example):
      { "total": 10, "avg_response_ms": 120.4, "last": [...] }
    """
    try:
        return JSONResponse(get_metrics())
    except Exception as e:
        # keep service healthy even if metrics fail
        return JSONResponse({"total": 0, "avg_response_ms": 0, "last": [], "error": str(e)})


# ---------- Entrypoint ----------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
