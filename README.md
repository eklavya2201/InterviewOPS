# InterviewOps 🎙️

**An AI mock-interviewer that grades itself.** Practice a realistic technical screen for AI/ML/DS roles — then get two reports: one scoring *you*, and one where an LLM-as-judge audits the *interviewer's own performance* (follow-up quality, difficulty calibration, hallucinations).

> Most AI interview tools stop at "ask questions." InterviewOps ships a built-in eval pipeline — the same discipline production AI teams use — so every interview doubles as a benchmark run.

![Demo](docs/demo.gif)

## Two modes: free demo vs real AI

The app runs in one of two modes, decided by a single environment variable — **no code changes**:

| | Demo mode (default) | Real mode |
|---|---|---|
| Trigger | `ANTHROPIC_API_KEY` **not set** | `ANTHROPIC_API_KEY` set in `backend/.env` (or Render env vars) |
| Questions | 6 realistic canned AI/DS questions | Claude asks adaptive questions, probes weak answers, escalates on strong ones |
| Report | Placeholder layout demo (marked `[Mock]`) | Real LLM-as-judge grading with evidence from your answers |
| Cost | **₹0 — zero API calls** | Pay-per-interview (a few rupees per full session) |
| UI signal | Amber "Demo mode" banner on the setup screen | No banner |

**Why:** the deployed site can stay up 24/7 at zero cost. When showcasing the project live (an interview, a demo call), add the API key for that hour, run a real interview, then remove the key — costs stay near zero while the portfolio link always works.

## Architecture

```
Frontend (Stitch design → light theme, vanilla JS)
        │  same-origin REST (served by FastAPI StaticFiles)
        ▼
FastAPI backend ──► Interview Agent (Claude, adaptive follow-ups)
        │
        ├─► Candidate Report  — per-question 0-10 scores, hire signal, ideal-answer outlines
        └─► Meta-Eval         — LLM-as-judge audits the interviewer itself
```

## Run locally

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000** — the full app (UI + API) runs on one port. It starts in demo mode; create `backend/.env` with `ANTHROPIC_API_KEY=sk-ant-...` to switch to real AI interviews (template in `.env.example`).

Interactive API docs: http://localhost:8000/docs

## Deploy (Render, free tier)

The repo ships a `render.yaml` blueprint:

1. Go to [render.com](https://render.com) → **New → Blueprint** → connect `eklavya2201/interviewops`
2. Render reads `render.yaml` and creates the web service automatically — deploy
3. Done. The site runs in free demo mode with zero API cost.

To showcase real AI interviews: Render dashboard → the service → **Environment** → add `ANTHROPIC_API_KEY` → save (auto-redeploys in ~1 min). Remove the variable afterwards to go back to free demo mode.

> Free-tier note: Render spins the service down after 15 idle minutes; the first visit after that takes ~30s to wake. Fine for a portfolio link.

### API

| Endpoint | What it does |
|---|---|
| `POST /api/session/start` | Pick role + difficulty (optionally paste your resume) → first question |
| `POST /api/session/{id}/answer` | Submit an answer → adaptive next question (6 total) |
| `POST /api/session/{id}/report` | Structured candidate report (scores, hire signal) |
| `POST /api/session/{id}/meta-eval` | **The differentiator** — judge the AI interviewer itself |
| `GET /api/health` | `{status, mock}` — tells the UI which mode is active |

## Roadmap

- [x] FastAPI backend with adaptive interview agent
- [x] LLM-as-judge evals (candidate report + interviewer self-audit)
- [x] Frontend (Google Stitch design → light theme) wired to the API
- [x] Free demo mode (runs with zero API cost)
- [ ] Deploy on Render (blueprint ready — see above)
- [ ] Voice mode (Web Speech API mic input + spoken questions)
- [ ] Model benchmark table (Claude vs GPT vs Gemini as interviewer, scored by the meta-eval)
- [ ] Cost dashboard (tokens + ₹ per interview)
- [ ] SQLite persistence for sessions and history

## Why evals?

Eval design is the #1 skill screen for AI engineering roles in 2026. `backend/app/evals.py` implements structured LLM-as-judge scoring with Pydantic-validated outputs — the meta-eval turns this app into a harness for comparing interviewer models objectively.
