"""Optional LLM steps. Disabled unless COR_LLM_MODEL is set."""

from __future__ import annotations

import os


def model_name() -> str:
    return os.environ.get("COR_LLM_MODEL", "").strip()


def enabled() -> bool:
    return bool(model_name())


def judge_enabled() -> bool:
    return enabled() and os.environ.get("COR_LLM_JUDGE", "").strip() in {"1", "true", "yes"}


def draft_claims(query: str, retrieved: list[dict]) -> list[dict]:
    raise NotImplementedError


def judge(claim_text: str, span_text: str) -> tuple[bool, float]:
    raise NotImplementedError
