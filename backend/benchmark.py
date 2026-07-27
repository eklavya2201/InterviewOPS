"""Model benchmark: which model is the best interviewer, judged by the meta-eval?

For each candidate interviewer model, runs simulated interviews (a Claude-played
candidate answers the questions), then grades each transcript with the existing
LLM-as-judge meta-eval. Writes frontend/benchmark-data.json for benchmark.html.

Usage (needs ANTHROPIC_API_KEY; OPENAI_API_KEY / GEMINI_API_KEY optional):
    cd backend && python benchmark.py [--runs 2]
"""
import argparse
import datetime
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

from app import costs, interviewer
from app.evals import JUDGE_MODEL, _render, META_EVAL_PROMPT
from app.models import InterviewerEval

QUESTIONS = 6
CANDIDATE_MODEL = "claude-opus-4-8"
CANDIDATE_SYSTEM = (
    "You are role-playing a fresher-level AI engineer candidate in a mock technical screen. "
    "Answer each interviewer question in 3-6 sentences: mostly correct fundamentals, but "
    "occasionally vague or missing edge cases, like a real fresher. Never break character."
)

# (display name, provider, model id, base_url or None, api key env var)
INTERVIEWER_MODELS = [
    ("Claude Opus 4.8", "anthropic", "claude-opus-4-8", None, "ANTHROPIC_API_KEY"),
    ("GPT-4o", "openai", "gpt-4o", "https://api.openai.com/v1", "OPENAI_API_KEY"),
    ("Gemini 2.0 Flash", "gemini", "gemini-2.0-flash",
     "https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY"),
]


def anthropic_turn(system: str, messages: list[dict], model: str, usage: dict) -> str:
    resp = interviewer.get_client().messages.create(
        model=model, max_tokens=1024, system=system, messages=messages
    )
    usage["input"] += resp.usage.input_tokens
    usage["output"] += resp.usage.output_tokens
    return next(b.text for b in resp.content if b.type == "text")


def openai_compatible_turn(system: str, messages: list[dict], model: str, base_url: str, api_key: str, usage: dict) -> str:
    resp = httpx.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": [{"role": "system", "content": system}] + messages, "max_tokens": 1024},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    u = data.get("usage", {})
    usage["input"] += u.get("prompt_tokens", 0)
    usage["output"] += u.get("completion_tokens", 0)
    return data["choices"][0]["message"]["content"]


def run_interview(provider: str, model: str, base_url: str | None, api_key: str, usage: dict) -> list[dict]:
    """Simulated interview: `model` asks, Claude answers. Returns the transcript."""
    system = interviewer.build_system("ai-engineer", "fresher", "Candidate", None)
    transcript = [{"role": "user", "content": "I'm ready. Please begin the interview."}]
    cand_usage = {"input": 0, "output": 0}  # candidate tokens are overhead, not benchmarked
    for _ in range(QUESTIONS):
        if provider == "anthropic":
            question = anthropic_turn(system, transcript, model, usage)
        else:
            question = openai_compatible_turn(system, transcript, model, base_url, api_key, usage)
        transcript.append({"role": "assistant", "content": question})
        # Candidate answers (roles flipped: interviewer msgs become "user" for the candidate)
        flipped = [
            {"role": "user" if t["role"] == "assistant" else "assistant", "content": t["content"]}
            for t in transcript[1:]
        ]
        answer = anthropic_turn(CANDIDATE_SYSTEM, flipped, CANDIDATE_MODEL, cand_usage)
        transcript.append({"role": "user", "content": answer})
    return transcript


def judge(transcript: list[dict]) -> InterviewerEval:
    resp = interviewer.get_client().messages.parse(
        model=JUDGE_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": META_EVAL_PROMPT.format(transcript=_render(transcript))}],
        output_format=InterviewerEval,
    )
    return resp.parsed_output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=2, help="interviews per model")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is required (candidate simulator + judge run on Claude).")

    dims = ["followed_up_on_weak_answers", "question_relevance", "difficulty_calibration", "no_hallucinated_facts"]
    results = []
    for name, provider, model, base_url, key_env in INTERVIEWER_MODELS:
        api_key = os.getenv(key_env)
        if not api_key:
            print(f"skip {name}: {key_env} not set")
            continue
        print(f"benchmarking {name} ({args.runs} runs)...")
        usage = {"input": 0, "output": 0}
        scores = {d: 0 for d in dims}
        notes = ""
        for i in range(args.runs):
            transcript = run_interview(provider, model, base_url, api_key, usage)
            ev = judge(transcript)
            for d in dims:
                scores[d] += getattr(ev, d)
            notes = ev.notes
            print(f"  run {i + 1}: {[getattr(ev, d) for d in dims]}")
        avg = {d: round(scores[d] / args.runs, 1) for d in dims}
        results.append({
            "model": name,
            "model_id": model,
            "provider": provider,
            "runs": args.runs,
            **avg,
            "overall": round(sum(avg.values()) / len(dims), 1),
            "input_tokens": usage["input"],
            "output_tokens": usage["output"],
            "cost_inr": round(costs.cost_inr(model, usage["input"], usage["output"]), 2),
        })

    out = {
        "sample": False,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "judge_model": JUDGE_MODEL,
        "questions_per_interview": QUESTIONS,
        "results": sorted(results, key=lambda r: -r["overall"]),
    }
    out_path = Path(__file__).resolve().parents[1] / "frontend" / "benchmark-data.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
