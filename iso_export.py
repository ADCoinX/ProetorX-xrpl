# iso_export.py
from datetime import datetime, timezone
from uuid import uuid4
from xml.sax.saxutils import escape

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _fmt_amt(x: float, decimals: int = 6) -> str:
    try:
        return f"{float(x):.{decimals}f}"
    except Exception:
        return "0.000000"

def generate_iso20022_xml(wallet: str, balance_xrp: float = 0.0) -> str:
    """
    Generate ISO 20022 pain.001.001.03 XML for a single transfer.
    - wallet: XRPL address (used as debtor ID & name)
    - balance_xrp: numeric balance to export (default 0.0)
    """
    msg_id = f"PX-{uuid4().hex[:12]}"
    e2e_id = f"E2E-{uuid4().hex[:12]}"
    pmtinf_id = f"PMT-{uuid4().hex[:10]}"
    created = _now_iso()
    amount = _fmt_amt(balance_xrp, decimals=6)
    req_exec_dt = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    wallet_name = escape(f"XRPL Wallet {wallet}")
    wallet_id = escape(wallet)

    creditor_name = "Compliance Receiver"
    creditor_id = "rComplianceReceiverXXXXXXXXXXXXXXX"

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>{msg_id}</MsgId>
      <CreDtTm>{created}</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <CtrlSum>{amount}</CtrlSum>
      <InitgPty>
        <Nm>{wallet_name}</Nm>
      </InitgPty>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>{pmtinf_id}</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <BtchBookg>false</BtchBookg>
      <NbOfTxs>1</NbOfTxs>
      <CtrlSum>{amount}</CtrlSum>
      <PmtTpInf>
        <SvcLvl>
          <Cd>SEPA</Cd>
        </SvcLvl>
      </PmtTpInf>
      <ReqdExctnDt>{req_exec_dt}</ReqdExctnDt>

      <!-- Debtor -->
      <Dbtr>
        <Nm>{wallet_name}</Nm>
      </Dbtr>
      <DbtrAcct>
        <Id>
          <Othr>
            <Id>{wallet_id}</Id>
            <SchmeNm>
              <Prtry>XRPL</Prtry>
            </SchmeNm>
          </Othr>
        </Id>
      </DbtrAcct>
      <DbtrAgt>
        <FinInstnId>
          <Othr>
            <Id>XRPL</Id>
          </Othr>
        </FinInstnId>
      </DbtrAgt>

      <ChrgBr>SLEV</ChrgBr>

      <!-- Credit Transfer -->
      <CdtTrfTxInf>
        <PmtId>
          <EndToEndId>{e2e_id}</EndToEndId>
        </PmtId>
        <Amt>
          <InstdAmt Ccy="XRP">{amount}</InstdAmt>
        </Amt>
        <CdtrAgt>
          <FinInstnId>
            <Othr>
              <Id>XRPL</Id>
            </Othr>
          </FinInstnId>
        </CdtrAgt>
        <Cdtr>
          <Nm>{creditor_name}</Nm>
        </Cdtr>
        <CdtrAcct>
          <Id>
            <Othr>
              <Id>{creditor_id}</Id>
              <SchmeNm>
                <Prtry>XRPL</Prtry>
              </SchmeNm>
            </Othr>
          </Id>
        </CdtrAcct>
        <RmtInf>
          <Ustrd>PX export (demo) — not a payment order</Ustrd>
        </RmtInf>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>'''
    return xml
