"""Interview agent: drives the question/answer loop with Claude."""
import os

import anthropic

from . import db
from .models import AnswerResponse

MODEL = "claude-opus-4-8"
# 6 real questions + 1 closing turn
MAX_QUESTIONS = 7

# Mock mode lets the full app run without an API key (demo / UI development).
MOCK = not os.getenv("ANTHROPIC_API_KEY")

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


SYSTEM_PROMPT = """You are a senior {role} interviewer at a top tech company, running a
{difficulty}-level technical screen for {candidate_name}.

Rules:
- Ask exactly ONE question per turn. Never answer your own question.
- Start with fundamentals, then go deeper based on the candidate's answers.
- If an answer is weak or vague, ask a probing follow-up on the same topic before moving on.
- If an answer is strong, escalate difficulty on the next question.
- Keep each question under 60 words. Be professional but human.
- Never reveal scores or judgements during the interview.
{resume_block}"""

_MOCK_QUESTIONS = [
    "Let's start with fundamentals: explain the bias-variance tradeoff, and describe how you'd detect which one is hurting a model you trained.",
    "You're building a fraud-detection model and only 0.3% of transactions are fraud. Walk me through at least two ways you'd handle that class imbalance.",
    "Explain how retrieval-augmented generation works end to end — from a user's question to the final answer. Where does it typically fail?",
    "You deployed a model and its accuracy dropped 10 points in a month. What are the likely causes, and how would you diagnose which one it is?",
    "How would you evaluate an LLM-based feature before shipping it? Describe the eval setup you'd build.",
    "Last one: you have 8GB of GPU memory and need to fine-tune a 7B-parameter model. What are your options?",
]
_MOCK_CLOSING = (
    "That's the end of the interview — thank you for your time! "
    "Your report is being generated now."
)


def build_system(role: str, difficulty: str, candidate_name: str, resume_summary: str | None) -> str:
    resume_block = (
        f"\nCandidate resume summary (tailor 1-2 questions to it):\n{resume_summary}"
        if resume_summary
        else ""
    )
    return SYSTEM_PROMPT.format(
        role=role, difficulty=difficulty, candidate_name=candidate_name, resume_block=resume_block
    )


def ask_next(system: str, transcript: list[dict], question_number: int, session_id: str | None = None) -> AnswerResponse:
    """Given the transcript so far (alternating user/assistant), get the next question."""
    done = question_number >= MAX_QUESTIONS

    if MOCK:
        text = _MOCK_CLOSING if done else _MOCK_QUESTIONS[(question_number - 1) % len(_MOCK_QUESTIONS)]
        return AnswerResponse(next_question=text, question_number=question_number, done=done)

    if done:
        closing = (
            "That's the end of the interview. Thank the candidate in one sentence and "
            "tell them their report is being generated."
        )
        messages = transcript + [{"role": "user", "content": closing}]
    else:
        messages = transcript

    response = get_client().messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=messages,
        thinking={"type": "adaptive"},
    )
    if session_id:
        db.record_usage(session_id, "interview", MODEL, response.usage.input_tokens, response.usage.output_tokens)
    text = next(b.text for b in response.content if b.type == "text")
    return AnswerResponse(next_question=text, question_number=question_number, done=done)
