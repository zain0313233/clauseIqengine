from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from services.comparer import compare_contracts
from services.parser import parse_document
from db.comparison import save_document_comparison, set_comparison_pending
from db.ownership import assert_document_owner, assert_template_owner
from job_limits import job_slot, reject_if_queue_full

router = APIRouter()


class CompareRequest(BaseModel):
  document_id: str
  template_id: str
  user_id: str
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
  async with job_slot():
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
  assert_document_owner(request.document_id, request.user_id)
  assert_template_owner(request.template_id, request.user_id)
  reject_if_queue_full()
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

