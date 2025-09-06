# xrpl_handler.py
import requests
from utils import rotate_fallback, log_error

# Public JSON-RPC endpoints (Mainnet)
XRPL_APIS = [
    "https://s1.ripple.com:51234/",   # Ripple public rippled
    "https://xrplcluster.com/"        # Public cluster (JSON-RPC)
    # NOTE: jangan guna "https://xrpl.org/public-api/" (itu docs, bukan endpoint)
]

JSON_HEADERS = {"Content-Type": "application/json"}

class XRPLHandler:
    def __init__(self):
        self.fallback_index = 0
        self.session = requests.Session()

    def _post(self, url: str, payload: dict, timeout: float = 6.0):
        return self.session.post(url, json=payload, headers=JSON_HEADERS, timeout=timeout)

    def validate_wallet(self, wallet: str) -> dict:
        """
        Returns:
          {
            "ok": bool,
            "api_used": str,
            "funded": bool,
            "balance_xrp": float,
            "balance_drops": int,
            "owner_count": int,
            "flags": int
          }
        """
        wallet = wallet.strip()
        attempts = 0
        n = len(XRPL_APIS)

        while attempts < n:
            api_url = XRPL_APIS[self.fallback_index]
            try:
                r = self._post(api_url, {
                    "method": "account_info",
                    "params": [{
                        "account": wallet,
                        "ledger_index": "validated",
                        "strict": True
                    }]
                })
                data = r.json()
                # Success path
                if r.status_code == 200 and isinstance(data, dict) and "result" in data:
                    res = data["result"]

                    # Unfunded or not found
                    if res.get("status") == "error" or "account_data" not in res:
                        err = res.get("error")
                        if err in ("actNotFound", "actMalformed", "invalidParams"):
                            return {
                                "ok": True,
                                "api_used": api_url,
                                "funded": False,
                                "balance_xrp": 0.0,
                                "balance_drops": 0,
                                "owner_count": 0,
                                "flags": 0
                            }
                        # other errors → try next endpoint
                        raise RuntimeError(f"XRPL error: {err or 'unknown'}")

                    acc = res["account_data"]
                    drops = int(acc.get("Balance", 0))
                    balance_xrp = round(drops / 1_000_000, 6)  # convert drops → XRP
                    owner_cnt = int(acc.get("OwnerCount", 0))
                    flags = int(acc.get("Flags", 0))

                    return {
                        "ok": True,
                        "api_used": api_url,
                        "funded": True,
                        "balance_xrp": balance_xrp,
                        "balance_drops": drops,
                        "owner_count": owner_cnt,
                        "flags": flags
                    }

                # Bad HTTP/shape → rotate
                raise RuntimeError(f"Bad response shape or status={r.status_code}")

            except Exception as e:
                log_error(f"[XRPL] {api_url} failed: {e}")
                # rotate once per failure
                self.fallback_index = rotate_fallback(self.fallback_index, n)
                attempts += 1

        # All endpoints failed
        return {
            "ok": False,
            "api_used": "",
            "funded": False,
            "balance_xrp": 0.0,
            "balance_drops": 0,
            "owner_count": 0,
            "flags": 0
        }
