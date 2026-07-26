"""LLM-as-judge: scores the candidate AND the interviewer itself."""
from .interviewer import MOCK, get_client
from .models import InterviewerEval, InterviewReport, QuestionScore

JUDGE_MODEL = "claude-opus-4-8"

REPORT_PROMPT = """You are an expert technical-interview grader. Below is the full transcript
of a {difficulty}-level {role} screen. Grade the CANDIDATE strictly but fairly.
Score each question 0-10 with concrete evidence from their answer, then give an
overall 0-100 score and a hire signal.

Transcript:
{transcript}"""

META_EVAL_PROMPT = """You are auditing an AI interviewer for quality. Below is the full
transcript of an interview it conducted. Score the INTERVIEWER (not the candidate)
on each dimension 0-10, citing specific turns as evidence in your notes.

Transcript:
{transcript}"""


def _render(transcript: list[dict]) -> str:
    lines = []
    for turn in transcript:
        speaker = "INTERVIEWER" if turn["role"] == "assistant" else "CANDIDATE"
        lines.append(f"{speaker}: {turn['content']}")
    return "\n\n".join(lines)


def _qa_pairs(transcript: list[dict]) -> list[tuple[str, str]]:
    pairs = []
    for i, turn in enumerate(transcript[:-1]):
        if turn["role"] == "assistant" and transcript[i + 1]["role"] == "user":
            pairs.append((turn["content"], transcript[i + 1]["content"]))
    return pairs


def _mock_report(transcript: list[dict]) -> InterviewReport:
    scores = [8, 6, 7, 9, 5, 7]
    per_question = [
        QuestionScore(
            question=q,
            answer=a,
            score=scores[i % len(scores)],
            strengths="[Mock] Covered the core concept with a reasonable structure.",
            gaps="[Mock] Missed edge cases and did not quantify trade-offs.",
            ideal_answer_outline="[Mock] 1. Define the concept  2. Give a concrete example  3. Discuss trade-offs  4. Mention production concerns",
        )
        for i, (q, a) in enumerate(_qa_pairs(transcript))
    ]
    overall = round(sum(p.score for p in per_question) / max(len(per_question), 1) * 10)
    signal = "yes" if overall >= 75 else "lean-yes" if overall >= 60 else "lean-no" if overall >= 45 else "no"
    return InterviewReport(
        overall_score=overall,
        hire_signal=signal,
        summary="[Mock mode] Set ANTHROPIC_API_KEY to get a real Claude-graded report. "
        "This placeholder shows how your results will be laid out.",
        per_question=per_question,
        top_strengths=["Clear communication", "Solid ML fundamentals", "Practical mindset"],
        top_improvements=["Quantify trade-offs with numbers", "Discuss failure modes unprompted"],
    )


def grade_candidate(transcript: list[dict], role: str, difficulty: str) -> InterviewReport:
    if MOCK:
        return _mock_report(transcript)
    response = get_client().messages.parse(
        model=JUDGE_MODEL,
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": REPORT_PROMPT.format(
                role=role, difficulty=difficulty, transcript=_render(transcript)
            ),
        }],
        output_format=InterviewReport,
    )
    return response.parsed_output


def grade_interviewer(transcript: list[dict]) -> InterviewerEval:
    if MOCK:
        return InterviewerEval(
            followed_up_on_weak_answers=7,
            question_relevance=9,
            difficulty_calibration=8,
            no_hallucinated_facts=10,
            notes="[Mock mode] Set ANTHROPIC_API_KEY for a real self-audit of the interviewer.",
        )
    response = get_client().messages.parse(
        model=JUDGE_MODEL,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": META_EVAL_PROMPT.format(transcript=_render(transcript)),
        }],
        output_format=InterviewerEval,
    )
    return response.parsed_output
