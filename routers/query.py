from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
from models.schemas import QueryRequest, QueryResponse, QuerySource
from db.ownership import assert_document_owner
from services.groq_service import (
  generate_answer,
  generate_answer_stream,
  _clean_answer,
  _confidence_from_sources,
)
from services.retrieval import retrieve_document_chunks

router = APIRouter()


def _sources_payload(chunks: list[dict]) -> list[dict]:
  return [
    {
      "content": c["content"],
      "chunk_index": c["chunk_index"],
      "score": c["score"],
    }
    for c in chunks
  ]


@router.post("/stream")
async def query_document_stream(request: QueryRequest):
  assert_document_owner(request.document_id, request.user_id)
  history = [{"role": t.role, "content": t.content} for t in request.history]

  def event_stream():
    yield f"data: {json.dumps({'type': 'status', 'text': 'Analyzing…'})}\n\n"

    chunks = retrieve_document_chunks(request.question, request.document_id, history)

    if not chunks:
      yield f"data: {json.dumps({'type': 'token', 'text': 'I could not find relevant information in this document for your question.'})}\n\n"
      yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
      yield f"data: {json.dumps({'type': 'done', 'confidence': 'low'})}\n\n"
      return

    sources = _sources_payload(chunks)
    yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
    yield f"data: {json.dumps({'type': 'status', 'text': 'Thinking…'})}\n\n"

    parts: list[str] = []
    for token in generate_answer_stream(
      request.question, chunks, mode=request.mode, history=request.history
    ):
      parts.append(token)
      yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

    answer = _clean_answer("".join(parts))
    confidence = _confidence_from_sources(chunks, answer)
    yield f"data: {json.dumps({'type': 'done', 'confidence': confidence})}\n\n"

  return StreamingResponse(
    event_stream(),
    media_type="text/event-stream",
    headers={
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    },
  )


@router.post("/", response_model=QueryResponse)
async def query_document(request: QueryRequest):
  assert_document_owner(request.document_id, request.user_id)
  history = [{"role": t.role, "content": t.content} for t in request.history]
  chunks = retrieve_document_chunks(request.question, request.document_id, history)

  if not chunks:
    return QueryResponse(
      answer="I could not find relevant information in this document for your question.",
      sources=[],
      confidence="low",
    )

  result = generate_answer(
    request.question, chunks, mode=request.mode, history=request.history
  )

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
