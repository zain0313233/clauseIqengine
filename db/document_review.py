import json
import os
import uuid
from datetime import datetime, timezone

import psycopg2


def _conn():
  return psycopg2.connect(os.getenv("DATABASE_URL"))


def update_document_review(
  document_id: str,
  status: str,
  notes: dict,
  reviewed_by: str | None = None,
  queries_enabled: bool | None = None,
):
  conn = _conn()
  cur = conn.cursor()
  try:
    if queries_enabled is None:
      cur.execute(
        '''
        UPDATE "Document"
        SET "contentReviewStatus" = %s,
            "contentReviewNotes" = %s::jsonb,
            "contentReviewedAt" = %s,
            "contentReviewedBy" = %s,
            "updatedAt" = NOW()
        WHERE id = %s
        ''',
        (
          status,
          json.dumps(notes),
          datetime.now(timezone.utc),
          reviewed_by,
          document_id,
        ),
      )
    else:
      cur.execute(
        '''
        UPDATE "Document"
        SET "contentReviewStatus" = %s,
            "contentReviewNotes" = %s::jsonb,
            "contentReviewedAt" = %s,
            "contentReviewedBy" = %s,
            "queriesEnabled" = %s,
            "updatedAt" = NOW()
        WHERE id = %s
        ''',
        (
          status,
          json.dumps(notes),
          datetime.now(timezone.utc),
          reviewed_by,
          queries_enabled,
          document_id,
        ),
      )
    conn.commit()
  finally:
    cur.close()
    conn.close()


def notify_admins_document_security(document_id: str, scan: dict) -> None:
  conn = _conn()
  cur = conn.cursor()
  try:
    cur.execute(
      'SELECT title, "userId" FROM "Document" WHERE id = %s',
      (document_id,),
    )
    doc = cur.fetchone()
    if not doc:
      return
    title, owner_id = doc[0], doc[1]

    cur.execute('SELECT id FROM "User" WHERE role = %s', ("admin",))
    admins = cur.fetchall()
    threats = scan.get("threats") or scan.get("security_risks") or []
    body = f'"{title}" was blocked after security scan. Threats: {", ".join(threats[:3]) or "see review"}.'

    for (admin_id,) in admins:
      ref = f"document_security_alert:{document_id}:{admin_id}"
      cur.execute(
        'SELECT id FROM "Notification" WHERE "userId" = %s AND "referenceKey" = %s',
        (admin_id, ref),
      )
      if cur.fetchone():
        continue
      cur.execute(
        '''
        INSERT INTO "Notification"
        (id, "userId", type, title, body, read, metadata, "referenceKey", "createdAt")
        VALUES (%s, %s, %s, %s, %s, false, %s::jsonb, %s, NOW())
        ''',
        (
          str(uuid.uuid4()),
          admin_id,
          "document_security_alert",
          "Malicious document blocked",
          body,
          json.dumps({
            "documentId": document_id,
            "ownerId": owner_id,
            "threats": threats,
          }),
          ref,
        ),
      )
    conn.commit()
  finally:
    cur.close()
    conn.close()


def get_document_chunks_sample(document_id: str, limit: int = 8) -> str:
  conn = _conn()
  cur = conn.cursor()
  try:
    cur.execute(
      '''
      SELECT content FROM "Chunk"
      WHERE "documentId" = %s
      ORDER BY "chunkIndex" ASC
      LIMIT %s
      ''',
      (document_id, limit),
    )
    rows = cur.fetchall()
    return "\n\n".join(r[0] for r in rows if r[0])
  finally:
    cur.close()
    conn.close()


def get_document_query_flags(document_id: str) -> dict:
  conn = _conn()
  cur = conn.cursor()
  try:
    cur.execute(
      '''
      SELECT "contentReviewStatus", "queriesEnabled", title
      FROM "Document"
      WHERE id = %s
      ''',
      (document_id,),
    )
    row = cur.fetchone()
    if not row:
      return {"found": False}
    return {
      "found": True,
      "content_review_status": row[0] or "valid",
      "queries_enabled": row[1] if row[1] is not None else True,
      "title": row[2],
    }
  finally:
    cur.close()
    conn.close()
