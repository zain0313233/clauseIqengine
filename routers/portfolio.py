from fastapi import APIRouter
from models.schemas import (
  PortfolioQueryRequest,
  PortfolioQueryResponse,
  PortfolioSource,
)
from db.ownership import assert_documents_owned
from services.embedder import embed_query
from services.pinecone_service import search_chunks_portfolio
from services.groq_service import generate_portfolio_answer

router = APIRouter()

MAX_PORTFOLIO_DOCS = 50


@router.post("/", response_model=PortfolioQueryResponse)
async def query_portfolio(request: PortfolioQueryRequest):
  document_ids = list(dict.fromkeys(request.document_ids))
  if len(document_ids) > MAX_PORTFOLIO_DOCS:
    from fastapi import HTTPException

    raise HTTPException(status_code=400, detail="Too many documents in portfolio query")

  assert_documents_owned(document_ids, request.user_id)

  if not document_ids:
    return PortfolioQueryResponse(
      answer="No ready documents in your portfolio to search. Upload and process contracts first.",
      sources=[],
      confidence="low",
      documents_searched=0,
    )

  query_embedding = embed_query(request.question)
  chunks = search_chunks_portfolio(query_embedding, document_ids)

  if not chunks:
    return PortfolioQueryResponse(
      answer="I could not find relevant information across your contracts for this question.",
      sources=[],
      confidence="low",
      documents_searched=len(document_ids),
    )

  result = generate_portfolio_answer(
    request.question,
    chunks,
    request.document_titles,
  )

  sources = [
    PortfolioSource(
      content=c["content"],
      chunk_index=c["chunk_index"],
      document_id=c["document_id"],
      document_title=request.document_titles.get(c["document_id"], "Unknown document"),
      score=c["score"],
    )
    for c in chunks
  ]

  return PortfolioQueryResponse(
    answer=result["answer"],
    sources=sources,
    confidence=result["confidence"],
    documents_searched=len(document_ids),
  )
