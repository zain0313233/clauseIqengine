from fastapi import APIRouter
from models.schemas import QueryRequest, QueryResponse, QuerySource
from services.groq_service import generate_answer
from services.retrieval import retrieve_document_chunks

router = APIRouter()


@router.post("/", response_model=QueryResponse)
async def query_document(request: QueryRequest):
  chunks = retrieve_document_chunks(request.question, request.document_id)

  if not chunks:
    return QueryResponse(
      answer="I could not find relevant information in this document for your question.",
      sources=[],
      confidence="low",
    )

  result = generate_answer(request.question, chunks, mode=request.mode)

  sources = [
    QuerySource(
      content=c["content"],
      chunk_index=c["chunk_index"],
      score=c["score"],
    )
    for c in chunks
  ]

  return QueryResponse(
    answer=result["answer"],
    sources=sources,
    confidence=result["confidence"],
  )
