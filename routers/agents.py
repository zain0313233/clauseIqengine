from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from services.agents import run_agent_team
from services.parser import parse_document
from db.agents import save_agent_report, set_agents_pending
from db.ownership import assert_document_owner
from job_limits import job_slot, reject_if_queue_full

router = APIRouter()


class AgentsRequest(BaseModel):
  document_id: str
  file_url: str
  file_type: str
  user_id: str


async def run_agents_task(document_id: str, file_url: str, file_type: str):
  async with job_slot():
    try:
      set_agents_pending(document_id)
      text_content = await parse_document(file_url, file_type)
      result = run_agent_team(text_content)
      save_agent_report(document_id, result)
    except Exception:
      save_agent_report(document_id, {"status": "failed", "agents": []})


@router.post("/")
async def trigger_agents(request: AgentsRequest, background_tasks: BackgroundTasks):
  assert_document_owner(request.document_id, request.user_id)
  reject_if_queue_full()
  background_tasks.add_task(
    run_agents_task,
    request.document_id,
    request.file_url,
    request.file_type,
  )
  return {"message": "Agent team analysis started", "document_id": request.document_id}

