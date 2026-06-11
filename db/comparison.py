import json
import uuid
from sqlalchemy import text
from db.neon import engine


def set_comparison_pending(document_id: str, template_id: str):
  with engine.connect() as conn:
    existing = conn.execute(
      text('''
        SELECT id FROM "DocumentComparison"
        WHERE "documentId" = :doc_id AND "templateId" = :tpl_id
      '''),
      {"doc_id": document_id, "tpl_id": template_id},
    ).fetchone()

    if existing:
      conn.execute(
        text('''
          UPDATE "DocumentComparison"
          SET status = 'pending', "updatedAt" = NOW()
          WHERE "documentId" = :doc_id AND "templateId" = :tpl_id
        '''),
        {"doc_id": document_id, "tpl_id": template_id},
      )
    else:
      conn.execute(
        text('''
          INSERT INTO "DocumentComparison"
          (id, "documentId", "templateId", status,
           "alignedCount", "deviationCount", "missingCount",
           "createdAt", "updatedAt")
          VALUES (:id, :doc_id, :tpl_id, 'pending', 0, 0, 0, NOW(), NOW())
        '''),
        {"id": str(uuid.uuid4()), "doc_id": document_id, "tpl_id": template_id},
      )
    conn.commit()


def save_document_comparison(document_id: str, template_id: str, result: dict):
  status = result.get("status", "failed")

  deviations = result.get("deviations") or []
  normalized = []
  for d in deviations:
    normalized.append({
      "clause": d.get("clause", "Unknown"),
      "standardText": d.get("standard_text"),
      "contractText": d.get("contract_text"),
      "flag": d.get("flag", "deviation"),
      "severity": d.get("severity", "medium"),
      "notes": d.get("notes", ""),
    })

  params = {
    "doc_id": document_id,
    "tpl_id": template_id,
    "status": status,
    "deviation_score": result.get("deviation_score"),
    "aligned": result.get("aligned_count", 0),
    "deviation": result.get("deviation_count", 0),
    "missing": result.get("missing_count", 0),
    "deviations": json.dumps(normalized),
    "summary": json.dumps(result.get("summary") or {}),
  }

  with engine.connect() as conn:
    conn.execute(
      text('''
        UPDATE "DocumentComparison"
        SET status = :status,
            "deviationScore" = :deviation_score,
            "alignedCount" = :aligned,
            "deviationCount" = :deviation,
            "missingCount" = :missing,
            deviations = CAST(:deviations AS jsonb),
            summary = CAST(:summary AS jsonb),
            "updatedAt" = NOW()
        WHERE "documentId" = :doc_id AND "templateId" = :tpl_id
      '''),
      params,
    )
    conn.commit()
