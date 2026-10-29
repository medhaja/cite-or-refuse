"""Loads the case data, chunks it with citation metadata, and resolves citations back to exact spans."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .generator import DATA_DIR, SYSTEM, ensure_data
from .text import fmt_ts

CALL_WINDOW, CALL_STRIDE = 4, 3
DOC_WINDOW, DOC_STRIDE = 4, 3
DOC_HEADER_LINES = 2


def citation_label(c: dict) -> str:
    if c.get("source_type") == "call":
        return f"{c['source_id']} @ {fmt_ts(int(c['start_ts']))}-{fmt_ts(int(c['end_ts']))}"
    lines = f"L{c['line_start']}" if c["line_start"] == c["line_end"] else f"L{c['line_start']}-{c['line_end']}"
    return f"{c['source_id']} p.{c['page']} {lines}"


def unit_citation(unit: dict) -> dict:
    """The citation for a single line (a 'unit')."""
    if unit["source_type"] == "call":
        c = {"source_type": "call", "source_id": unit["source_id"], "start_ts": unit["start_ts"],
             "end_ts": unit["end_ts"], "speaker": unit["speaker"]}
    else:
        c = {"source_type": "doc", "source_id": unit["source_id"], "page": unit["page"],
             "line_start": unit["line"], "line_end": unit["line"], "speaker": unit["speaker"]}
    c["label"] = citation_label(c)
    return c


@dataclass
class Corpus:
    case: dict
    calls: dict[str, dict]
    docs: dict[str, dict]
    gold: list[dict]
    chunks: list[dict] = field(default_factory=list)

    @classmethod
    def load(cls, data_dir: Path = DATA_DIR) -> "Corpus":
        ensure_data(data_dir)
        read = lambda name: json.loads((data_dir / name).read_text(encoding="utf-8"))  # noqa: E731
        corpus = cls(
            case=read("case.json"),
            calls={c["call_id"]: c for c in read("calls.json")},
            docs={d["doc_id"]: d for d in read("case_files.json")},
            gold=read("gold_questions.json"),
        )
        corpus.chunks = corpus._chunk()
        return corpus

    @property
    def people(self) -> dict[str, list[str]]:
        return self.case["people"]

    def title(self, source_id: str) -> str:
        if source_id in self.calls:
            c = self.calls[source_id]
            return f"Jail call, {c['date']}: {', '.join(c['participants'])}"
        return self.docs[source_id]["title"]

    # ---- units and chunks -------------------------------------------------------------------------------

    def call_units(self, call_id: str) -> list[dict]:
        return [
            {"source_type": "call", "source_id": call_id, "start_ts": ln["start_ts"], "end_ts": ln["end_ts"],
             "speaker": ln["speaker"], "text": ln["text"]}
            for ln in self.calls[call_id]["lines"] if ln["speaker"] != SYSTEM
        ]

    def doc_units(self, doc_id: str) -> list[dict]:
        doc = self.docs[doc_id]
        return [
            {"source_type": "doc", "source_id": doc_id, "page": p["page"], "line": n, "speaker": doc["speaker"],
             "text": text}
            for p in doc["pages"] for n, text in enumerate(p["lines"], start=1) if n > DOC_HEADER_LINES
        ]

    def _chunk(self) -> list[dict]:
        chunks = []
        for call_id in self.calls:
            units = self.call_units(call_id)
            for i in range(0, len(units), CALL_STRIDE):
                window = units[i:i + CALL_WINDOW]
                if not window:
                    break
                chunks.append(self._make_chunk(window, start_ts=window[0]["start_ts"], end_ts=window[-1]["end_ts"]))
                if i + CALL_WINDOW >= len(units):
                    break
        for doc_id, doc in self.docs.items():
            units = self.doc_units(doc_id)
            for page in doc["pages"]:
                page_units = [u for u in units if u["page"] == page["page"]]
                for i in range(0, len(page_units), DOC_STRIDE):
                    window = page_units[i:i + DOC_WINDOW]
                    if not window:
                        break
                    chunks.append(self._make_chunk(window, page=page["page"], line_start=window[0]["line"],
                                                   line_end=window[-1]["line"]))
                    if i + DOC_WINDOW >= len(page_units):
                        break
        return chunks

    def _make_chunk(self, units: list[dict], **span) -> dict:
        source_type, source_id = units[0]["source_type"], units[0]["source_id"]
        speakers = list(dict.fromkeys(u["speaker"] for u in units))
        chunk = {
            "source_type": source_type, "source_id": source_id,
            "start_ts": span.get("start_ts"), "end_ts": span.get("end_ts"),
            "page": span.get("page"), "line_start": span.get("line_start"), "line_end": span.get("line_end"),
            "speaker": ", ".join(speakers), "text": "\n".join(u["text"] for u in units),
            "title": self.title(source_id), "units": units,
        }
        chunk["label"] = citation_label(chunk)
        chunk["chunk_id"] = chunk["label"]
        return chunk

    # ---- citation resolution ----------------------------------------------------------------------------

    def resolve(self, citation: dict) -> tuple[list[dict] | None, str]:
        """Return the lines a citation points at, or (None, reason) if it points at nothing real."""
        sid = citation.get("source_id")
        try:
            if citation.get("source_type") == "call":
                if sid not in self.calls:
                    return None, f"unknown call {sid}"
                start, end = int(citation["start_ts"]), int(citation["end_ts"])
                duration = self.calls[sid]["duration"]
                if start < 0 or end < start or end > duration:
                    return None, f"timestamp range {fmt_ts(max(start, 0))}-{fmt_ts(max(end, 0))} is outside " \
                                 f"the call (00:00-{fmt_ts(duration)})"
                lines = [u for u in self.call_units(sid) if u["start_ts"] <= end and u["end_ts"] >= start]
                if not lines:
                    return None, "no transcript lines in that range"
                return lines, ""
            if citation.get("source_type") == "doc":
                if sid not in self.docs:
                    return None, f"unknown document {sid}"
                pages = {p["page"]: p for p in self.docs[sid]["pages"]}
                page, a, b = int(citation["page"]), int(citation["line_start"]), int(citation["line_end"])
                if page not in pages:
                    return None, f"{sid} has no page {page}"
                if a < 1 or b < a or b > len(pages[page]["lines"]):
                    return None, f"lines {a}-{b} do not exist on {sid} p.{page}"
                lines = [u for u in self.doc_units(sid) if u["page"] == page and a <= u["line"] <= b]
                if not lines:
                    return None, "citation covers only the page header"
                return lines, ""
        except (KeyError, TypeError, ValueError):
            return None, "malformed citation"
        return None, "unknown source type"

    def source_view(self, source_id: str) -> dict | None:
        if source_id in self.calls:
            c = self.calls[source_id]
            return {"source_type": "call", "source_id": source_id, "title": self.title(source_id), "date": c["date"],
                    "participants": c["participants"], "duration": c["duration"], "lines": c["lines"]}
        if source_id in self.docs:
            d = self.docs[source_id]
            return {"source_type": "doc", "source_id": source_id, "title": d["title"], "date": d["date"],
                    "speaker": d["speaker"], "pages": d["pages"]}
        return None
