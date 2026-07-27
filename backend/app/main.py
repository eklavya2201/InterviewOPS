import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .models import (
    AnswerRequest,
    AnswerResponse,
    InterviewerEval,
    InterviewReport,
    StartSessionRequest,
    StartSessionResponse,
)
from . import costs, db, interviewer, evals

app = FastAPI(title="InterviewOps API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "mock": interviewer.MOCK}


@app.post("/api/session/start", response_model=StartSessionResponse)
def start_session(req: StartSessionRequest):
    session_id = uuid.uuid4().hex[:12]
    system = interviewer.build_system(req.role, req.difficulty, req.candidate_name, req.resume_summary)
    transcript = [{"role": "user", "content": "I'm ready. Please begin the interview."}]
    result = interviewer.ask_next(system, transcript, question_number=1, session_id=session_id)
    transcript.append({"role": "assistant", "content": result.next_question})
    db.save_session(session_id, {
        "system": system,
        "transcript": transcript,
        "question_number": 1,
        "role": req.role,
        "difficulty": req.difficulty,
        "done": False,
    })
    return StartSessionResponse(session_id=session_id, opening_question=result.next_question)


@app.post("/api/session/{session_id}/answer", response_model=AnswerResponse)
def submit_answer(session_id: str, req: AnswerRequest):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session["done"]:
        raise HTTPException(400, "Interview already finished — fetch the report")

    session["transcript"].append({"role": "user", "content": req.answer})
    session["question_number"] += 1
    result = interviewer.ask_next(
        session["system"], session["transcript"], session["question_number"], session_id=session_id
    )
    session["transcript"].append({"role": "assistant", "content": result.next_question})
    session["done"] = result.done
    db.save_session(session_id, session)
    return result


@app.post("/api/session/{session_id}/report", response_model=InterviewReport)
def get_report(session_id: str):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    report = evals.grade_candidate(session["transcript"], session["role"], session["difficulty"], session_id=session_id)
    db.save_interview(session_id, session["role"], session["difficulty"], report=report.model_dump())
    return report


@app.post("/api/session/{session_id}/meta-eval", response_model=InterviewerEval)
def get_meta_eval(session_id: str):
    """The differentiator: grade the AI interviewer itself."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    meta = evals.grade_interviewer(session["transcript"], session_id=session_id)
    db.save_interview(session_id, session["role"], session["difficulty"], meta=meta.model_dump())
    return meta


@app.get("/api/history")
def get_history():
    """Completed interviews persisted server-side (survives browser and server restarts)."""
    return db.list_interviews()


@app.get("/api/usage")
def get_usage():
    """Token + cost summary for the cost dashboard."""
    summary = db.usage_summary()
    for s in summary["sessions"]:
        s["cost_inr"] = round(costs.cost_inr(s["model"], s["input_tokens"], s["output_tokens"]), 2)
    summary["total_cost_inr"] = round(sum(s["cost_inr"] for s in summary["sessions"]), 2)
    summary["usd_to_inr"] = costs.USD_TO_INR
    summary["mock"] = interviewer.MOCK
    return summary


# Serve the frontend from the same origin (must be mounted after the API routes)
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
