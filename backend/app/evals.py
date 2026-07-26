"""LLM-as-judge: scores the candidate AND the interviewer itself."""
import anthropic

from .models import InterviewReport, InterviewerEval

client = anthropic.Anthropic()

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


def grade_candidate(transcript: list[dict], role: str, difficulty: str) -> InterviewReport:
    response = client.messages.parse(
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
    response = client.messages.parse(
        model=JUDGE_MODEL,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": META_EVAL_PROMPT.format(transcript=_render(transcript)),
        }],
        output_format=InterviewerEval,
    )
    return response.parsed_output
