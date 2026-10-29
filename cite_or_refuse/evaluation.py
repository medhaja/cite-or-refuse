"""Offline eval over the gold questions, using the same retriever, answerer and verifier as the API."""

from __future__ import annotations

from collections import Counter

from . import llm
from .faults import FAULT_TYPES, inject
from .pipeline import Pipeline
from .text import normalize_ws
from .verifier import find_quote

TARGETS = {
    "recall_at_5": (">=", 0.85),
    "quote_fidelity": ("==", 1.0),
    "unanswerable_refusal_rate": (">=", 0.8),
    "false_refusal_rate": ("<=", 0.15),
    "fault_catch_rate": (">=", 0.95),
}
# With faults injected, refusing a corrupted claim is correct even if it leaves a question unanswered,
# so the fault run is judged only on what reaches the user and on what the verifier caught.
FAULT_RUN_TARGETS = ("quote_fidelity", "fault_catch_rate")


def _passes(value: float | None, op: str, target: float) -> bool | None:
    if value is None:
        return None
    return {">=": value >= target, "<=": value <= target, "==": abs(value - target) < 1e-9}[op]


def _hits(group: dict, source_id: str, text: str) -> bool:
    return any(ev["source_id"] == source_id and normalize_ws(ev["contains"]) in normalize_ws(text)
               for ev in group["any_of"])


def _mean(xs: list[float]) -> float | None:
    return round(sum(xs) / len(xs), 4) if xs else None


def run_eval(pipeline: Pipeline, inject_faults: bool = False, fault_rate: float = 0.2, seed: int = 7) -> dict:
    corpus = pipeline.corpus
    mode = None

    # 1. Retrieve and draft for every question.
    rows = []
    for g in corpus.gold:
        retrieved = pipeline.retrieve(g["question"])
        drafted, mode = pipeline.draft(g["question"], retrieved)
        rows.append({"gold": g, "retrieved": retrieved, "drafted": drafted})

    # 2. Optionally corrupt a fixed share of all drafted claims, chosen from the seed.
    flat = [(i, j) for i, r in enumerate(rows) for j in range(len(r["drafted"]))]
    if inject_faults and flat:
        corrupted = inject(corpus, [rows[i]["drafted"][j] for i, j in flat], rate=fault_rate, seed=seed)
        for (i, j), claim in zip(flat, corrupted):
            rows[i]["drafted"][j] = claim

    # 3. Verify and score.
    recalls, precision_hits, fidelity, raw_fidelity = [], [], [], []
    answerable_refused, unanswerable_refused, coverage = [], [], []
    injected, caught, clean_refused = Counter(), Counter(), 0
    caught_by_reason = Counter()
    per_question = []
    for r in rows:
        g = r["gold"]
        shown, refused = pipeline.verify_all(r["drafted"])
        for claim in r["drafted"]:
            lines, _ = corpus.resolve(claim["citation"])
            raw_fidelity.append(bool(lines) and find_quote(lines, claim["quote"]) is not None)
        for claim in shown:
            lines, _ = corpus.resolve(claim["citation"])
            fidelity.append(bool(lines) and find_quote(lines, claim["quote"]) is not None)
        for claim in refused:
            if claim.get("fault"):
                caught[claim["fault"]] += 1
                caught_by_reason[claim["reason"]] += 1
            else:
                clean_refused += 1
        for claim in r["drafted"]:
            if claim.get("fault"):
                injected[claim["fault"]] += 1

        issues = []
        row = {"qid": g["qid"], "question": g["question"], "category": g["category"],
               "retrieved": [c["label"] for c in r["retrieved"]],
               "shown": [c["citation"]["label"] for c in shown],
               "refused": [{"citation": c["citation"].get("label"), "reason": c["reason"], "fault": c.get("fault")}
                           for c in refused]}
        if g["evidence"]:
            groups = g["evidence"]
            hit = [any(_hits(grp, c["source_id"], c["text"]) for c in r["retrieved"]) for grp in groups]
            recalls.append(sum(hit) / len(groups))
            row["recall_at_5"] = round(sum(hit) / len(groups), 3)
            if not all(hit):
                issues.append("gold evidence not in top 5")
            spans = [(c["citation"]["source_id"], " ".join(ln["text"] for ln in corpus.resolve(c["citation"])[0]))
                     for c in shown]
            claim_hits = [any(_hits(grp, sid, span) for grp in groups) for sid, span in spans]
            precision_hits += claim_hits
            covered = [any(_hits(grp, sid, span) for sid, span in spans) for grp in groups]
            coverage.append(sum(covered) / len(groups))
            answerable_refused.append(not shown)
            if not shown:
                issues.append("false refusal: nothing shown")
            elif not all(covered):
                issues.append("shown claims miss part of the gold evidence")
            if shown and not all(claim_hits):
                issues.append(f"{claim_hits.count(False)} shown claim(s) cite non-gold spans")
        else:
            unanswerable_refused.append(not shown)
            if shown:
                issues.append("answered an unanswerable question")
        row["issues"] = issues
        per_question.append(row)

    metrics = {
        "recall_at_5": _mean(recalls),
        "citation_precision": _mean(precision_hits),
        "evidence_coverage": _mean(coverage),
        "quote_fidelity": _mean(fidelity) if fidelity else 1.0,
        "raw_quote_fidelity": _mean(raw_fidelity),
        "unanswerable_refusal_rate": _mean(unanswerable_refused),
        "false_refusal_rate": _mean(answerable_refused),
    }
    report = {
        "mode": mode,
        "judge": "llm" if llm.judge_enabled() else "lexical",
        "k": pipeline.k,
        "questions": len(rows),
        "claims_drafted": len(flat),
        "claims_shown": len(fidelity),
        "metrics": metrics,
        "fault_injection": None,
        "per_question": per_question,
        "failures": [q for q in per_question if q["issues"]],
    }
    if inject_faults:
        n_inj, n_caught = sum(injected.values()), sum(caught.values())
        metrics["fault_catch_rate"] = round(n_caught / n_inj, 4) if n_inj else None
        report["fault_injection"] = {
            "rate": fault_rate, "seed": seed, "injected": n_inj, "caught": n_caught,
            "by_type": {t: {"injected": injected[t], "caught": caught[t]} for t in FAULT_TYPES},
            "caught_by_reason": dict(caught_by_reason),
            "clean_claims_refused": clean_refused,
        }
    report["targets"] = {
        name: {"op": op, "target": target, "value": metrics.get(name), "pass": _passes(metrics.get(name), op, target)}
        for name, (op, target) in TARGETS.items()
        if name in metrics and (not inject_faults or name in FAULT_RUN_TARGETS)
    }
    return report
