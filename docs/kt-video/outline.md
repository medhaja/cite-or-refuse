# KT video outline: Cite or Refuse

## Summary

Cite or Refuse is a small Python prototype that answers questions about a synthetic cold case (40 jail-call
transcripts, 15 case-file documents) and refuses to show anything it can't trace. Every claim carries a verbatim
quote and a citation to a call timestamp range or a document page and line range. A plain-code verifier
(`cite_or_refuse/verifier.py`) re-checks each citation against the source and drops failures into a visible
"Refused" list with one of three reasons: `bad_citation`, `quote_not_found` or `unsupported`. An offline eval
(`eval.py`) scores the same pipeline on 30 gold questions and measures how many deliberately corrupted citations the
verifier catches. It's aimed at Closure founders and engineers: the PRD reads Closure's public pitch ("AI finds,
humans check, evidence faces cross-examination") and its Zero Access Architecture as meaning that answer quality
has to be measurable without reading customer data. Everything runs locally with no API key. An LLM is optional
and never decides whether a quote exists.

Colour meaning used throughout: **blue = request / data in motion**, **amber = stored state (data files, chunks,
reports)**, **green = verified claim**, **red = refused claim**, neutral grey = code/components.

## Scenes (target ~3:30 total, ~520 words)

### 01 / Why it exists (~25 s)
- **Idea:** In this domain one invented quote is expensive. Closure's public pitch is that humans check what the AI
  finds, and that evidence must survive court. So every sentence should trace to the record, and that should be
  measurable offline.
- **Visual:** A single answer card appears with a quote. A citation chip snaps on (`CALL-017 @ 01:27-01:34`, green).
  A second card with no traceable source turns red and slides into a "Refused" column. Title: "Cite or refuse."
  Small source footnotes (Comstock's, Axios, New Times SLO, Inc.) are shown as names only.
- **Files:** `PRD.md` (Problem, Goals), `README.md` (problem section).

### 02 / Architecture (~30 s)
- **Idea:** One pipeline, two callers. `generator → chunker → BM25 retriever → answerer → verifier`, served by
  FastAPI to a static page, and the eval runner calls the *same* `Pipeline` object.
- **Visual:** Architecture diagram. Boxes light up left to right as the narration names them; the arrows animate in
  data order. The "eval runner" box fades in at the bottom with an arrow into the same Pipeline box. The verifier box
  is outlined as "plain code"; the answerer box carries a small "mock (default) / LLM (optional)" tag.
- **Files:** `cite_or_refuse/pipeline.py`, `cite_or_refuse/app.py`, `cite_or_refuse/evaluation.py`, `run.py`.

### 03 / Data model: chunks that keep their citations (~30 s)
- **Idea:** The data is seeded and fictional. Chunks are windows of 4 lines with a stride of 3, and every chunk and
  line keeps the metadata needed to cite it: call ID + start/end seconds, or doc ID + page + line numbers. The
  citation label is generated from that metadata, never written by hand.
- **Visual:** Data model. Left: a transcript (amber) with timestamped lines; a 4-line window slides down by 3.
  Right: the resulting chunk record with `source_type`, `source_id`, `start_ts`/`end_ts` (or `page`/`line_start`/
  `line_end`), `speaker`, `text`, `label`. Counter: "40 calls + 15 docs → 357 chunks".
- **Files:** `cite_or_refuse/generator.py`, `cite_or_refuse/corpus.py` (`CALL_WINDOW`, `_chunk`, `_make_chunk`,
  `citation_label`, `unit_citation`).

### 04 / One request, end to end (~45 s)
- **Idea:** Trace "What did Andre tell Rico to do with the green car?" through the real functions, with the real
  values the code produces today.
- **Visual:** Request trace. A blue query card travels through `POST /ask` → `Pipeline.ask` → `Retriever.search`
  (top 5 chunks appear with BM25 scores: DOC-03, DOC-09, CALL-018, CALL-017, DOC-03) → `MockAnswerer.answer`
  (lines scored by IDF-weighted coverage, threshold 0.55; 3 lines kept) → `verify` (each gets a green check) →
  response with "3 traceable claims" → a line appended to `runs.jsonl` (amber).
- **Files:** `app.py:58-62`, `pipeline.py:41-63`, `retriever.py:36-53`, `answerer.py:59-103`, `verifier.py:47-88`,
  `app.py:38-52`.

### 05 / The verifier, in code (~35 s)
- **Idea:** Three checks in order, first failure wins: does the citation resolve to real lines; is the quote
  verbatim in those lines (whitespace-normalized, case kept); does the claim's speaker, numbers, names and wording
  match the span (overlap ≥ 0.6). String matching, not the model, decides whether a quote exists.
- **Visual:** Code focus on `cite_or_refuse/verifier.py`, ~14 lines from `verify()`, highlighting the
  `resolve` / `find_quote` / speaker / numbers / overlap lines as narrated. Then a with/without beat: the demo's
  injected fault moves CALL-017 to `05:19-05:39` on a 5:14 call → red `bad_citation` badge.
- **Files:** `verifier.py:17-18, 28-88`, `corpus.py:125-156`, `faults.py`.

### 06 / The eval and fault injection (~30 s)
- **Idea:** `python eval.py` runs the same pipeline over 30 gold questions (20 answerable, 5 two-source,
  5 unanswerable) and reports recall@5, quote fidelity, refusal rates and citation precision against targets.
  `--inject-faults` corrupts 20 % of drafted claims (wrong timestamp, altered quote, swapped speaker); 9 of 9 caught.
- **Visual:** Metric tiles fill in from `eval_report.json` (amber source) with target ticks. Then three fault cards
  (one per type) drop into the verifier and each lands in red with its reason. Citation precision 0.68 is shown
  honestly, not hidden.
- **Files:** `cite_or_refuse/evaluation.py`, `eval.py`, `cite_or_refuse/faults.py`, `eval_report*.json`.

### 07 / Gotchas and limitations (~35 s)
- **Idea:** What to know before trusting it.
  - In mock mode the claim text *is* the quote, so the support score is always 1.0; the support check earns its
    keep with faults and with an LLM drafting paraphrases.
  - Verbatim matching assumes clean transcripts; real ASR output would break it.
  - Lexical support misses paraphrase; compound questions are only split on ", and".
  - The verifier checks traceability, not truth: the green-car and blue-pickup witnesses are both shown.
  - 30 gold questions written alongside the data are a smoke test, and the clean numbers are optimistic.
- **Visual:** With/without panels: "Traceable ✓" vs "True ?" (green car vs blue pickup cards both green-checked).
  Then a compact list of limitations, each with a one-line "next step" arrow (FAISS alongside BM25, LLM-mode eval
  diff between two models, fuzzy timestamp-aware matching, larger independent gold set in CI).
- **Files:** `answerer.py:96-101`, `verifier.py:75-88`, `answerer.py:17-20`, `generator.py` (DOC-03/DOC-04),
  `README.md` Limitations / Next steps.

### 08 / Run it, and recap (~25 s)
- **Idea:** One command: `python -m pip install -r requirements.txt && python run.py`, then open localhost:8000.
  Three tabs: Ask, Source viewer, Eval. Optional LLM via `COR_LLM_MODEL` in `.env`; the model picks line IDs and our
  metadata builds the citation. Then 5 takeaways.
- **Visual:** A terminal card with the command and the startup log ("Indexed 357 chunks from 40 calls and 15 case
  files."), a schematic of the three tabs, then the recap list.
- **Files:** `README.md`, `run.py`, `cite_or_refuse/llm.py`, `.env.example`.

## Open questions

Resolved: all five were approved as proposed.

1. **Python for Kokoro.** The only Python on this machine is 3.13 (system and Anaconda). Kokoro needs 3.10–3.12.
   `uv` is installed, so I'd like to run `uv python install 3.12` (a one-time download of a standalone Python
   build from GitHub; nothing from this repo is sent anywhere) and create `docs/kt-video/.venv` with it. OK?
2. **The "mock support score is always 1.0" gotcha** (scene 07) is an observation from the code and a live run,
   not something the README states. Keep it in? I think it's the most useful thing an engineer could learn here.
3. **Source names in scene 01:** I plan to show the publication names (Comstock's, Axios, New Times SLO, Inc.) as
   small footnotes and say "public coverage" in the narration, without naming the people quoted. OK?
4. **Synthetic names on screen:** the fictional characters (Andre, Rico, Tasha) and fictional case number appear
   in the trace. They're generated by `generator.py` and are not real people, so I plan to show them. OK?
5. **Build command:** the repo already has a Makefile, so I'd add a `kt-video` target (`make kt-video`), plus a
   `package.json` in `docs/kt-video/` for the Playwright dependency. OK, or would you prefer only `npm run kt-video`?
