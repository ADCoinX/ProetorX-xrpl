def generate_iso20022_xml(wallet):
    # pain.001 example stub
    xml = f"""<?xml version="1.0"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>PX-{wallet}</MsgId>
      <CreDtTm>2025-09-06T00:00:00</CreDtTm>
    </GrpHdr>
    <PmtInf>
      <Dbtr>
        <Nm>Wallet {wallet}</Nm>
      </Dbtr>
      <CdtTrfTxInf>
        <Amt>
          <InstdAmt Ccy="XRP">0</InstdAmt>
        </Amt>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>
"""
    return xml