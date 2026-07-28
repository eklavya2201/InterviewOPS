"""Test setup: isolated SQLite DB + forced demo mode so tests never spend API tokens."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="interviewops-test-"), "test.db")
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest
from fastapi.testclient import TestClient

from app import evals, interviewer
from app.main import app

# load_dotenv() in app.main may re-read a local .env with a real key — override it.
interviewer.MOCK = True
evals.MOCK = True


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture()
def finished_session(client):
    """Start a session and answer all 6 questions so it is ready for grading."""
    start = client.post("/api/session/start", json={"role": "ai-engineer", "difficulty": "fresher"}).json()
    sid = start["session_id"]
    for i in range(6):
        resp = client.post(f"/api/session/{sid}/answer", json={"answer": f"My answer to question {i + 1}."})
        assert resp.status_code == 200
        last = resp.json()
    assert last["done"] is True
    return sid
