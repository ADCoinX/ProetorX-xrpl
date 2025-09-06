# risk_engine.py
def score_wallet_risk(wallet_data: dict) -> dict:
    """
    Simple heuristic scoring engine.
    Input: wallet_data dict dari xrpl_handler.validate_wallet
    Output: {score, level, reasons, model}
    """
    score = 0
    reasons = []

    # Baki XRP
    balance_xrp = float(wallet_data.get("balance_xrp", 0) or 0)
    if balance_xrp < 1:
        score += 15
        reasons.append(f"Very low balance ({balance_xrp:.6f} XRP).")
    elif balance_xrp > 20:
        score -= 5
        reasons.append("Healthy balance (>20 XRP).")
    else:
        reasons.append("Moderate balance.")

    # Owner count
    owner_count = int(wallet_data.get("owner_count", 0) or 0)
    if owner_count > 100:
        score += 10
        reasons.append(f"High owner count ({owner_count}).")
    elif owner_count == 0:
        score -= 2
        reasons.append("No owned objects (simple account).")

    # Flags
    flags = int(wallet_data.get("flags", 0) or 0)
    if flags & 0x00400000:
        score += 60
        reasons.append("GlobalFreeze set.")
    if flags & 0x00080000:
        score += 25
        reasons.append("DisallowXRP set.")
    if flags & 0x00010000:
        score += 5
        reasons.append("RequireDestTag set.")
    if flags & 0x00020000:
        reasons.append("DefaultRipple enabled.")

    # Clamp 0–100
    score = max(0, min(100, score))

    # Kategori
    if score <= 20:
        level = "Low Risk"
    elif score <= 60:
        level = "Medium Risk"
    else:
        level = "High Risk"

    return {
        "score": int(score),
        "level": level,
        "reasons": reasons,
        "model": "heuristic-stub"
    }
