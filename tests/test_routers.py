from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_backend():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["llm_backend"] in {"mock", "claude"}


def test_enrich_endpoint_returns_prospects():
    r = client.post(
        "/v1/prospects/enrich",
        json={"companies": [{"domain": "acme.com", "name": "Acme"}]},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["prospects"]) == 1
    p = body["prospects"][0]
    assert p["company"]["domain"] == "acme.com"
    assert p["sources"]
    assert p["signals"]


def test_draft_endpoint_returns_grounded_draft():
    enrich = client.post(
        "/v1/prospects/enrich",
        json={"companies": [{"domain": "acme.com"}]},
    ).json()
    prospect = enrich["prospects"][0]
    r = client.post(
        "/v1/outreach/draft",
        json={
            "prospect": prospect,
            "tone": "consultative",
            "seller_context": "Bid shading platform that cuts CPMs ~15%",
        },
    )
    assert r.status_code == 200
    draft = r.json()["draft"]
    assert draft["subject"]
    assert draft["body"]
    for i in draft["cited_signal_indices"]:
        assert 0 <= i < len(prospect["signals"])


def test_evals_latest_returns_404_when_no_runs(tmp_path, monkeypatch):
    # The endpoint should 404 cleanly if no eval has been run yet.
    from app.routers import evals as evals_module

    monkeypatch.setattr(evals_module, "_RESULTS_DIR", tmp_path / "empty")
    r = client.get("/v1/evals/latest")
    assert r.status_code == 404
