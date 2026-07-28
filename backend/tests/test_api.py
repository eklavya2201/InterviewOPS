"""API tests — run entirely in demo mode (zero API calls), backed by a throwaway SQLite DB."""
from app import db

HIRE_SIGNALS = {"strong-no", "no", "lean-no", "lean-yes", "yes", "strong-yes"}


def test_health_reports_mock_mode(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["mock"] is True


def test_start_session_returns_opening_question(client):
    resp = client.post("/api/session/start", json={"role": "ml-engineer", "difficulty": "intern"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["session_id"]) == 12
    assert body["opening_question"]


def test_invalid_role_rejected(client):
    resp = client.post("/api/session/start", json={"role": "astronaut", "difficulty": "fresher"})
    assert resp.status_code == 422


def test_full_interview_finishes_after_six_answers(client):
    sid = client.post("/api/session/start", json={}).json()["session_id"]
    for i in range(6):
        body = client.post(f"/api/session/{sid}/answer", json={"answer": f"answer {i + 1}"}).json()
        assert body["done"] is (i == 5)
        assert body["next_question"]


def test_answer_unknown_session_is_404(client):
    resp = client.post("/api/session/doesnotexist/answer", json={"answer": "hi"})
    assert resp.status_code == 404


def test_answer_after_done_is_400(client, finished_session):
    resp = client.post(f"/api/session/{finished_session}/answer", json={"answer": "one more"})
    assert resp.status_code == 400


def test_session_survives_restart_via_db(client):
    sid = client.post("/api/session/start", json={"role": "data-analyst"}).json()["session_id"]
    session = db.get_session(sid)
    assert session is not None
    assert session["role"] == "data-analyst"
    assert session["question_number"] == 1
    assert session["done"] is False
    # transcript alternates user/assistant, starting with the candidate's "ready"
    assert [t["role"] for t in session["transcript"]] == ["user", "assistant"]


def test_report_structure(client, finished_session):
    resp = client.post(f"/api/session/{finished_session}/report")
    assert resp.status_code == 200
    report = resp.json()
    assert 0 <= report["overall_score"] <= 100
    assert report["hire_signal"] in HIRE_SIGNALS
    assert len(report["per_question"]) == 6
    for q in report["per_question"]:
        assert 0 <= q["score"] <= 10
        assert q["question"] and q["answer"]
    assert report["top_strengths"] and report["top_improvements"]


def test_meta_eval_structure(client, finished_session):
    resp = client.post(f"/api/session/{finished_session}/meta-eval")
    assert resp.status_code == 200
    meta = resp.json()
    for key in ("followed_up_on_weak_answers", "question_relevance", "difficulty_calibration", "no_hallucinated_facts"):
        assert 0 <= meta[key] <= 10
    assert meta["notes"]


def test_report_for_unknown_session_is_404(client):
    assert client.post("/api/session/nope/report").status_code == 404
    assert client.post("/api/session/nope/meta-eval").status_code == 404


def test_history_lists_graded_interviews(client, finished_session):
    client.post(f"/api/session/{finished_session}/report")
    client.post(f"/api/session/{finished_session}/meta-eval")
    history = client.get("/api/history").json()
    entry = next(h for h in history if h["id"] == finished_session)
    assert entry["role"] == "ai-engineer"
    assert entry["report"]["per_question"]
    assert entry["meta"]["notes"]


def test_ungraded_sessions_stay_out_of_history(client):
    sid = client.post("/api/session/start", json={}).json()["session_id"]
    assert sid not in {h["id"] for h in client.get("/api/history").json()}


def test_usage_summary_shape(client):
    body = client.get("/api/usage").json()
    assert body["mock"] is True
    assert body["total_input_tokens"] == 0  # demo mode makes no API calls
    assert body["total_cost_inr"] == 0
    assert body["usd_to_inr"] > 0
    assert isinstance(body["sessions"], list)


def test_frontend_served_from_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "InterviewOps" in resp.text
