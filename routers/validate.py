from fastapi import APIRouter
from pydantic import BaseModel

from db.document_review import (
  get_document_chunks_sample,
  get_document_query_flags,
  update_document_review,
)
from services.content_guard import assess_question_scope
from services.document_reviewer import assess_document_content

router = APIRouter()


class ValidateDocumentRequest(BaseModel):
  document_id: str
  title: str = ""
  reviewed_by: str | None = None
  persist: bool = True


class QuestionScopeRequest(BaseModel):
  question: str


@router.post("/document")
async def validate_document(request: ValidateDocumentRequest):
  text = get_document_chunks_sample(request.document_id, limit=12)
  if not text.strip():
    return {
      "status": "pending",
      "summary": "No document text available yet — wait for processing to finish.",
      "is_legal_document": None,
      "confidence": "low",
      "issues": ["empty_content"],
      "security_risks": [],
      "recommendation": "review",
      "admin_message": "Re-run review after document processing completes.",
    }

  result = assess_document_content(text, title=request.title)

  if request.persist:
    queries_enabled = result.get("status") != "rejected"
    update_document_review(
      request.document_id,
      result.get("status", "pending"),
      result,
      reviewed_by=request.reviewed_by,
      queries_enabled=queries_enabled,
    )

  return result


@router.post("/question-scope")
async def validate_question_scope(request: QuestionScopeRequest):
  return assess_question_scope(request.question)
