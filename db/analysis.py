import json
import uuid
from sqlalchemy import text
from db.neon import engine
from db.document_metadata import sync_document_metadata


def set_analysis_pending(document_id: str):
  with engine.connect() as conn:
    existing = conn.execute(
      text('SELECT id FROM "DocumentAnalysis" WHERE "documentId" = :doc_id'),
      {"doc_id": document_id},
    ).fetchone()

    if existing:
      conn.execute(
        text('''
          UPDATE "DocumentAnalysis"
          SET status = 'pending', "updatedAt" = NOW()
          WHERE "documentId" = :doc_id
        '''),
        {"doc_id": document_id},
      )
    else:
      conn.execute(
        text('''
          INSERT INTO "DocumentAnalysis"
          (id, "documentId", status, "highRiskCount", "mediumRiskCount", "lowRiskCount", "createdAt", "updatedAt")
          VALUES (:id, :doc_id, 'pending', 0, 0, 0, NOW(), NOW())
        '''),
        {"id": str(uuid.uuid4()), "doc_id": document_id},
      )
    conn.commit()


def save_document_analysis(document_id: str, result: dict):
  status = result.get("status", "failed")

  with engine.connect() as conn:
    existing = conn.execute(
      text('SELECT id FROM "DocumentAnalysis" WHERE "documentId" = :doc_id'),
      {"doc_id": document_id},
    ).fetchone()

    params = {
      "doc_id": document_id,
      "status": status,
      "risk_score": result.get("risk_score"),
      "risk_level": result.get("risk_level"),
      "high": result.get("high_risk_count", 0),
      "medium": result.get("medium_risk_count", 0),
      "low": result.get("low_risk_count", 0),
      "summary": json.dumps(result.get("summary") or {}),
      "risks": json.dumps(result.get("risks") or []),
      "missing": json.dumps(result.get("missing_clauses") or []),
      "obligations": json.dumps(result.get("obligations") or []),
      "timeline": json.dumps(result.get("timeline") or []),
    }

    if existing:
      conn.execute(
        text('''
          UPDATE "DocumentAnalysis"
          SET status = :status,
              "riskScore" = :risk_score,
              "riskLevel" = :risk_level,
              "highRiskCount" = :high,
              "mediumRiskCount" = :medium,
              "lowRiskCount" = :low,
              summary = CAST(:summary AS jsonb),
              risks = CAST(:risks AS jsonb),
              "missingClauses" = CAST(:missing AS jsonb),
              obligations = CAST(:obligations AS jsonb),
              timeline = CAST(:timeline AS jsonb),
              "updatedAt" = NOW()
          WHERE "documentId" = :doc_id
        '''),
        params,
      )
    else:
      conn.execute(
        text('''
          INSERT INTO "DocumentAnalysis"
          (id, "documentId", status, "riskScore", "riskLevel",
           "highRiskCount", "mediumRiskCount", "lowRiskCount",
           summary, risks, "missingClauses", obligations, timeline, "createdAt", "updatedAt")
          VALUES (:id, :doc_id, :status, :risk_score, :risk_level,
                  :high, :medium, :low,
                  CAST(:summary AS jsonb), CAST(:risks AS jsonb), CAST(:missing AS jsonb),
                  CAST(:obligations AS jsonb), CAST(:timeline AS jsonb),
                  NOW(), NOW())
        '''),
        {**params, "id": str(uuid.uuid4())},
      )

    if status == "ready":
      sync_document_metadata(document_id, result)

    conn.commit()
