from fastapi import HTTPException
from sqlalchemy import text

from db.neon import engine


def assert_document_owner(document_id: str, user_id: str) -> None:
    with engine.connect() as conn:
        row = conn.execute(
            text('SELECT id FROM "Document" WHERE id = :doc_id AND "userId" = :user_id'),
            {"doc_id": document_id, "user_id": user_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")


def assert_template_owner(template_id: str, user_id: str) -> None:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                'SELECT id FROM "StandardTemplate" WHERE id = :tpl_id AND "userId" = :user_id'
            ),
            {"tpl_id": template_id, "user_id": user_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")


def assert_documents_owned(document_ids: list[str], user_id: str) -> None:
    unique_ids = list(dict.fromkeys(document_ids))
    if not unique_ids:
        return

    placeholders = ", ".join(f":id{i}" for i in range(len(unique_ids)))
    params: dict = {f"id{i}": doc_id for i, doc_id in enumerate(unique_ids)}
    params["user_id"] = user_id

    with engine.connect() as conn:
        count = conn.execute(
            text(
                f'SELECT COUNT(*) FROM "Document" WHERE "userId" = :user_id AND id IN ({placeholders})'
            ),
            params,
        ).scalar()

    if count != len(unique_ids):
        raise HTTPException(status_code=404, detail="One or more documents not found")
