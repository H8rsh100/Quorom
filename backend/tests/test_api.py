from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        body = res.json()
        assert body["service"] == "quorom"
        assert body["mode"] == "mock"


def test_findings_seeded_in_mock_mode():
    with TestClient(app) as client:
        res = client.get("/api/findings")
        assert res.status_code == 200
        findings = res.json()
        assert len(findings) >= 1
        assert all("explanation" in f for f in findings)
        assert all("proposed_action" in f for f in findings)
