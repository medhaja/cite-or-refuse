"""Small, deterministic text helpers shared by retrieval, answering and verification."""

from __future__ import annotations

import re

_QUOTE_MAP = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})
_TOKEN_RE = re.compile(r"\$?\d+(?:[/:.,]\d+)*(?:mm)?|[a-z]+(?:'[a-z]+)?")

STOPWORDS = frozenset(
    """a about after again all am an and any anything are as at be been before being but by can could did do does
    doing don't for from had has have he her here him his how i if in into is it it's its just me my no not of on
    or our out over own say said says saying she so some than that the their them then there these they this those
    through to too told tell up us was we were what when where which who whom why will with would you your
    according state stated states statement write writes wrote""".split()
)


def normalize_ws(text: str) -> str:
    """Whitespace and typographic-quote normalization. Case is preserved: quotes must match verbatim."""
    return " ".join(text.translate(_QUOTE_MAP).split())


def _stem(tok: str) -> str:
    if tok.endswith("'s"):
        tok = tok[:-2]
    if tok[0].isdigit() or tok[0] == "$":
        return tok.replace(",", "").lstrip("$")
    for suffix in ("ing", "ed"):
        if tok.endswith(suffix) and len(tok) > len(suffix) + 3:
            return tok[: -len(suffix)]
    if tok.endswith("s") and not tok.endswith("ss") and len(tok) > 3:
        return tok[:-1]
    return tok


def tokenize(text: str, keep_stopwords: bool = False) -> list[str]:
    toks = _TOKEN_RE.findall(normalize_ws(text).lower())
    if keep_stopwords:
        return [_stem(t) for t in toks]
    stems = (_stem(t) for t in toks if t not in STOPWORDS)
    return [t for t in stems if t not in STOPWORDS]


def numbers(text: str) -> set[str]:
    """Numbers, amounts, times and dates in a string, normalized (1,260 -> 1260, $150 -> 150)."""
    return {t.replace(",", "").lstrip("$") for t in re.findall(r"\$?\d+(?:[/:.,]\d+)*", normalize_ws(text))}


def capitalized_words(text: str) -> set[str]:
    """Capitalized words that are not sentence-initial: a cheap proxy for names and places."""
    out = set()
    for sentence in re.split(r"(?<=[.!?:])\s+|\"", normalize_ws(text)):
        words = re.findall(r"[A-Za-z][A-Za-z'.]*", sentence)
        for w in words[1:]:
            if w[0].isupper():
                w = w.rstrip(".")
                if w.endswith("'s"):
                    w = w[:-2]
                if w.lower() not in STOPWORDS and len(w) > 1:
                    out.add(w.lower())
    return out


def fmt_ts(seconds: int) -> str:
    return f"{seconds // 60:02d}:{seconds % 60:02d}"
