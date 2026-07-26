# InterviewOps 🎙️

**An AI mock-interviewer that grades itself.** Practice a realistic technical screen for AI/ML/DS roles — then get two reports: one scoring *you*, and one where an LLM-as-judge audits the *interviewer's own performance* (follow-up quality, difficulty calibration, hallucinations).

> Most AI interview tools stop at "ask questions." InterviewOps ships a built-in eval pipeline — the same discipline production AI teams use — so every interview doubles as a benchmark run.

<!-- TODO: demo GIF here -->

## Architecture

```
Stitch-designed UI (React)
        │  REST
        ▼
FastAPI backend ──► Interview Agent (Claude, adaptive follow-ups)
        │
        ├─► Candidate Report  — per-question 0-10 scores, hire signal, ideal-answer outlines
        └─► Meta-Eval         — LLM-as-judge audits the interviewer itself
```

## Quickstart

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env                            # add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

### API

| Endpoint | What it does |
|---|---|
| `POST /api/session/start` | Pick role + difficulty (optionally paste your resume) → first question |
| `POST /api/session/{id}/answer` | Submit an answer → adaptive next question (max 6) |
| `POST /api/session/{id}/report` | Structured candidate report (scores, hire signal) |
| `POST /api/session/{id}/meta-eval` | **The differentiator** — judge the AI interviewer itself |

## Roadmap

- [ ] Frontend (Google Stitch design → React)
- [ ] Voice mode (browser Web Speech API → Whisper)
- [ ] Model benchmark table (Claude vs GPT vs Gemini as interviewer, scored by the meta-eval)
- [ ] Cost dashboard (tokens + ₹ per interview)
- [ ] Deploy: Vercel (frontend) + Render (backend)

## Why evals?

Eval design is the #1 skill screen for AI engineering roles in 2026. `evals.py` implements structured LLM-as-judge scoring with Pydantic-validated outputs — the meta-eval turns this app into a harness for comparing interviewer models objectively.
