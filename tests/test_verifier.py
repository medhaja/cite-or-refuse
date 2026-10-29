import copy
import random

import pytest

from cite_or_refuse.corpus import citation_label, unit_citation
from cite_or_refuse.faults import FAULT_TYPES, corrupt
from cite_or_refuse.pipeline import NO_ANSWER, Pipeline
from cite_or_refuse.verifier import BAD_CITATION, QUOTE_NOT_FOUND, UNSUPPORTED, verify


@pytest.fixture(scope="module")
def pipeline(corpus):
    return Pipeline(corpus)


def _claim(corpus, source_id, contains):
    units = corpus.call_units(source_id) if source_id.startswith("CALL") else corpus.doc_units(source_id)
    unit = next(u for u in units if contains in u["text"])
    verb = "said" if unit["source_type"] == "call" else "wrote"
    return {"text": f'{unit["speaker"]} {verb}: "{unit["text"]}"', "quote": unit["text"],
            "citation": unit_citation(unit)}


def _recite(claim, **changes):
    claim = copy.deepcopy(claim)
    claim["citation"].update(changes)
    claim["citation"]["label"] = citation_label(claim["citation"])
    return claim


def test_valid_call_claim_is_supported(corpus):
    result = verify(corpus, _claim(corpus, "CALL-017", "green one"))
    assert result["verdict"] == "supported" and result["score"] >= 0.6


def test_valid_doc_claim_is_supported(corpus):
    assert verify(corpus, _claim(corpus, "DOC-04", "blue pickup"))["verdict"] == "supported"


def test_quote_matching_ignores_whitespace_only(corpus):
    claim = _claim(corpus, "DOC-01", "$1,260")
    claim["quote"] = "  Ruiz stated approximately\n $1,260   in cash  was taken from the register. "
    assert verify(corpus, claim)["verdict"] == "supported"
    claim["quote"] = "ruiz stated approximately $1,260 in cash was taken from the register."
    assert verify(corpus, claim)["reason"] == QUOTE_NOT_FOUND  # case is part of "verbatim"


def test_quote_not_in_span_is_always_refused(corpus):
    claim = _claim(corpus, "CALL-008", "Lucky's")
    claim["quote"] = claim["quote"].replace("Kev", "Rico")
    assert verify(corpus, claim)["reason"] == QUOTE_NOT_FOUND
    # A real quote from a different line of the same call is still not in the cited span.
    other = _claim(corpus, "CALL-008", "Don't talk about that")
    claim = _claim(corpus, "CALL-008", "Lucky's")
    claim["quote"] = other["quote"]
    assert verify(corpus, claim)["reason"] == QUOTE_NOT_FOUND


def test_quote_spanning_two_cited_lines_is_found(corpus):
    a, b = _claim(corpus, "CALL-017", "green one"), _claim(corpus, "CALL-017", "Why you keep")
    claim = _recite(a, end_ts=b["citation"]["end_ts"])
    claim["quote"] = "in Dunmore. Why you keep"
    assert verify(corpus, claim)["verdict"] == "supported"


@pytest.mark.parametrize("changes", [
    {"start_ts": 9000, "end_ts": 9020},  # past the end of the call
    {"start_ts": 30, "end_ts": 10},  # inverted range
    {"start_ts": -5, "end_ts": 10},
    {"source_id": "CALL-999"},
])
def test_bad_call_citation_is_always_refused(corpus, changes):
    claim = _recite(_claim(corpus, "CALL-017", "green one"), **changes)
    assert verify(corpus, claim)["reason"] == BAD_CITATION


@pytest.mark.parametrize("changes", [
    {"page": 7},
    {"line_start": 40, "line_end": 41},
    {"line_start": 0, "line_end": 3},
    {"line_start": 1, "line_end": 2},  # header lines only
    {"source_id": "DOC-99"},
])
def test_bad_doc_citation_is_always_refused(corpus, changes):
    claim = _recite(_claim(corpus, "DOC-04", "blue pickup"), **changes)
    assert verify(corpus, claim)["reason"] == BAD_CITATION


def test_swapped_speaker_is_refused(corpus):
    claim = _claim(corpus, "CALL-020", "after midnight")
    claim["citation"]["speaker"] = "Andre Whitfield"
    claim["text"] = claim["text"].replace("Loretta Whitfield", "Andre Whitfield")
    result = verify(corpus, claim)
    assert result["reason"] == UNSUPPORTED and "speaker" in result["detail"]


def test_number_or_name_not_in_span_is_refused(corpus):
    claim = _claim(corpus, "DOC-01", "$1,260")
    claim["text"] = "About $2,600 in cash was taken from the register."
    assert verify(corpus, claim)["reason"] == UNSUPPORTED
    claim["text"] = "Ruiz stated Hector Banks took the cash from the register."
    result = verify(corpus, claim)
    assert result["reason"] == UNSUPPORTED and "banks" in result["detail"]


def test_claim_that_drifts_from_span_is_refused(corpus):
    claim = _claim(corpus, "DOC-08", "failed hard drive")
    claim["text"] = "The suspect deliberately destroyed footage to hide the getaway."
    assert verify(corpus, claim)["reason"] == UNSUPPORTED


def test_every_fault_type_is_caught_on_every_drafted_claim(pipeline, corpus):
    rng = random.Random(0)
    drafted = []
    for g in corpus.gold:
        drafted += pipeline.mock.answer(g["question"], pipeline.retrieve(g["question"]))
    assert len(drafted) > 30
    for claim in drafted:
        assert verify(corpus, claim)["verdict"] == "supported"
        for fault in FAULT_TYPES:
            assert verify(corpus, corrupt(corpus, claim, fault, rng))["verdict"] == "refused", (fault, claim)


def test_unanswerable_question_gets_no_traceable_answer(pipeline):
    result = pipeline.ask("What did the victim's brother say on the jail calls?")
    assert result["claims"] == [] and result["answer"] == NO_ANSWER
    assert result["retrieved"], "should still list what was retrieved"


def test_mock_mode_is_deterministic(pipeline):
    q = "Who was the green car registered to, and what did Andre tell Rico to do with it?"
    a, b = pipeline.ask(q), pipeline.ask(q)
    a.pop("latency_ms"), b.pop("latency_ms")
    assert a == b and a["claims"]


def test_demo_fault_injection_is_refused(pipeline):
    result = pipeline.ask("What did Andre tell Rico to do with the green car?", inject_fault=True)
    assert [c for c in result["refused"] if c.get("fault")]
    assert all("fault" not in c for c in result["claims"])
