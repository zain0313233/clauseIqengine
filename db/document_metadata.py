import json
from sqlalchemy import text
from db.neon import engine

VALID_TYPES = {"nda", "vendor", "employment", "service", "saas", "other"}


def _detect_unlimited_liability(result: dict) -> bool:
  if result.get("unlimited_liability"):
    return True
  for risk in result.get("risks") or []:
    blob = f"{risk.get('title', '')} {risk.get('description', '')}".lower()
    if any(
      phrase in blob
      for phrase in (
        "unlimited liability",
        "uncapped liability",
        "no cap on liability",
        "without limitation of liability",
      )
    ):
      return True
  return False


def sync_document_metadata(document_id: str, result: dict):
  summary = result.get("summary") or {}
  parties = summary.get("parties") or []

  contract_type = (result.get("contract_type") or "other").lower()
  if contract_type not in VALID_TYPES:
    contract_type = "other"

  expiration = summary.get("expirationDate")
  if not expiration:
    for event in result.get("timeline") or []:
      if event.get("type") == "expiration" and event.get("date"):
        expiration = event.get("date")
        break

  params = {
    "doc_id": document_id,
    "contract_type": contract_type,
    "parties": json.dumps(parties),
    "effective_date": summary.get("effectiveDate"),
    "expiration_date": expiration,
    "unlimited_liability": _detect_unlimited_liability(result),
  }

  with engine.connect() as conn:
    conn.execute(
      text('''
        UPDATE "Document"
        SET "contractType" = :contract_type,
            parties = CAST(:parties AS jsonb),
            "effectiveDate" = :effective_date,
            "expirationDate" = :expiration_date,
            "unlimitedLiability" = :unlimited_liability,
            "updatedAt" = NOW()
        WHERE id = :doc_id
      '''),
      params,
    )
    conn.commit()
