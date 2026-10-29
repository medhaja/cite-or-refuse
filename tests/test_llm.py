import json

import pytest

from cite_or_refuse import llm
from cite_or_refuse.pipeline import Pipeline


@pytest.fixture()
def llm_on(monkeypatch):
    monkeypatch.setenv("COR_LLM_MODEL", "fake/model")


def _fake(monkeypatch, payload_for):
    monkeypatch.setattr(llm, "_completion", lambda prompt: payload_for(prompt))


def _line_id(prompt, contains):
    return next(line.split("]")[0][1:] for line in prompt.splitlines() if contains in line)


def test_llm_claims_are_verified_and_hallucinations_refused(corpus, llm_on, monkeypatch):
    def answer(prompt):
        good = _line_id(prompt, "Kev said he took it")
        return json.dumps({"claims": [
            {"text": "Tasha said Kev took the gold watch to Lucky's.",
             "quote": "That watch you had, the gold one, Kev said he took it to Lucky's.",
             "line_ids": [good], "speaker": "Tasha Greene"},
            {"text": "Tasha said Kev sold the watch for $900.",
             "quote": "Kev sold it for nine hundred.", "line_ids": [good], "speaker": "Tasha Greene"},
            {"text": "Tasha said Rico had the watch.", "quote": "Rico had it.", "line_ids": ["L999"]},
        ]})
    _fake(monkeypatch, answer)
    result = Pipeline(corpus).ask("Who did Tasha say had the gold watch?")
    assert result["mode"] == "llm:fake/model"
    assert [c["citation"]["source_id"] for c in result["claims"]] == ["CALL-008"]
    assert sorted(c["reason"] for c in result["refused"]) == ["bad_citation", "quote_not_found"]


def test_llm_paraphrase_with_wrong_number_is_unsupported(corpus, llm_on, monkeypatch):
    def answer(prompt):
        lid = _line_id(prompt, "$1,260")
        return json.dumps({"claims": [{"text": "About $2,000 was taken.", "line_ids": [lid],
                                       "quote": "approximately $1,260 in cash was taken"}]})
    _fake(monkeypatch, answer)
    result = Pipeline(corpus).ask("How much cash was taken from the register?")
    assert result["claims"] == [] and result["refused"][0]["reason"] == "unsupported"


def test_llm_failure_falls_back_to_mock(corpus, llm_on, monkeypatch):
    def boom(prompt):
        raise RuntimeError("no network")
    _fake(monkeypatch, boom)
    result = Pipeline(corpus).ask("Who did Tasha say had the gold watch?")
    assert result["mode"].startswith("mock (llm failed")
    assert result["claims"]


def test_llm_judge_can_refuse_but_not_rescue_a_missing_quote(corpus, llm_on, monkeypatch):
    monkeypatch.setenv("COR_LLM_JUDGE", "1")
    pipe = Pipeline(corpus)
    drafted = pipe.mock.answer("Why was the rear camera not recording?",
                               pipe.retrieve("Why was the rear camera not recording?"))
    monkeypatch.setattr(llm, "judge", lambda claim, span: (False, 0.1))
    shown, refused = pipe.verify_all(drafted)
    assert not shown and all(r["detail"].startswith("LLM judge") for r in refused)
    monkeypatch.setattr(llm, "judge", lambda claim, span: (True, 0.99))
    bad = dict(drafted[0], quote="The rear camera was unplugged by the suspect.")
    shown, refused = pipe.verify_all([bad])
    assert not shown and refused[0]["reason"] == "quote_not_found"
