"""BM25 retrieval over chunks. Deterministic and free; dense embeddings are a possible later addition."""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from .corpus import Corpus
from .text import tokenize

_CALL_HINT = re.compile(r"\b(on|in|during) (the |a |his |her )?(jail |phone )?calls?\b|\bjail calls?\b", re.I)
_DOC_HINT = re.compile(r"\b(report|statements?|log|records?|lab|files?|documents?)\b", re.I)


def source_filter(query: str) -> str | None:
    """'call' or 'doc' when the question names a source type ("on the calls", "the incident report")."""
    wants_call, wants_doc = bool(_CALL_HINT.search(query)), bool(_DOC_HINT.search(query))
    if wants_call and not wants_doc:
        return "call"
    if wants_doc and not wants_call:
        return "doc"
    return None


def chunk_tokens(chunk: dict) -> list[str]:
    return tokenize(f"{chunk['text']} {chunk['speaker']} {chunk['title']}")


class Retriever:
    def __init__(self, corpus: Corpus):
        self.corpus = corpus
        self.chunks = corpus.chunks
        self.bm25 = BM25Okapi([chunk_tokens(c) for c in self.chunks])

    def search(self, query: str, k: int = 5) -> list[dict]:
        q = tokenize(query)
        if not q:
            return []
        wanted = source_filter(query)
        scores = self.bm25.get_scores(q)
        order = sorted(range(len(self.chunks)), key=lambda i: (-scores[i], i))
        results = []
        for i in order:
            chunk = self.chunks[i]
            if wanted and chunk["source_type"] != wanted:
                continue
            if scores[i] <= 0:
                break
            results.append(dict(chunk, score=round(float(scores[i]), 4)))
            if len(results) == k:
                break
        return results
