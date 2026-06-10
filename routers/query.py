from fastapi import APIRouter
from models.schemas import QueryRequest, QueryResponse
from services.embedder import embed_query
from services.pinecone_service import search_chunks
from services.groq_service import generate_answer

router = APIRouter()

@router.post("/", response_model=QueryResponse)
async def query_document(request: QueryRequest):
    # 1. Embed the question
    query_embedding = embed_query(request.question)

    # 2. Search Pinecone for relevant chunks
    chunks = search_chunks(query_embedding, request.document_id)

    if not chunks:
        return QueryResponse(
            answer="No relevant information found in this document.",
            sources=[]
        )

    # 3. Generate answer with Groq
    answer = generate_answer(request.question, chunks)

    return QueryResponse(answer=answer, sources=chunks)