from fastapi import APIRouter, BackgroundTasks
from models.schemas import ProcessRequest
from services.parser import parse_document
from services.chunker import chunk_text
from services.embedder import embed_texts
from services.pinecone_service import store_chunks
from db.neon import update_document_status
import psycopg2
import os

router = APIRouter()

async def process_document_task(request: ProcessRequest):
    try:
        # 1. Update status to processing
        update_document_status(request.document_id, "processing")

        # 2. Parse document
        text = await parse_document(request.file_url, request.file_type)

        # 3. Chunk text
        chunks = chunk_text(text)

        # 4. Embed chunks
        embeddings = embed_texts(chunks)

        # 5. Store in Pinecone
        pinecone_ids = store_chunks(request.document_id, chunks, embeddings)

        # 6. Save chunks to Neon DB
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        for i, (chunk, pid) in enumerate(zip(chunks, pinecone_ids)):
            cur.execute(
                'INSERT INTO "Chunk" (id, content, "chunkIndex", "pineconeId", "documentId", "createdAt") VALUES (gen_random_uuid()::text, %s, %s, %s, %s, NOW())',
                (chunk, i, pid, request.document_id)
            )
        conn.commit()
        cur.close()
        conn.close()

        # 7. Update status to ready
        update_document_status(request.document_id, "ready")

    except Exception as e:
        update_document_status(request.document_id, "failed")
        raise e

@router.post("/")
async def process_document(request: ProcessRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_document_task, request)
    return {"message": "Document processing started", "document_id": request.document_id}