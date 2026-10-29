"""Narration -> audio with Kokoro (runs locally), plus timing.json and captions.srt.

    .venv/Scripts/python.exe tts.py            # all scenes
    .venv/Scripts/python.exe tts.py 03 05      # only these scenes; timing is rebuilt from every scene
    .venv/Scripts/python.exe tts.py --timing   # no synthesis, just rebuild timing.json and captions.srt

Reads the **Narration** blocks from script.md. Writes audio/scene_XX.wav (24 kHz mono), audio/scene_XX.words.json
(word timestamps from the pipeline), timing.json and captions.srt.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
AUDIO = HERE / "audio"
SCRIPT = HERE / "script.md"
RATE = 24_000
VOICE = "af_heart"
PAD = 0.6  # seconds of silence after each scene
HOLD = {"09": 2.5}  # extra silent hold for scenes that need reading time (the closing card)
CAPTION_CHARS = 84
# Narration is spelled for the voice; captions show the written form.
CAPTION_FIXES = [
    ("B M twenty-five", "BM25"), ("Fast A-P-I", "FastAPI"), ("runs dot J-son-L", "runs.jsonl"),
    ("python run dot pie", "python run.py"), ("slash ask", "/ask"), ("I D", "ID"),
    ("zero point six eight", "0.68"), ("zero point six", "0.6"), ("recall at five", "recall@5"),
]


def read_scenes(path: Path = SCRIPT) -> list[dict]:
    scenes, cur, in_narr = [], None, False
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## Scene (\d+) / (.+)$", line)
        if m:
            cur = {"id": m.group(1), "title": m.group(2).strip(), "text": []}
            scenes.append(cur)
            in_narr = False
        elif line.startswith("**Narration**"):
            in_narr = True
        elif line.startswith("**") or line.startswith("## "):
            in_narr = False
        elif in_narr and cur is not None and line.strip():
            cur["text"].append(line.strip())
    for s in scenes:
        s["text"] = " ".join(s["text"])
    return scenes


def synthesize(pipeline, scene: dict) -> None:
    chunks, words, offset = [], [], 0.0
    for result in pipeline(scene["text"], voice=VOICE, speed=1.0):
        audio = result.audio.numpy() if hasattr(result.audio, "numpy") else np.asarray(result.audio)
        for tok in result.tokens or []:
            if tok.start_ts is None or tok.end_ts is None or not tok.text.strip():
                continue
            if re.fullmatch(r"\W+", tok.text):
                if words:  # attach punctuation to the previous word for captions
                    words[-1]["text"] += tok.text
                continue
            words.append({"text": tok.text, "start": round(offset + tok.start_ts, 3),
                          "end": round(offset + tok.end_ts, 3)})
        chunks.append(audio)
        offset += len(audio) / RATE
    AUDIO.mkdir(exist_ok=True)
    sf.write(AUDIO / f"scene_{scene['id']}.wav", np.concatenate(chunks), RATE, subtype="PCM_16")
    (AUDIO / f"scene_{scene['id']}.words.json").write_text(json.dumps(words, indent=1), encoding="utf-8")
    print(f"scene {scene['id']}: {offset:.2f}s, {len(words)} timed words")


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3_600_000:02d}:{ms // 60_000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def caption_lines(words: list[dict]) -> list[tuple[float, float, str]]:
    """Group words into captions: break at sentence ends or when a caption gets too long."""
    out, cur = [], []
    for w in words:
        if cur and len(" ".join(x["text"] for x in cur + [w])) > CAPTION_CHARS:
            out.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.?!]$", w["text"]):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [(g[0]["start"], g[-1]["end"], written(" ".join(x["text"] for x in g))) for g in out]


def written(text: str) -> str:
    for spoken, form in CAPTION_FIXES:
        text = re.sub(rf"\b{re.escape(spoken)}\b", form, text)
    return text


def build_timing(scenes: list[dict]) -> dict:
    t, out, captions = 0.0, [], []
    for s in scenes:
        wav = AUDIO / f"scene_{s['id']}.wav"
        audio_dur = sf.info(str(wav)).frames / RATE
        words = json.loads((AUDIO / f"scene_{s['id']}.words.json").read_text(encoding="utf-8"))
        pad = PAD + HOLD.get(s["id"], 0.0)
        dur = round(audio_dur + pad, 3)
        out.append({"id": s["id"], "title": s["title"], "start": round(t, 3), "duration": dur,
                    "audio_duration": round(audio_dur, 3), "pad": pad, "words": words})
        for a, b, text in caption_lines(words):
            captions.append((t + a, t + b, text))
        t += dur
    timing = {"fps": 30, "pad": PAD, "total": round(t, 3), "scenes": out}
    (HERE / "timing.json").write_text(json.dumps(timing, indent=1), encoding="utf-8", newline="\n")
    srt = []
    for i, (a, b, text) in enumerate(captions, start=1):
        srt.append(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n")
    (HERE / "captions.srt").write_text("\n".join(srt), encoding="utf-8", newline="\n")
    print(f"timing.json: {len(out)} scenes, {t:.2f}s total; captions.srt: {len(captions)} cues")
    return timing


def main(argv: list[str]) -> None:
    scenes = read_scenes()
    if argv == ["--timing"]:  # rebuild timing.json and captions.srt from existing audio
        wanted = set()
    else:
        wanted = {a.zfill(2) for a in argv} or {s["id"] for s in scenes}
    todo = [s for s in scenes if s["id"] in wanted]
    if todo:
        from kokoro import KPipeline

        pipeline = KPipeline(lang_code="a")
        for s in todo:
            synthesize(pipeline, s)
    build_timing(scenes)


if __name__ == "__main__":
    main(sys.argv[1:])
