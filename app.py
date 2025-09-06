from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from xrpl_handler import XRPLHandler
from risk_engine import score_wallet_risk
from iso_export import generate_iso20022_xml
from rwa_handler import rwa_check
from utils import log_event, get_metrics, sanitize_wallet_input
import uvicorn
import os

app = FastAPI(
    title="PX – ProetorX Wallet Validator",
    description="XRPL Wallet Validation powered by ADC CryptoGuard"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

xrpl_handler = XRPLHandler()

@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse("templates/index.html")

@app.post("/validate")
async def validate_wallet(request: Request):
    data = await request.json()
    wallet = sanitize_wallet_input(data.get("wallet", ""))
    print("Wallet input received:", data.get("wallet", ""))
    print("Sanitized wallet:", wallet)
    if not wallet:
        raise HTTPException(status_code=400, detail="Invalid wallet address.")
    xrpl_data = xrpl_handler.validate_wallet(wallet)
    risk_score = score_wallet_risk(xrpl_data)
    rwa_status = rwa_check(wallet)
    log_event(wallet, risk_score)
    return {
        "wallet": wallet,
        "xrpl": xrpl_data,
        "risk_score": risk_score,
        "rwa_status": rwa_status
    }

@app.post("/export_iso")
async def export_iso(request: Request):
    data = await request.json()
    wallet = sanitize_wallet_input(data.get("wallet", ""))
    iso_xml = generate_iso20022_xml(wallet)
    return {"wallet": wallet, "iso_xml": iso_xml}

@app.get("/metrics")
def metrics():
    return get_metrics()

@app.get("/static/{file_path:path}")
def static_files(file_path: str):
    return FileResponse(f"static/{file_path}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
