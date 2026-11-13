"""LLM Evaluation Arena & FACTS Benchmark Studio.

Main FastAPI Application.
"""

import os
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

from core.engine import run_arena_comparison
from core.facts_rubric import (
    FACTSAssessment,
    EvaluationSubmission,
    compare_assessments
)
from core.ground_truth_trainer import grade_trainer_case
from core.storage import (
    init_db,
    save_evaluation,
    save_trainer_attempt,
    get_recent_evaluations
)


app = FastAPI(
    title="LLM Evaluation Arena & FACTS Studio",
    description="Dual-model comparison arena and ground-truth evaluator trainer.",
    version="1.0.0"
)

# Enable CORS for external automation/hooks
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Initialize storage on startup
init_db()


# -------------------------------------------------------------
# Request Schemas
# -------------------------------------------------------------
class CompareRequest(BaseModel):
    prompt: str
    model_a: str = "llama3:latest"
    model_b: str = "gemini-1.5-flash"


class TrainerSubmitRequest(BaseModel):
    case_id: str
    assessment_a: FACTSAssessment
    assessment_b: FACTSAssessment
    user_winner: str


# -------------------------------------------------------------
# Web & API Endpoints
# -------------------------------------------------------------
@app.get("/")
async def index_view(request: Request):
    """Renders the main interactive studio dashboard."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/compare")
async def api_compare(req: CompareRequest):
    """Executes asynchronous dual-model inference."""
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    
    result = await run_arena_comparison(
        prompt=req.prompt,
        model_a=req.model_a,
        model_b=req.model_b
    )
    return result


@app.post("/api/evaluate")
async def api_evaluate(sub: EvaluationSubmission):
    """Processes user FACTS scores, computes composite weights, and persists evaluation."""
    comparison = compare_assessments(sub.assessment_a, sub.assessment_b)
    
    record_id = save_evaluation({
        "prompt": sub.prompt,
        "model_a_name": sub.model_a_name,
        "model_a_response": sub.model_a_response,
        "model_b_name": sub.model_b_name,
        "model_b_response": sub.model_b_response,
        "score_a": comparison["score_a"],
        "score_b": comparison["score_b"],
        "winner": sub.winner,
        "assessment_a": sub.assessment_a.model_dump(),
        "assessment_b": sub.assessment_b.model_dump(),
        "tags": sub.tags or []
    })
    
    return {
        "status": "success",
        "evaluation_id": record_id,
        "comparison": comparison
    }


@app.get("/api/benchmarks")
async def api_get_benchmarks():
    """Returns curated benchmark cases for Evaluator Trainer mode."""
    benchmarks_path = os.path.join(BASE_DIR, "data", "benchmarks.json")
    if not os.path.exists(benchmarks_path):
        return []
    with open(benchmarks_path, "r", encoding="utf-8") as f:
        benchmarks = json.load(f)
    
    # Return sanitized version (hide gold standard from pre-submission inspection)
    sanitized = []
    for b in benchmarks:
        sanitized.append({
            "id": b["id"],
            "title": b["title"],
            "domain": b["domain"],
            "difficulty": b["difficulty"],
            "prompt": b["prompt"],
            "model_a_name": b["model_a_name"],
            "model_a_response": b["model_a_response"],
            "model_b_name": b["model_b_name"],
            "model_b_response": b["model_b_response"]
        })
    return sanitized


@app.post("/api/trainer/submit")
async def api_trainer_submit(req: TrainerSubmitRequest):
    """Evaluates human reviewer against hidden Gold Standard annotations."""
    benchmarks_path = os.path.join(BASE_DIR, "data", "benchmarks.json")
    with open(benchmarks_path, "r", encoding="utf-8") as f:
        benchmarks = json.load(f)
        
    case_data = next((b for b in benchmarks if b["id"] == req.case_id), None)
    if not case_data:
        raise HTTPException(status_code=404, detail="Benchmark case not found.")

    report = grade_trainer_case(
        case_data=case_data,
        user_assessment_a=req.assessment_a,
        user_assessment_b=req.assessment_b,
        user_winner=req.user_winner
    )
    
    save_trainer_attempt(report)
    return report


@app.get("/api/history")
async def api_get_history():
    """Fetches recent evaluations for audit trails."""
    return get_recent_evaluations(limit=15)


@app.post("/api/webhook/evaluate")
async def api_webhook(req: CompareRequest):
    """Webhook entrypoint for automated test runners or n8n workflows."""
    result = await run_arena_comparison(
        prompt=req.prompt,
        model_a=req.model_a,
        model_b=req.model_b
    )
    return {
        "webhook_status": "processed",
        "result": result
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"🚀 LLM Eval Arena running on http://{host}:{port}")
    uvicorn.run("app:app", host=host, port=port, reload=True)
