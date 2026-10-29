"""The verifier. Plain code decides whether a citation exists and whether a quote is in it; nothing else does.

Checks run in order and the first failure wins:
  1. bad_citation     the cited call/timestamp range or doc/page/lines does not exist
  2. quote_not_found  the quote is not verbatim (after whitespace normalization) inside the cited span
  3. unsupported      the cited speaker didn't say it, a number or name in the claim isn't in the span,
                      or the claim's wording doesn't overlap the span enough (or an optional LLM judge says no)
"""

from __future__ import annotations

from typing import Callable

from .corpus import Corpus
from .text import capitalized_words, normalize_ws, numbers, tokenize

BAD_CITATION, QUOTE_NOT_FOUND, UNSUPPORTED = "bad_citation", "quote_not_found", "unsupported"
SUPPORT_THRESHOLD = 0.6

# judge(claim_text, span_text) -> (supported, score)
Judge = Callable[[str, str], tuple[bool, float]]


def _refuse(claim: dict, reason: str, detail: str, score: float = 0.0) -> dict:
    return dict(claim, verdict="refused", reason=reason, detail=detail, score=round(score, 3))


def find_quote(lines: list[dict], quote: str) -> list[dict] | None:
    """Return the span lines the quote falls in, or None if it is not verbatim in the span."""
    q = normalize_ws(quote)
    if not q:
        return None
    parts, offsets, pos = [], [], 0
    for ln in lines:
        t = normalize_ws(ln["text"])
        parts.append(t)
        offsets.append((pos, pos + len(t)))
        pos += len(t) + 1
    joined = " ".join(parts)
    at = joined.find(q)
    if at < 0:
        return None
    end = at + len(q)
    return [ln for ln, (a, b) in zip(lines, offsets) if a < end and b > at]


def verify(corpus: Corpus, claim: dict, judge: Judge | None = None) -> dict:
    citation = claim.get("citation") or {}
    lines, why = corpus.resolve(citation)
    if lines is None:
        return _refuse(claim, BAD_CITATION, why)

    quoted_lines = find_quote(lines, claim.get("quote", ""))
    if quoted_lines is None:
        return _refuse(claim, QUOTE_NOT_FOUND, f"quote is not verbatim in {citation.get('label', 'the cited span')}")

    speakers = list(dict.fromkeys(ln["speaker"] for ln in quoted_lines))
    cited = citation.get("speaker")
    if cited and cited not in speakers:
        return _refuse(claim, UNSUPPORTED, f"cited speaker is {cited} but the quote is from {', '.join(speakers)}")

    span_text = " ".join(ln["text"] for ln in lines)
    aliases = " ".join(a for s in speakers for a in corpus.people.get(s, []))
    vocab_text = f"{span_text} {' '.join(speakers)} {aliases}"
    claim_text = claim.get("text", "")

    missing_numbers = numbers(claim_text) - numbers(span_text)
    if missing_numbers:
        return _refuse(claim, UNSUPPORTED, f"number/date not in span: {', '.join(sorted(missing_numbers))}")
    vocab = set(tokenize(vocab_text, keep_stopwords=True))
    missing_names = {w for w in capitalized_words(claim_text) if not set(tokenize(w, keep_stopwords=True)) <= vocab}
    if missing_names:
        return _refuse(claim, UNSUPPORTED, f"name not in span: {', '.join(sorted(missing_names))}")

    terms = set(tokenize(claim_text))
    overlap = len(terms & set(tokenize(vocab_text))) / len(terms) if terms else 0.0
    if judge is not None:
        try:
            ok, score = judge(claim_text, span_text)
        except Exception:  # judge unavailable: fall through to the lexical check
            ok = None
        if ok is False:
            return _refuse(claim, UNSUPPORTED, "LLM judge: span does not support the claim", score)
        if ok:
            return dict(claim, verdict="supported", reason=None, detail="LLM judge", score=round(score, 3))
    if overlap < SUPPORT_THRESHOLD:
        return _refuse(claim, UNSUPPORTED, f"lexical overlap {overlap:.2f} < {SUPPORT_THRESHOLD}", overlap)
    return dict(claim, verdict="supported", reason=None, detail="", score=round(overlap, 3))
