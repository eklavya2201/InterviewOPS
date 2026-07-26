# Google Stitch UI prompt for InterviewOps

Paste the prompt below into Stitch (stitch.withgoogle.com). Generate screen by screen if it truncates — the per-screen prompts are at the bottom.

---

## Main prompt

Design a modern web app called "InterviewOps" — an AI mock-interview platform for AI/ML/data-science students. Dark theme: near-black background (#0B0E14), soft white text, one electric accent color (#6EE7B7 mint-green) used sparingly for CTAs, scores, and the live "recording" indicator. Typography: a distinctive geometric sans for headings (e.g. Space Grotesk), clean sans for body. Rounded 16px cards, subtle 1px borders (#1F2430), gentle glass-blur on elevated panels. No purple gradients, no generic AI clichés.

The app has 4 screens:

1. **Setup screen** — centered card titled "Start your mock interview". Fields: role selector as 4 pill-style radio cards (AI Engineer, ML Engineer, Data Scientist, Data Analyst) each with a small icon; difficulty segmented control (Intern / Fresher / Mid-level); optional textarea "Paste your resume (optional)"; large primary button "Begin interview". Top nav: logo "InterviewOps" left, links "History" and "About" right.

2. **Interview screen** — chat-style layout, single column max-width 720px. Interviewer messages left-aligned in bordered cards with a small robot avatar and "Interviewer" label; a progress indicator top-right showing "Question 3 of 6" as a thin segmented progress bar in the accent color. Bottom: fixed answer composer with a large textarea, a microphone button (voice input) with a pulsing accent ring when active, and a "Submit answer" button. Show a subtle "Interviewer is thinking…" shimmer state on the latest card.

3. **Report screen** — headline row: big circular score dial (e.g. 72/100) in accent color, next to a "Hire signal: LEAN YES" chip and a 2-line summary. Below: vertical list of per-question cards, each with question text, a 0-10 score bar, collapsible sections "Strengths", "Gaps", "Ideal answer outline". Right sidebar (stacks on mobile): "Top strengths" and "Top improvements" as bullet cards, plus a secondary card "Interviewer self-audit" with 4 mini score rows (Follow-up quality, Question relevance, Difficulty calibration, Factual accuracy) each 0-10 — this card has a small "beta" tag.

4. **History screen** — table/list of past interviews: date, role, difficulty, score dial (small), hire-signal chip, "View report" link. Empty state with a friendly illustration and "No interviews yet — start your first one".

Fully responsive; mobile shows the interview screen as a full-height chat. Buttons and inputs have visible focus states. Keep the overall feel: serious developer tool, not a toy.

---

## Per-screen prompts (if Stitch truncates)

- "Screen 1 of InterviewOps (see style above): the Setup screen only — …" (copy bullet 1)
- Repeat for screens 2–4.

## After generating

Export the design as React/HTML from Stitch and drop it into `frontend/`. The backend endpoints it must call are documented in the main README (start / answer / report / meta-eval).
