from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from services.analyzer import analyze_contract
from services.parser import parse_document
from db.analysis import save_document_analysis, set_analysis_pending
from db.agents import set_agents_pending, save_agent_report
from services.agents import run_agent_team
from db.neon import engine

router = APIRouter()


class AnalyzeRequest(BaseModel):
  document_id: str
  file_url: str
  file_type: str


async def run_analysis_task(document_id: str, file_url: str, file_type: str):
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
  background_tasks.add_task(
    run_analysis_task,
    request.document_id,
    request.file_url,
    request.file_type,
  )
  return {"message": "Analysis started", "document_id": request.document_id}


@router.get("/{document_id}")
async def get_analysis(document_id: str):
  with engine.connect() as conn:
    row = conn.execute(
      text('SELECT * FROM "DocumentAnalysis" WHERE "documentId" = :id'),
      {"id": document_id},
    ).mappings().fetchone()

  if not row:
    raise HTTPException(status_code=404, detail="Analysis not found")

  return {
    "id": row["id"],
    "document_id": row["documentId"],
    "status": row["status"],
    "risk_score": row["riskScore"],
    "risk_level": row["riskLevel"],
    "high_risk_count": row["highRiskCount"],
    "medium_risk_count": row["mediumRiskCount"],
    "low_risk_count": row["lowRiskCount"],
    "summary": row["summary"],
    "risks": row["risks"],
    "missing_clauses": row["missingClauses"],
    "updated_at": row["updatedAt"].isoformat() if row["updatedAt"] else None,
  }
