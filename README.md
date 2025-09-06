# PX – ProetorX Wallet Validator

![PX Logo](static/px-logo.png)
[![SonarCloud Status](https://sonarcloud.io/api/project_badges/measure?project=ProetorX)](https://sonarcloud.io/dashboard?id=ProetorX)

## Tagline
**Verified First, Trusted Later**

---

## Description

ProetorX (PX) is an open-source, compliance-first, stateless XRPL wallet validator and risk assessment engine powered by ADC CryptoGuard. Designed for Ripple XRPL Grants and BDAX Accelerator, PX validates wallets, scores risk with AI, exports ISO20022 XML, and provides RWA readiness.

## Features

- **XRPL Wallet Validation:** Balance, transaction count, flags, with robust API failover.
- **AI Risk Scoring:** Scikit-learn powered stub (full model in development).
- **ISO 20022 Export:** Generate pain.001 XML for compliance/reporting.
- **RWA Module:** Real-World Asset eligibility (stub, in development).
- **Metrics Dashboard:** Validations, response time, last 5 wallets.
- **Stateless, Secure:** No sensitive data stored, InfoSec best practices.
- **Modern UI:** Responsive, branding, dark/light theme, SonarCloud badges.

## Setup

1. **Clone:**
   ```bash
   git clone https://github.com/ADCoinX/ProetorX.git && cd ProetorX
   ```
2. **Install:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run:**
   ```bash
   uvicorn app:app --reload
   ```
4. **Visit:** [localhost:8080](http://localhost:8080)

## API Examples

- **Validate Wallet**
  ```bash
  curl -X POST http://localhost:8080/validate -d '{"wallet": "rEXAMPLEADDRESS"}' -H 'Content-Type: application/json'
  ```
- **Export ISO XML**
  ```bash
  curl -X POST http://localhost:8080/export_iso -d '{"wallet": "rEXAMPLEADDRESS"}' -H 'Content-Type: application/json'
  ```
- **Metrics**
  ```bash
  curl http://localhost:8080/metrics
  ```

## Screenshot Placeholders

> ![UI Screenshot Placeholder](static/px-logo.png)
> _Grant reviewers: Demo screenshots available on request._

## InfoSec Disclaimer

PX is stateless and does **not** store sensitive user data. All validation, scoring, and exports are performed with security best practices (CORS, headers, TLS-ready).

---

## License

See [LICENSE](LICENSE).

---