"""Interview agent: drives the question/answer loop with Claude."""
import anthropic

from .models import AnswerResponse

client = anthropic.Anthropic()

MODEL = "claude-opus-4-8"
MAX_QUESTIONS = 6

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


def build_system(role: str, difficulty: str, candidate_name: str, resume_summary: str | None) -> str:
    resume_block = (
        f"\nCandidate resume summary (tailor 1-2 questions to it):\n{resume_summary}"
        if resume_summary
        else ""
    )
    return SYSTEM_PROMPT.format(
        role=role, difficulty=difficulty, candidate_name=candidate_name, resume_block=resume_block
    )


def ask_next(system: str, transcript: list[dict], question_number: int) -> AnswerResponse:
    """Given the transcript so far (alternating user/assistant), get the next question."""
    done = question_number >= MAX_QUESTIONS
    if done:
        closing = (
            "That's the end of the interview. Thank the candidate in one sentence and "
            "tell them their report is being generated."
        )
        messages = transcript + [{"role": "user", "content": closing}]
    else:
        messages = transcript

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=messages,
        thinking={"type": "adaptive"},
    )
    text = next(b.text for b in response.content if b.type == "text")
    return AnswerResponse(next_question=text, question_number=question_number, done=done)
