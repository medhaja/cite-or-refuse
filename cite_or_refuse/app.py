"""FastAPI app: the /ask and /source endpoints, eval reports, request logging, and the static UI."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import llm
from .pipeline import Pipeline

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
REPORTS = {"clean": ROOT / "eval_report.json", "faults": ROOT / "eval_report_faults.json"}
SAMPLE_QIDS = ["Q01", "Q02", "Q10", "Q13", "Q16", "Q22", "Q24", "Q26"]


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    inject_fault: bool = False


def _log_path() -> Path:
    return Path(os.environ.get("COR_RUNS_LOG", ROOT / "runs.jsonl"))


def create_app(pipeline: Pipeline | None = None) -> FastAPI:
    pipe = pipeline or Pipeline()
    lock = threading.Lock()
    app = FastAPI(title="Cite or Refuse", docs_url="/api/docs")

    def log_run(result: dict, inject_fault: bool) -> None:
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "query": result["query"],
            "mode": result["mode"],
            "inject_fault": inject_fault,
            "retrieved": [r["chunk_id"] for r in result["retrieved"]],
            "claims": [{"citation": c["citation"]["label"], "quote": c["quote"], "verdict": c["verdict"],
                        "score": c["score"]} for c in result["claims"]],
            "refused": [{"citation": c["citation"].get("label"), "quote": c.get("quote"), "reason": c["reason"],
                         "detail": c["detail"], "fault": c.get("fault")} for c in result["refused"]],
            "latency_ms": result["latency_ms"],
        }
        with lock, _log_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC / "index.html")

    @app.post("/ask")
    def ask(req: AskRequest) -> dict:
        result = pipe.ask(req.query.strip(), inject_fault=req.inject_fault)
        log_run(result, req.inject_fault)
        return result

    @app.get("/source/{source_id}")
    def source(source_id: str) -> dict:
        view = pipe.corpus.source_view(source_id.upper())
        if view is None:
            raise HTTPException(404, f"No source {source_id}")
        return view

    @app.get("/sources")
    def sources() -> list[dict]:
        return [{"source_id": sid, "title": pipe.corpus.title(sid)} for sid in [*pipe.corpus.calls, *pipe.corpus.docs]]

    @app.get("/case")
    def case() -> dict:
        gold = {g["qid"]: g["question"] for g in pipe.corpus.gold}
        meta = {k: v for k, v in pipe.corpus.case.items() if k != "people"}
        mode = f"llm:{llm.model_name()}" if llm.enabled() else "mock"
        return dict(meta, samples=[gold[q] for q in SAMPLE_QIDS], mode=mode, judge=llm.judge_enabled())

    @app.get("/eval")
    def eval_reports() -> dict:
        return {name: json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
                for name, p in REPORTS.items()}

    return app
