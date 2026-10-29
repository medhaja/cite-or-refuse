# KT video script: Cite or Refuse

Narration is written for text-to-speech: hard words are spelled out ("B M twenty-five", "Fast A-P-I", "J-son-L",
"run dot pie"). `[Refuse](/ɹəfjˈuz/)` is a Kokoro pronunciation hint: without it the name is read as the noun.
Colours: blue = request, amber = stored data, green = verified, red = refused, grey = components.
Line references are to the repo at commit `df9d96d`.

---

## Scene 01 / Why it exists

**Narration**

Closure's public pitch is that the AI finds the material, and people check it. That evidence still has to survive
court, and one invented quote could cost trust with many agencies. Cite or [Refuse](/ɹəfjˈuz/) is built on one rule. Every claim
links to an exact line in the record. If it can't be traced, it's refused, and you see why. All of it runs on
synthetic data.

**On screen**

- Title "Cite or Refuse" with subtitle "Every claim traces to the record, or it's refused."
- At "the AI finds the material, and people check it": two small labels, "AI finds" → "people check", connected by
  a blue arrow. Footnote line: "Public coverage: Comstock's · Axios · New Times SLO · Inc."
- At "one invented quote": a claim card with a quote fades in, no citation, grey.
- At "links to an exact line": a green citation chip `CALL-017 @ 01:27-01:34` snaps onto a second card, and the card
  turns green.
- At "it's refused, and you see why": the uncited card slides into a red "Refused" column with the tag
  `quote_not_found`.
- At "synthetic data": a small amber tag "synthetic data · offline eval".

**Sources**

- AI finds, humans check; evidence faces court scrutiny: `PRD.md:7`
- One invented quote could cost trust with many agencies: `PRD.md:9`
- Every claim carries a citation; unsupported claims are refused and listed: `PRD.md:18-19`, `README.md:17-21`
- Synthetic data, offline eval (the PRD's reading of Zero Access, stated as an assumption): `PRD.md:9`,
  `README.md:35-37`, `cite_or_refuse/generator.py:3-4`

---

## Scene 02 / Architecture

**Narration**

Here's the big picture. A seeded generator writes a fictional case. The chunker splits it into windows that keep
their source metadata. A B M twenty-five retriever finds the best chunks, the answerer drafts quoted claims, and the
verifier checks each one. Fast A-P-I serves it to one static page. And the eval calls the same pipeline, so you
measure what users see.

**On screen**

- Chapter label "02 / Architecture". Boxes appear left to right as named: `generator` (amber, data) → `chunker` →
  `BM25 retriever` → `answerer` → `verifier` → `FastAPI` → `static page`.
- At "drafts quoted claims": tag on answerer "mock (default) · LLM (optional)".
- At "checks each one": verifier gets a "plain code" outline.
- A dashed bracket groups retriever → answerer → verifier, labelled `Pipeline` (`pipeline.py`).
- At "the eval calls the same pipeline": an `eval runner` box rises below and an arrow enters the same `Pipeline` bracket.

**Sources**

- Pipeline order: `README.md:60-62`, `PRD.md:63`
- Seeded generator: `cite_or_refuse/generator.py:16`, `cite_or_refuse/generator.py:464-465`
- Chunks keep source metadata: `cite_or_refuse/corpus.py:109-121`
- BM25 retriever: `cite_or_refuse/retriever.py:30-34`
- Answerer drafts claims, verifier checks each: `cite_or_refuse/pipeline.py:27-39`
- FastAPI serves a static page: `cite_or_refuse/app.py:36`, `cite_or_refuse/app.py:54-56`
- Eval calls the same Pipeline: `cite_or_refuse/evaluation.py:1`, `cite_or_refuse/evaluation.py:40-49`,
  `cite_or_refuse/evaluation.py:66`, `cite_or_refuse/pipeline.py:1`

---

## Scene 03 / Data model

**Narration**

The case is forty jail calls and fifteen case files, from a fixed seed. The chunker slides a four-line window,
three lines at a time. Every chunk keeps what's needed to cite it: a call I D with start and end seconds, or a page
and line numbers. The citation label is computed from those fields. Nobody types it.

**On screen**

- Left: an amber transcript panel "CALL-017" with timestamped lines (`01:14`, `01:27`, …).
- At "four-line window": a blue bracket covers lines 1-4; at "three lines at a time" it steps down by 3, overlapping
  one line.
- Right: the chunk record, fields appearing one by one: `source_type: "call"`, `source_id: "CALL-017"`,
  `start_ts: 74`, `end_ts: 106`, `speaker`, `text`, then the document variant `page`, `line_start`, `line_end`.
- At "computed from those fields": `citation_label()` arrow → chip `CALL-017 @ 01:14-01:46`.
- Small counter: "40 calls + 15 case files → 357 chunks".

**Sources**

- 40 calls, 15 case files, fixed seed: `cite_or_refuse/generator.py:16`, `cite_or_refuse/generator.py:464-467`,
  `cite_or_refuse/generator.py:235-384`
- Window 4, stride 3: `cite_or_refuse/corpus.py:12-13`, `cite_or_refuse/corpus.py:86-106`
- Chunk fields: `cite_or_refuse/corpus.py:109-121`; line-level ("unit") fields: `cite_or_refuse/corpus.py:69-82`
- Label computed from fields: `cite_or_refuse/corpus.py:17-21`, `cite_or_refuse/corpus.py:24-33`
- 357 chunks (on screen only): printed by `run.py:40-41`; checked with a live run at `df9d96d`
- `CALL-017 @ 01:14-01:46` chunk (74 s to 106 s): live run of `Retriever.search` at `df9d96d`

---

## Scene 04 / One request, end to end

**Narration**

Let's trace one question. What did Andre tell Rico to do with the green car? The page posts it to slash ask. The
retriever keeps the top five chunks. The mock answerer scores each line by how much of the question's rare
vocabulary it covers. Three lines clear the bar: the same instruction from two near-duplicate calls, plus the car's
registration record. All three pass the verifier, and the request is logged to runs dot J-son-L.

**On screen**

- A blue query card with the question. A rail of function names left to right: `POST /ask` → `Pipeline.ask` →
  `Retriever.search` → `MockAnswerer.answer` → `verify` → response.
- At "posts it to slash ask": card moves to `POST /ask` (`app.py`).
- At "keeps the top five chunks": five chunk rows fan out with BM25 scores: `DOC-03 p.1 L6-9 13.17`,
  `DOC-09 p.1 L3-6 9.56`, `CALL-018 @ 00:23-00:57 9.08`, `CALL-017 @ 01:14-01:46 8.68`, `DOC-03 p.1 L3-6 7.99`.
- At "rare vocabulary": caption "IDF-weighted coverage ≥ 0.55".
- At "Three lines clear the bar": three claim cards: `CALL-018 @ 00:39-00:45`, `CALL-017 @ 01:27-01:34`,
  `DOC-09 p.1 L5`.
- At "pass the verifier": each card gets a green check and "score 1.0".
- At "logged": an amber line appends to a `runs.jsonl` panel: `{query, mode, retrieved, claims, refused, latency_ms}`.

**Sources**

- The question is a sample/gold question: `cite_or_refuse/generator.py:405-406`
- Page posts to /ask: `static/index.html:222`; endpoint: `cite_or_refuse/app.py:58-62`
- Pipeline.ask → retrieve → draft → verify: `cite_or_refuse/pipeline.py:41-48`
- Top five: `cite_or_refuse/pipeline.py:18`, `cite_or_refuse/pipeline.py:24-25`, `cite_or_refuse/retriever.py:36-53`
- Mock is the default when no model is configured: `cite_or_refuse/pipeline.py:27-34`
- Scores every line by IDF-weighted coverage, threshold 0.55: `cite_or_refuse/answerer.py:37`,
  `cite_or_refuse/answerer.py:49-57`, `cite_or_refuse/answerer.py:76-87`
- Near-duplicate calls 17 and 18: `cite_or_refuse/generator.py:149-158`
- Registration record: `cite_or_refuse/generator.py:336`
- Retrieved chunks, three claims, scores 1.0: live run of `Pipeline.ask` at `df9d96d` (also `README.md:43-45`)
- Logged to runs.jsonl: `cite_or_refuse/app.py:38-52`, `cite_or_refuse/app.py:61`

---

## Scene 05 / The verifier

**Narration**

The verifier is plain code, and the first failure wins. One: does the citation point at real lines? If not, it's a
bad citation. Two: is the quote verbatim? Only whitespace and curly quotes are normalized. Three: is it supported?
The speaker must match, every number and name must be in the span, and word overlap must reach zero point six. In
the demo, inject a fault, and call seventeen's timestamp moves past the end of the call. Refused, with the reason.

**On screen**

- Code focus, path `cite_or_refuse/verifier.py`, real line numbers, gaps marked `⋮`:
  - 47-51 (`def verify` … `resolve` … `BAD_CITATION`), highlighted at "real lines".
  - 53-55 (`find_quote` … `QUOTE_NOT_FOUND`), highlighted at "verbatim".
  - 57-60 (speaker check), highlighted at "speaker must match".
  - 67-69 (missing numbers), highlighted at "number and name".
  - 86-87 (`overlap < SUPPORT_THRESHOLD`), highlighted at "zero point six".
- Side card at "whitespace and curly quotes": `normalize_ws()` from `text.py`.
- At "inject a fault": with/without pair. Left: green `CALL-017 @ 01:27-01:34`. Right: red
  `CALL-017 @ 05:19-05:39` with "call is 00:00-05:14" and the badge `bad_citation`.

**Sources**

- First failure wins; three reasons: `cite_or_refuse/verifier.py:1-8`, `cite_or_refuse/verifier.py:17`
- Citation must resolve to real lines: `cite_or_refuse/verifier.py:49-51`, `cite_or_refuse/corpus.py:125-156`
- Verbatim quote: `cite_or_refuse/verifier.py:28-44`, `cite_or_refuse/verifier.py:53-55`
- Only whitespace and typographic quotes/dashes normalized, case kept: `cite_or_refuse/text.py:7`,
  `cite_or_refuse/text.py:19-21`
- Speaker must match: `cite_or_refuse/verifier.py:57-60`
- Numbers and names must appear in the span: `cite_or_refuse/verifier.py:67-73`
- Overlap ≥ 0.6: `cite_or_refuse/verifier.py:18`, `cite_or_refuse/verifier.py:75-87`
- Demo fault toggle: `static/index.html:154`, `cite_or_refuse/pipeline.py:46-47`
- Timestamp moved past the end: `cite_or_refuse/faults.py:17-21`; refused as outside the call:
  `cite_or_refuse/corpus.py:133-136`
- `05:19-05:39` vs a 5:14 call: live run of `Pipeline.ask(..., inject_fault=True)` at `df9d96d`

---

## Scene 06 / Eval and fault injection

**Narration**

The eval runs the same pipeline over thirty gold questions, five of them unanswerable. In mock mode, recall at five
is one, every shown quote is verbatim, and every unanswerable question is refused. Then fault injection corrupts a
fifth of the claims: a wrong timestamp, an altered quote, or a swapped speaker. The verifier catches nine of nine.
Citation precision is only zero point six eight, because the mock sometimes quotes a related line.

**On screen**

- Terminal chip `python eval.py --inject-faults`. An amber `eval_report.json` card.
- At "thirty gold questions": a 30-dot grid, 20 answerable, 5 two-source, 5 unanswerable (outlined).
- Metric tiles fill in with target ticks: recall@5 1.00 (≥ 0.85 ✓), quote fidelity 1.00 (= 1.0 ✓), unanswerable
  refused 1.00 (≥ 0.8 ✓), false refusals 0.00 (≤ 0.15 ✓).
- At "wrong timestamp, an altered quote, or a swapped speaker": three red fault cards drop into a verifier box and
  land under "caught 3/3" each. Counter "9 / 9 caught".
- At "only zero point six eight": a neutral tile "citation precision 0.68" with a small example: question "What
  vehicle did Paul Ortiz describe?" quotes "A vehicle came out of the lot…" instead of "blue pickup truck".

**Sources**

- Same pipeline: `cite_or_refuse/evaluation.py:40-49`, `cite_or_refuse/evaluation.py:66`
- 30 gold questions, 20 / 5 / 5: `cite_or_refuse/generator.py:404-461`
- Clean metrics (recall 1.0, fidelity 1.0, unanswerable refusal 1.0, false refusal 0.0, precision 0.68):
  `eval_report.json` (`metrics`), `README.md:92-99`
- Targets: `cite_or_refuse/evaluation.py:13-19`
- 20 % corrupted, three fault types: `eval.py:43`, `cite_or_refuse/faults.py:11`, `cite_or_refuse/faults.py:79-88`
- 9 of 9 caught, 3 per type: `eval_report_faults.json` (`fault_injection`), `README.md:98`
- Precision 0.68 and the Paul Ortiz example: `README.md:105-108`

---

## Scene 07 / Gotchas and next steps

**Narration**

Some gotchas. In mock mode the claim is built from the quote, so a clean claim always scores one. The support check
really matters against faults, or a model that paraphrases. Verbatim matching assumes clean transcripts;
speech-to-text errors would break it. And the verifier proves traceable, not true: the green car and the blue
pickup witnesses both pass. Next steps: dense retrieval beside B M twenty-five, comparing models on the same eval,
fuzzy matching, and a bigger gold set, written by someone else.

**On screen**

- Gotcha 1: a claim card `Andre Whitfield said: "Tell Rico get rid of the green one…"` with the quote part
  underlined; caption "claim text = speaker + quote → overlap 1.0".
- Gotcha 2: transcript line with a garbled word ("get rid of the green won") → red `quote_not_found`; caption
  "ASR noise breaks strict matching".
- Gotcha 3: with/without panel "Traceable ✓ / True ?": `DOC-03 p.1 L7 "The car was dark green…"` and
  `DOC-04 p.1 L7 "The color was blue…"`, both green-checked, captioned with the question that shows them both.
- At "Next steps": four arrows with one-line items: dense retrieval (FAISS) + BM25 · LLM-mode eval, two models,
  diff the reports · fuzzy, timestamp-aware quote matching · larger independent gold set, tracked in CI.
- At "written by someone else": tag "today: 30 questions, same author as the data = smoke test".

**Sources**

- Mock claim text is speaker + verb + quote: `cite_or_refuse/answerer.py:96-101`; overlap counts span and speaker
  vocabulary, and "said"/"wrote" are stopwords: `cite_or_refuse/verifier.py:62-76`, `cite_or_refuse/text.py:10-16`;
  all clean demo claims score 1.0 in a live run at `df9d96d`
- Support check matters for faults and LLM paraphrase: `tests/test_llm.py:40` (paraphrase with wrong number is
  unsupported), `cite_or_refuse/faults.py:52-61`
- ASR errors break verbatim matching: `README.md:147-149`, `PRD.md:83`
- Traceable, not true; conflicting witnesses both shown: `README.md:154-155`, `cite_or_refuse/generator.py:272`,
  `cite_or_refuse/generator.py:283`; a live run of gold question Q22 at `df9d96d` shows DOC-03 p.1 L7 and
  DOC-04 p.1 L7 both `supported`
- All 47 clean mock claims across the 30 gold questions score 1.0: live run at `df9d96d`
- Smoke test, not a benchmark: `README.md:156`, `README.md:105-106`
- Next steps: `README.md:161-165`

The on-screen "green won" line is an illustration of ASR noise, not a line from the data; it is labelled
"illustration".

---

## Scene 08 / Run it, and recap

**Narration**

To run it, install the requirements and run python run dot pie. Then open localhost, port eight thousand. No key
needed. You get three tabs: Ask, Source viewer, and Eval. To try a real model, set one environment variable. The
model only picks lines by I D; our metadata builds the citation. To recap: citations come from metadata, string
matching decides if a quote exists, refusals stay visible, and the eval measures it all.

**On screen**

- Terminal card: `python -m pip install -r requirements.txt && python run.py`, then the log lines
  `Indexed 357 chunks from 40 calls and 15 case files.` and `Open http://127.0.0.1:8000`.
- At "three tabs": three tab pills `Ask` · `Source viewer` · `Eval`.
- At "one environment variable": `COR_LLM_MODEL=<model-name>` in a `.env` card (placeholder, no key shown);
  arrow "line IDs → citation_for() → citation".
- At "To recap": four takeaways, one per beat:
  1. Citations are built from metadata, never written.
  2. String matching decides whether a quote exists.
  3. Refusals are shown, with a reason.
  4. The eval runs the same pipeline, offline, on synthetic data.

**Sources**

- Run command: `README.md:3-9`
- Builds index and serves on 127.0.0.1:8000: `run.py:26-27`, `run.py:38-49`
- No key needed: `README.md:9`, `cite_or_refuse/llm.py:39-44`, `cite_or_refuse/pipeline.py:29-34`
- Three tabs: `static/index.html:138-140`
- One environment variable enables the model: `cite_or_refuse/llm.py:1`, `cite_or_refuse/llm.py:39-44`
- Model picks lines by ID; citation built from metadata: `cite_or_refuse/llm.py:5`, `cite_or_refuse/llm.py:66-96`
- String matching decides: `PRD.md:65`, `README.md:83`, `cite_or_refuse/verifier.py:1`
- Eval offline on synthetic data: `cite_or_refuse/evaluation.py:1`, `cite_or_refuse/generator.py:3-4`

---

## Totals

| Scene | Words | Est. at 145 wpm |
|---|---|---|
| 01 Why it exists | 67 | 0:28 |
| 02 Architecture | 65 | 0:27 |
| 03 Data model | 59 | 0:24 |
| 04 One request | 76 | 0:31 |
| 05 Verifier | 82 | 0:34 |
| 06 Eval | 74 | 0:31 |
| 07 Gotchas | 83 | 0:34 |
| 08 Run + recap | 74 | 0:31 |
| **Total** | **580** | **≈ 4:00** plus 8 × 0.6 s padding (Kokoro usually reads a little faster) |

No claims are marked UNVERIFIED.
