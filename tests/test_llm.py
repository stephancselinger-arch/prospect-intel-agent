import json

from app.services.llm import (
    OUTREACH_DRAFT_SYSTEM,
    SIGNAL_EXTRACTION_SYSTEM,
    MockLLMClient,
    _extract_json,
    get_default_client,
)


def test_mock_signal_extraction_grounded_in_user_payload():
    llm = MockLLMClient()
    payload = json.dumps({
        "company": {"domain": "acme.com", "name": "Acme"},
        "sources": [
            {
                "title": "Acme raises Series C",
                "source_type": "press_release",
                "excerpt": "Acme today announced a $80M Series C round.",
            },
            {
                "title": "Acme is hiring Staff Engineers",
                "source_type": "job_posting",
                "excerpt": "We're hiring across engineering.",
            },
        ],
    })
    resp = llm.complete_json(system=SIGNAL_EXTRACTION_SYSTEM, user=payload)
    parsed = json.loads(resp.text)
    types = {s["signal_type"] for s in parsed["signals"]}
    assert "funding" in types
    assert "hiring" in types
    for s in parsed["signals"]:
        for idx in s["citation_indices"]:
            assert 0 <= idx < 2


def test_mock_outreach_cites_first_signal_when_present():
    llm = MockLLMClient()
    payload = json.dumps({
        "prospect": {
            "company": {"domain": "acme.com", "name": "Acme"},
            "signals": [{"signal_type": "funding", "claim": "Series C", "confidence": 0.9, "citation_indices": [0]}],
        },
        "tone": "consultative",
        "seller_context": "ROI platform",
    })
    resp = llm.complete_json(system=OUTREACH_DRAFT_SYSTEM, user=payload)
    parsed = json.loads(resp.text)
    assert parsed["cited_signal_indices"] == [0]
    assert "[0]" in parsed["body"]


def test_get_default_client_returns_mock_when_no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("LLM_BACKEND", "auto")
    assert get_default_client().backend_name == "mock"


def test_get_default_client_respects_explicit_mock(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_BACKEND", "mock")
    assert get_default_client().backend_name == "mock"


def test_extract_json_strips_code_fences():
    assert _extract_json("```json\n{\"a\": 1}\n```") == '{"a": 1}'


def test_extract_json_finds_object_in_prose():
    assert _extract_json("Sure, here is your JSON: {\"a\": 1} done") == '{"a": 1}'
