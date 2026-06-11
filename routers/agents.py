from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from services.agents import run_agent_team
from services.parser import parse_document
from db.agents import save_agent_report, set_agents_pending
from db.neon import engine

router = APIRouter()


class AgentsRequest(BaseModel):
  document_id: str
  file_url: str
  file_type: str


async def run_agents_task(document_id: str, file_url: str, file_type: str):
  try:
    set_agents_pending(document_id)
    text_content = await parse_document(file_url, file_type)
    result = run_agent_team(text_content)
    save_agent_report(document_id, result)
  except Exception:
    save_agent_report(document_id, {"status": "failed", "agents": []})


@router.post("/")
async def trigger_agents(request: AgentsRequest, background_tasks: BackgroundTasks):
  background_tasks.add_task(
    run_agents_task,
    request.document_id,
    request.file_url,
    request.file_type,
  )
  return {"message": "Agent team analysis started", "document_id": request.document_id}


@router.get("/{document_id}")
async def get_agent_report(document_id: str):
  with engine.connect() as conn:
    row = conn.execute(
      text('SELECT * FROM "AgentReport" WHERE "documentId" = :id'),
      {"id": document_id},
    ).mappings().fetchone()

  if not row:
    raise HTTPException(status_code=404, detail="Agent report not found")

  return {
    "id": row["id"],
    "document_id": row["documentId"],
    "status": row["status"],
    "agents": row["agents"],
    "updated_at": row["updatedAt"].isoformat() if row["updatedAt"] else None,
  }
