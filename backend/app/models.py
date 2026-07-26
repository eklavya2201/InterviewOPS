from typing import Literal, Optional
from pydantic import BaseModel, Field


Role = Literal["ml-engineer", "data-analyst", "data-scientist", "ai-engineer"]
Difficulty = Literal["intern", "fresher", "mid"]


class StartSessionRequest(BaseModel):
    role: Role = "ai-engineer"
    difficulty: Difficulty = "fresher"
    candidate_name: str = "Candidate"
    resume_summary: Optional[str] = None  # optional pasted resume text to tailor questions


class StartSessionResponse(BaseModel):
    session_id: str
    opening_question: str


class AnswerRequest(BaseModel):
    answer: str


class AnswerResponse(BaseModel):
    next_question: str
    question_number: int
    done: bool


class QuestionScore(BaseModel):
    question: str
    answer: str
    score: int = Field(ge=0, le=10)
    strengths: str
    gaps: str
    ideal_answer_outline: str


class InterviewReport(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    hire_signal: Literal["strong-no", "no", "lean-no", "lean-yes", "yes", "strong-yes"]
    summary: str
    per_question: list[QuestionScore]
    top_strengths: list[str]
    top_improvements: list[str]


class InterviewerEval(BaseModel):
    """LLM-as-judge scoring of the INTERVIEWER itself (the meta-eval)."""
    followed_up_on_weak_answers: int = Field(ge=0, le=10)
    question_relevance: int = Field(ge=0, le=10)
    difficulty_calibration: int = Field(ge=0, le=10)
    no_hallucinated_facts: int = Field(ge=0, le=10)
    notes: str
