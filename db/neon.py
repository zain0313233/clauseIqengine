import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

def get_db():
    with engine.connect() as conn:
        yield conn

def update_document_status(document_id: str, status: str):
    with engine.connect() as conn:
        conn.execute(
            text('UPDATE "Document" SET status = :status WHERE id = :id'),
            {"status": status, "id": document_id}
        )
        conn.commit()