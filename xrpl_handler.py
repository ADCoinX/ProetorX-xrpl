import requests
from utils import rotate_fallback, log_error

XRPL_APIS = [
    "https://s1.ripple.com:51234/",
    "https://xrplcluster.com/",
    "https://xrpl.org/public-api/"
]

class XRPLHandler:
    def __init__(self):
        self.fallback_index = 0

    def validate_wallet(self, wallet):
        api_url = XRPL_APIS[self.fallback_index]
        # Input sanitization
        wallet = wallet.strip()
        try:
            # Example: get account info (replace with actual XRPL API call as needed)
            r = requests.post(api_url, json={
                "method": "account_info",
                "params": [{"account": wallet}]
            }, timeout=5)
            if r.status_code == 200 and "result" in r.json():
                result = r.json()["result"]["account_data"]
                return {
                    "balance": result.get("Balance", 0),
                    "tx_count": result.get("OwnerCount", 0),
                    "flags": result.get("Flags", 0)
                }
            else:
                # fallback if needed
                self.fallback_index = rotate_fallback(self.fallback_index, len(XRPL_APIS))
                log_error(f"Fallback to XRPL API #{self.fallback_index}")
                return self.validate_wallet(wallet)
        except Exception as e:
            self.fallback_index = rotate_fallback(self.fallback_index, len(XRPL_APIS))
            log_error(str(e))
            return self.validate_wallet(wallet)