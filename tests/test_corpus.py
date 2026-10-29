import json

from cite_or_refuse import generator
from cite_or_refuse.corpus import citation_label
from cite_or_refuse.retriever import source_filter


def test_generator_is_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    generator.write(a)
    generator.write(b)
    for name in ("case.json", "calls.json", "case_files.json", "gold_questions.json"):
        assert (a / name).read_bytes() == (b / name).read_bytes()


def test_committed_data_matches_generator():
    for name, payload in generator.generate().items():
        committed = json.loads((generator.DATA_DIR / name).read_text(encoding="utf-8"))
        assert committed == json.loads(json.dumps(payload)), f"{name} is stale, rerun the generator"


def test_dataset_shape(corpus):
    assert len(corpus.calls) == 40
    assert len(corpus.docs) == 15
    assert len(corpus.gold) == 30
    cats = [g["category"] for g in corpus.gold]
    assert cats.count("answerable") == 20 and cats.count("multi_source") == 5 and cats.count("unanswerable") == 5
    for call in corpus.calls.values():
        assert 120 <= call["duration"] <= 400
        assert 2 <= len(call["participants"]) <= 3


def test_chunks_carry_citation_metadata(corpus):
    for chunk in corpus.chunks:
        for key in ("source_type", "source_id", "speaker", "text"):
            assert chunk[key]
        if chunk["source_type"] == "call":
            assert chunk["start_ts"] is not None and chunk["end_ts"] >= chunk["start_ts"]
        else:
            assert chunk["page"] >= 1 and chunk["line_end"] >= chunk["line_start"] >= 1
        lines, reason = corpus.resolve(chunk)
        assert lines, reason


def test_citation_labels():
    assert citation_label({"source_type": "call", "source_id": "CALL-017", "start_ts": 192, "end_ts": 211}) \
        == "CALL-017 @ 03:12-03:31"
    assert citation_label({"source_type": "doc", "source_id": "DOC-04", "page": 2, "line_start": 14,
                           "line_end": 19}) == "DOC-04 p.2 L14-19"


def test_gold_evidence_exists_in_sources(corpus):
    for g in corpus.gold:
        for group in g["evidence"]:
            for ev in group["any_of"]:
                units = corpus.call_units(ev["source_id"]) if ev["source_id"].startswith("CALL") \
                    else corpus.doc_units(ev["source_id"])
                assert any(ev["contains"] in u["text"] for u in units), (g["qid"], ev)


def test_source_filter():
    assert source_filter("What did Kevin say on the calls?") == "call"
    assert source_filter("What does the incident report say?") == "doc"
    assert source_filter("What time did dispatch receive the 911 call?") is None


def test_retrieval_finds_planted_line(retriever):
    labels = [c["source_id"] for c in retriever.search("Who was the green Honda Accord registered to?")]
    assert "DOC-09" in labels
