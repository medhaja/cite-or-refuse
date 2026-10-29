"""Optional LLM steps, behind LiteLLM so the provider is swappable. Disabled unless COR_LLM_MODEL is set.

The model drafts claims and, with COR_LLM_JUDGE=1, judges whether a span supports a claim. It never decides
whether a quote exists or a citation is real: the verifier checks those with plain string and range logic.
The model picks lines by ID; the citation itself (timestamps, page, line numbers) is built from our metadata.
"""

from __future__ import annotations

import json
import os
import re

from .corpus import citation_label

DRAFT_PROMPT = """You answer questions about a case file using ONLY the numbered lines below.
Return JSON: {{"claims": [{{"text": "...", "quote": "...", "line_ids": ["L3"], "speaker": "..."}}]}}
Rules:
- Each claim is one short factual sentence answering part of the question.
- "quote" must be copied character for character from the cited lines.
- "line_ids" lists the line(s) the quote comes from (consecutive lines of one source only).
- "speaker" is the speaker shown on that line.
- At most 3 claims. If the lines do not answer the question, return {{"claims": []}}.

Question: {question}

Lines:
{lines}
"""

JUDGE_PROMPT = """Does the SPAN support the CLAIM? Paraphrase is fine; added facts are not.
Return JSON: {{"supported": true|false, "confidence": 0.0-1.0}}

CLAIM: {claim}
SPAN: {span}
"""


def model_name() -> str:
    return os.environ.get("COR_LLM_MODEL", "").strip()


def enabled() -> bool:
    return bool(model_name())


def judge_enabled() -> bool:
    return enabled() and os.environ.get("COR_LLM_JUDGE", "").strip().lower() in {"1", "true", "yes"}


def _completion(prompt: str) -> str:
    import litellm  # optional dependency: pip install -r requirements-llm.txt

    resp = litellm.completion(model=model_name(), messages=[{"role": "user", "content": prompt}],
                              temperature=0, max_tokens=800, timeout=30)
    return resp.choices[0].message.content or ""


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("model did not return JSON")
    return json.loads(match.group(0))


def number_lines(retrieved: list[dict]) -> tuple[str, dict[str, dict]]:
    table, rows, seen = {}, [], set()
    for chunk in retrieved:
        for unit in chunk["units"]:
            key = (unit["source_id"], unit.get("start_ts"), unit.get("page"), unit.get("line"))
            if key in seen:
                continue
            seen.add(key)
            lid = f"L{len(table) + 1}"
            table[lid] = unit
            rows.append(f"[{lid}] {unit['source_id']} | {unit['speaker']} | {unit['text']}")
    return "\n".join(rows), table


def citation_for(line_ids: list[str], table: dict[str, dict], speaker: str | None) -> dict:
    units = [table[i] for i in line_ids if i in table]
    if not units or len({u["source_id"] for u in units}) != 1:
        # Unknown or mixed line IDs: keep the claim so the verifier refuses it visibly.
        c = {"source_type": "unknown", "source_id": "UNRESOLVED", "speaker": speaker}
        c["label"] = f"unresolved {','.join(line_ids) or 'citation'}"
        return c
    first = units[0]
    if first["source_type"] == "call":
        c = {"source_type": "call", "source_id": first["source_id"], "start_ts": min(u["start_ts"] for u in units),
             "end_ts": max(u["end_ts"] for u in units)}
    else:
        c = {"source_type": "doc", "source_id": first["source_id"], "page": first["page"],
             "line_start": min(u["line"] for u in units), "line_end": max(u["line"] for u in units)}
    c["speaker"] = speaker or first["speaker"]
    c["label"] = citation_label(c)
    return c


def draft_claims(query: str, retrieved: list[dict]) -> list[dict]:
    if not retrieved:
        return []
    lines, table = number_lines(retrieved)
    data = _parse_json(_completion(DRAFT_PROMPT.format(question=query, lines=lines)))
    claims = []
    for item in data.get("claims", [])[:3]:
        ids = [str(i) for i in item.get("line_ids", [])]
        claims.append({
            "text": str(item.get("text", "")),
            "quote": str(item.get("quote", "")),
            "citation": citation_for(ids, table, item.get("speaker")),
        })
    return claims


def judge(claim_text: str, span_text: str) -> tuple[bool, float]:
    data = _parse_json(_completion(JUDGE_PROMPT.format(claim=claim_text, span=span_text)))
    return bool(data.get("supported")), float(data.get("confidence", 0.0))
