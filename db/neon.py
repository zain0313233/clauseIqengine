import os
import re

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


def normalize_database_url(raw: str) -> str:
    url = re.sub(r"&?channel_binding=require", "", raw)
    if "connect_timeout=" not in url:
        url += "&connect_timeout=30" if "?" in url else "?connect_timeout=30"
    return url


_raw_url = os.getenv("DATABASE_URL") or ""
DATABASE_URL = normalize_database_url(_raw_url) if _raw_url else ""

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


def get_db():
    with engine.connect() as conn:
        yield conn


def update_document_status(document_id: str, status: str):
    with engine.connect() as conn:
        conn.execute(
            text('UPDATE "Document" SET status = :status WHERE id = :id'),
            {"status": status, "id": document_id},
        )
        conn.commit()
