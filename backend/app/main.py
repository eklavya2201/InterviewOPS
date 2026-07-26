import uuid

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    AnswerRequest,
    AnswerResponse,
    InterviewerEval,
    InterviewReport,
    StartSessionRequest,
    StartSessionResponse,
)
from . import interviewer, evals

app = FastAPI(title="InterviewOps API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store — swap for Redis/DB before deploying multi-instance
SESSIONS: dict[str, dict] = {}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/session/start", response_model=StartSessionResponse)
def start_session(req: StartSessionRequest):
    session_id = uuid.uuid4().hex[:12]
    system = interviewer.build_system(req.role, req.difficulty, req.candidate_name, req.resume_summary)
    transcript = [{"role": "user", "content": "I'm ready. Please begin the interview."}]
    result = interviewer.ask_next(system, transcript, question_number=1)
    transcript.append({"role": "assistant", "content": result.next_question})
    SESSIONS[session_id] = {
        "system": system,
        "transcript": transcript,
        "question_number": 1,
        "role": req.role,
        "difficulty": req.difficulty,
        "done": False,
    }
    return StartSessionResponse(session_id=session_id, opening_question=result.next_question)


@app.post("/api/session/{session_id}/answer", response_model=AnswerResponse)
def submit_answer(session_id: str, req: AnswerRequest):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session["done"]:
        raise HTTPException(400, "Interview already finished — fetch the report")

    session["transcript"].append({"role": "user", "content": req.answer})
    session["question_number"] += 1
    result = interviewer.ask_next(
        session["system"], session["transcript"], session["question_number"]
    )
    session["transcript"].append({"role": "assistant", "content": result.next_question})
    session["done"] = result.done
    return result


@app.post("/api/session/{session_id}/report", response_model=InterviewReport)
def get_report(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return evals.grade_candidate(session["transcript"], session["role"], session["difficulty"])


@app.post("/api/session/{session_id}/meta-eval", response_model=InterviewerEval)
def get_meta_eval(session_id: str):
    """The differentiator: grade the AI interviewer itself."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return evals.grade_interviewer(session["transcript"])
