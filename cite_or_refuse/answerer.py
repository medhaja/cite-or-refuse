"""Answerers turn retrieved chunks into claims, each with a verbatim quote and a citation.

The mock answerer is extractive and deterministic: it scores every retrieved line by how much of the question's
(IDF-weighted) vocabulary it covers and quotes the best ones. It never writes a word that isn't in the record.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .corpus import Corpus, unit_citation
from .text import tokenize


def split_question(query: str) -> list[str]:
    parts = [p.strip(" ?") for p in re.split(r",\s*and\s+|;\s*", query)]
    parts = [p for p in parts if tokenize(p)]
    return parts or [query]


def people_in(text: str, people: dict[str, list[str]]) -> set[str]:
    low = text.lower()
    found = set()
    for name, aliases in people.items():
        for alias in aliases + [name.lower()]:
            if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", low):
                found.add(name)
                break
    return found


class MockAnswerer:
    name = "mock"

    def __init__(self, corpus: Corpus, threshold: float = 0.55, relative: float = 0.7, max_claims: int = 3):
        self.corpus = corpus
        self.threshold, self.relative, self.max_claims = threshold, relative, max_claims
        units = [u for cid in corpus.calls for u in corpus.call_units(cid)]
        units += [u for did in corpus.docs for u in corpus.doc_units(did)]
        df = Counter(t for u in units for t in set(self._unit_tokens(u)))
        self._n, self._df = len(units), df

    def _unit_tokens(self, unit: dict) -> list[str]:
        title = self.corpus.docs[unit["source_id"]]["title"] if unit["source_type"] == "doc" else ""
        return tokenize(f"{unit['text']} {unit['speaker']} {title}")

    def idf(self, term: str) -> float:
        return math.log((self._n + 1) / (self._df.get(term, 0) + 1)) + 1.0

    def coverage(self, query_terms: set[str], unit: dict) -> float:
        total = sum(self.idf(t) for t in query_terms)
        if not total:
            return 0.0
        hit = query_terms & set(self._unit_tokens(unit))
        return sum(self.idf(t) for t in hit) / total

    def answer(self, query: str, retrieved: list[dict]) -> list[dict]:
        """Answer each part of a compound question ("..., and ...") separately, then merge."""
        parts = split_question(query)
        if len(parts) == 1:
            return self._answer_part(query, retrieved, self.max_claims)
        claims, seen = [], set()
        for part in parts:
            for claim in self._answer_part(part, retrieved, max(1, self.max_claims // len(parts) + 1)):
                if claim["citation"]["label"] not in seen:
                    seen.add(claim["citation"]["label"])
                    claims.append(claim)
        return claims

    def _answer_part(self, query: str, retrieved: list[dict], max_claims: int) -> list[dict]:
        terms = set(tokenize(query))
        named = people_in(query, self.corpus.people)
        seen, scored = set(), []
        for rank, chunk in enumerate(retrieved):
            for unit in chunk["units"]:
                cite = unit_citation(unit)
                if cite["label"] in seen:
                    continue
                seen.add(cite["label"])
                # "What did Tasha say..." should only quote lines spoken by, or about, the people named.
                if named and unit["speaker"] not in named and not (people_in(unit["text"], self.corpus.people) & named):
                    continue
                cov = self.coverage(terms, unit)
                if cov >= self.threshold:
                    scored.append((cov, rank, unit, cite))
        if not scored:
            return []
        scored.sort(key=lambda s: (-s[0], s[1], s[3]["label"]))
        best = scored[0][0]
        claims = []
        for cov, _, unit, cite in scored:
            if cov < best * self.relative or len(claims) == max_claims:
                break
            verb = "said" if unit["source_type"] == "call" else "wrote"
            claims.append({
                "text": f'{unit["speaker"]} {verb}: "{unit["text"]}"',
                "quote": unit["text"],
                "citation": cite,
                "relevance": round(cov, 3),
            })
        return claims
