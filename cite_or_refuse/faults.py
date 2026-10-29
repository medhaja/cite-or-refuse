"""Fault injection: corrupt drafted claims the way a careless model would, so we can measure the verifier."""

from __future__ import annotations

import copy
import random

from .corpus import Corpus, citation_label
from .text import normalize_ws

FAULT_TYPES = ("wrong_timestamp", "altered_quote", "swapped_speaker")
_SWAP_WORDS = ["blue", "Tuesday", "never", "seven", "basement", "Marcus", "truck", "left"]


def _wrong_location(corpus: Corpus, claim: dict, rng: random.Random) -> dict:
    c = claim["citation"]
    if c["source_type"] == "call":
        duration = corpus.calls[c["source_id"]]["duration"]
        if rng.random() < 0.5:
            # Point past the end of the call.
            c["start_ts"], c["end_ts"] = duration + 5, duration + 25
        else:
            # Point at a different line of the same call.
            others = [u for u in corpus.call_units(c["source_id"])
                      if normalize_ws(claim["quote"]) not in normalize_ws(u["text"])]
            u = rng.choice(others)
            c["start_ts"], c["end_ts"] = u["start_ts"], u["end_ts"]
    else:
        pages = corpus.docs[c["source_id"]]["pages"]
        if rng.random() < 0.5:
            c["page"] = len(pages) + 1
        else:
            others = [u for u in corpus.doc_units(c["source_id"])
                      if normalize_ws(claim["quote"]) not in normalize_ws(u["text"])]
            u = rng.choice(others)
            c["page"], c["line_start"], c["line_end"] = u["page"], u["line"], u["line"]
    return claim


def _alter_quote(claim: dict, rng: random.Random) -> dict:
    words = claim["quote"].split()
    idx = [i for i, w in enumerate(words) if len(w.strip(".,!?\"'")) > 3] or list(range(len(words)))
    i = rng.choice(idx)
    replacement = rng.choice([w for w in _SWAP_WORDS if w.lower() != words[i].lower()])
    original = claim["quote"]
    words[i] = replacement
    claim["quote"] = " ".join(words)
    claim["text"] = claim["text"].replace(original, claim["quote"])
    return claim


def _swap_speaker(corpus: Corpus, claim: dict, rng: random.Random) -> dict:
    c = claim["citation"]
    if c["source_type"] == "call":
        pool = [p for p in corpus.calls[c["source_id"]]["participants"] if p != c["speaker"]]
    else:
        pool = sorted({d["speaker"] for d in corpus.docs.values()} - {c["speaker"]})
    new = rng.choice(pool)
    claim["text"] = claim["text"].replace(c["speaker"], new, 1)
    c["speaker"] = new
    return claim


def corrupt(corpus: Corpus, claim: dict, fault: str, rng: random.Random) -> dict:
    claim = copy.deepcopy(claim)
    if fault == "wrong_timestamp":
        claim = _wrong_location(corpus, claim, rng)
    elif fault == "altered_quote":
        claim = _alter_quote(claim, rng)
    elif fault == "swapped_speaker":
        claim = _swap_speaker(corpus, claim, rng)
    else:
        raise ValueError(fault)
    claim["citation"]["label"] = citation_label(claim["citation"])
    claim["fault"] = fault
    return claim


def inject(corpus: Corpus, claims: list[dict], rate: float = 0.2, seed: int = 7) -> list[dict]:
    """Corrupt round(rate * N) of the claims, chosen and corrupted deterministically from the seed."""
    rng = random.Random(seed)
    n = round(rate * len(claims))
    chosen = sorted(rng.sample(range(len(claims)), n)) if claims else []
    first = rng.randrange(len(FAULT_TYPES))
    out = list(claims)
    for k, i in enumerate(chosen):
        out[i] = corrupt(corpus, claims[i], FAULT_TYPES[(first + k) % len(FAULT_TYPES)], rng)
    return out
