from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from services.comparer import compare_contracts
from services.parser import parse_document
from db.comparison import save_document_comparison, set_comparison_pending
from db.neon import engine

router = APIRouter()


class CompareRequest(BaseModel):
  document_id: str
  template_id: str
  document_file_url: str
  document_file_type: str
  template_file_url: str
  template_file_type: str
  template_name: str = "Standard"


async def run_comparison_task(
  document_id: str,
  template_id: str,
  document_file_url: str,
  document_file_type: str,
  template_file_url: str,
  template_file_type: str,
  template_name: str,
):
  try:
    set_comparison_pending(document_id, template_id)
    standard_text = await parse_document(template_file_url, template_file_type)
    contract_text = await parse_document(document_file_url, document_file_type)
    result = compare_contracts(standard_text, contract_text, template_name)
    save_document_comparison(document_id, template_id, result)
  except Exception:
    save_document_comparison(document_id, template_id, {"status": "failed"})


@router.post("/")
async def trigger_comparison(request: CompareRequest, background_tasks: BackgroundTasks):
  background_tasks.add_task(
    run_comparison_task,
    request.document_id,
    request.template_id,
    request.document_file_url,
    request.document_file_type,
    request.template_file_url,
    request.template_file_type,
    request.template_name,
  )
  return {
    "message": "Comparison started",
    "document_id": request.document_id,
    "template_id": request.template_id,
  }


@router.get("/{document_id}/{template_id}")
async def get_comparison(document_id: str, template_id: str):
  with engine.connect() as conn:
    row = conn.execute(
      text('''
        SELECT * FROM "DocumentComparison"
        WHERE "documentId" = :doc_id AND "templateId" = :tpl_id
      '''),
      {"doc_id": document_id, "tpl_id": template_id},
    ).mappings().fetchone()

  if not row:
    raise HTTPException(status_code=404, detail="Comparison not found")

  return {
    "id": row["id"],
    "document_id": row["documentId"],
    "template_id": row["templateId"],
    "status": row["status"],
    "deviation_score": row["deviationScore"],
    "aligned_count": row["alignedCount"],
    "deviation_count": row["deviationCount"],
    "missing_count": row["missingCount"],
    "deviations": row["deviations"],
    "summary": row["summary"],
    "updated_at": row["updatedAt"].isoformat() if row["updatedAt"] else None,
  }
