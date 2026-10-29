import json

import pytest
from fastapi.testclient import TestClient

from cite_or_refuse.app import create_app
from cite_or_refuse.pipeline import NO_ANSWER, Pipeline


@pytest.fixture()
def client(corpus, tmp_path, monkeypatch):
    monkeypatch.setenv("COR_RUNS_LOG", str(tmp_path / "runs.jsonl"))
    return TestClient(create_app(Pipeline(corpus)))


def test_ask_returns_claims_with_citations(client):
    body = client.post("/ask", json={"query": "Who did Tasha say had the gold watch?"}).json()
    assert body["claims"], body
    claim = body["claims"][0]
    assert set(claim) >= {"text", "quote", "citation", "verdict", "score"}
    assert claim["verdict"] == "supported"
    assert claim["citation"]["label"].startswith("CALL-008 @ ")
    assert body["refused"] == []


def test_ask_unanswerable(client):
    body = client.post("/ask", json={"query": "Who was the getaway driver?"}).json()
    assert body["answer"] == NO_ANSWER and body["claims"] == []


def test_ask_with_injected_fault_lists_refusal(client):
    body = client.post("/ask", json={"query": "What did Andre tell Rico to do with the green car?",
                                     "inject_fault": True}).json()
    assert len(body["refused"]) == 1
    assert body["refused"][0]["reason"] in {"bad_citation", "quote_not_found", "unsupported"}


def test_requests_are_logged(client, tmp_path):
    client.post("/ask", json={"query": "Why was the rear camera not recording?"})
    client.post("/ask", json={"query": "Who was the getaway driver?"})
    records = [json.loads(line) for line in (tmp_path / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(records) == 2
    assert set(records[0]) >= {"query", "retrieved", "claims", "refused", "latency_ms"}
    assert records[0]["claims"][0]["verdict"] == "supported"


def test_source_endpoint(client):
    call = client.get("/source/CALL-017").json()
    assert call["source_type"] == "call" and call["lines"][0]["speaker"] == "SYSTEM"
    doc = client.get("/source/doc-04").json()
    assert doc["pages"][0]["lines"]
    assert client.get("/source/CALL-999").status_code == 404


def test_index_and_case(client):
    assert client.get("/").status_code == 200
    case = client.get("/case").json()
    assert case["mode"] == "mock" and len(case["samples"]) >= 5


def test_empty_query_rejected(client):
    assert client.post("/ask", json={"query": ""}).status_code == 422
