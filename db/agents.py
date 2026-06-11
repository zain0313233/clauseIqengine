import json
import uuid
from sqlalchemy import text
from db.neon import engine


def set_agents_pending(document_id: str):
  with engine.connect() as conn:
    existing = conn.execute(
      text('SELECT id FROM "AgentReport" WHERE "documentId" = :doc_id'),
      {"doc_id": document_id},
    ).fetchone()

    if existing:
      conn.execute(
        text('''
          UPDATE "AgentReport"
          SET status = 'pending', "updatedAt" = NOW()
          WHERE "documentId" = :doc_id
        '''),
        {"doc_id": document_id},
      )
    else:
      conn.execute(
        text('''
          INSERT INTO "AgentReport"
          (id, "documentId", status, "createdAt", "updatedAt")
          VALUES (:id, :doc_id, 'pending', NOW(), NOW())
        '''),
        {"id": str(uuid.uuid4()), "doc_id": document_id},
      )
    conn.commit()


def save_agent_report(document_id: str, result: dict):
  status = result.get("status", "failed")
  agents_json = json.dumps(result.get("agents") or [])

  with engine.connect() as conn:
    existing = conn.execute(
      text('SELECT id FROM "AgentReport" WHERE "documentId" = :doc_id'),
      {"doc_id": document_id},
    ).fetchone()

    if existing:
      conn.execute(
        text('''
          UPDATE "AgentReport"
          SET status = :status,
              agents = CAST(:agents AS jsonb),
              "updatedAt" = NOW()
          WHERE "documentId" = :doc_id
        '''),
        {"doc_id": document_id, "status": status, "agents": agents_json},
      )
    else:
      conn.execute(
        text('''
          INSERT INTO "AgentReport"
          (id, "documentId", status, agents, "createdAt", "updatedAt")
          VALUES (:id, :doc_id, :status, CAST(:agents AS jsonb), NOW(), NOW())
        '''),
        {
          "id": str(uuid.uuid4()),
          "doc_id": document_id,
          "status": status,
          "agents": agents_json,
        },
      )
    conn.commit()
