from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from services.analyzer import analyze_contract
from services.parser import parse_document
from db.analysis import save_document_analysis, set_analysis_pending
from db.agents import set_agents_pending, save_agent_report
from db.ownership import assert_document_owner
from services.agents import run_agent_team
from job_limits import job_slot, reject_if_queue_full

router = APIRouter()


class AnalyzeRequest(BaseModel):
  document_id: str
  file_url: str
  file_type: str
  user_id: str


async def run_analysis_task(document_id: str, file_url: str, file_type: str):
  async with job_slot():
    try:
      set_analysis_pending(document_id)
      text_content = await parse_document(file_url, file_type)
      result = analyze_contract(text_content)
      save_document_analysis(document_id, result)

      if result.get("status") == "ready":
        try:
          set_agents_pending(document_id)
          agent_result = run_agent_team(text_content)
          save_agent_report(document_id, agent_result)
        except Exception:
          save_agent_report(document_id, {"status": "failed", "agents": []})
    except Exception:
      save_document_analysis(document_id, {"status": "failed"})


@router.post("/")
async def trigger_analysis(request: AnalyzeRequest, background_tasks: BackgroundTasks):
  assert_document_owner(request.document_id, request.user_id)
  reject_if_queue_full()
  background_tasks.add_task(
    run_analysis_task,
    request.document_id,
    request.file_url,
    request.file_type,
  )
  return {"message": "Analysis started", "document_id": request.document_id}
