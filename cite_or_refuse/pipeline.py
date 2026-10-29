"""retrieve -> draft claims -> (optionally corrupt) -> verify -> response. Shared by the API and the eval."""

from __future__ import annotations

import time

from . import llm
from .answerer import MockAnswerer
from .corpus import Corpus
from .faults import inject
from .retriever import Retriever
from .verifier import verify

NO_ANSWER = "No traceable answer found"


class Pipeline:
    def __init__(self, corpus: Corpus | None = None, k: int = 5):
        self.corpus = corpus or Corpus.load()
        self.retriever = Retriever(self.corpus)
        self.mock = MockAnswerer(self.corpus)
        self.k = k

    def retrieve(self, query: str) -> list[dict]:
        return self.retriever.search(query, self.k)

    def draft(self, query: str, retrieved: list[dict]) -> tuple[list[dict], str]:
        """Draft claims with the LLM if one is configured, else the mock. Returns (claims, mode)."""
        if llm.enabled():
            try:
                return llm.draft_claims(query, retrieved), f"llm:{llm.model_name()}"
            except Exception as exc:  # any provider/parse failure falls back so the demo keeps working
                return self.mock.answer(query, retrieved), f"mock (llm failed: {type(exc).__name__})"
        return self.mock.answer(query, retrieved), "mock"

    def verify_all(self, claims: list[dict]) -> tuple[list[dict], list[dict]]:
        judge = llm.judge if llm.judge_enabled() else None
        results = [verify(self.corpus, c, judge) for c in claims]
        return [r for r in results if r["verdict"] == "supported"], [r for r in results if r["verdict"] == "refused"]

    def ask(self, query: str, inject_fault: bool = False, seed: int = 7) -> dict:
        """Answer a question. With inject_fault, one drafted claim is corrupted before verification (demo aid)."""
        t0 = time.perf_counter()
        retrieved = self.retrieve(query)
        drafted, mode = self.draft(query, retrieved)
        if inject_fault and drafted:
            drafted = inject(self.corpus, drafted, rate=1 / len(drafted), seed=seed)
        claims, refused = self.verify_all(drafted)
        return {
            "query": query,
            "mode": mode,
            "answer": f"{len(claims)} traceable claim{'s' if len(claims) != 1 else ''}" if claims else NO_ANSWER,
            "claims": claims,
            "refused": refused,
            "retrieved": [
                {"chunk_id": c["chunk_id"], "label": c["label"], "source_id": c["source_id"],
                 "source_type": c["source_type"], "title": c["title"], "score": c["score"],
                 **{k: c[k] for k in ("start_ts", "end_ts", "page", "line_start", "line_end")},
                 "preview": c["text"][:160]}
                for c in retrieved
            ],
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
