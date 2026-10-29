# Walkthrough video

A narrated, about 3.5-minute code walkthrough of Cite or Refuse: `kt-video.mp4`, with `captions.vtt`, `chapters.txt`
and `poster.jpg`. Everything is generated locally: Kokoro for the voice, Chromium (Playwright) for the frames,
ffmpeg for encoding.

## Rebuild

Needs Python 3.10-3.12, Node 18+, ffmpeg and espeak-ng on the PATH.

```bash
cd docs/kt-video
python3.12 -m venv .venv && .venv/Scripts/python.exe -m pip install "kokoro>=0.9" soundfile   # once
# (or: uv venv --python 3.12 .venv && uv pip install --python .venv/Scripts/python.exe "kokoro>=0.9" soundfile pip)
cd ../.. && make kt-video        # on macOS/Linux: make kt-video KT_PY=.venv/bin/python
```

`make kt-video` runs, in order:

1. `tts.py`: reads the **Narration** blocks in `script.md`, writes `audio/scene_XX.wav` plus word timestamps,
   then `timing.json` (each scene = its audio + 0.6 s) and `captions.srt`.
2. `check_excerpts.py`: fails if a code line shown on screen no longer matches the source file.
3. `render.mjs`: loads `kt-video.html`, calls `window.renderAt(t)` for every frame at 30 fps, pipes PNGs into
   ffmpeg, muxes the narration, and writes `out/` plus the committed `kt-video.mp4`, `poster.jpg`,
   `captions.vtt` and `chapters.txt`.

## Edit a scene

- **Words:** edit the scene's **Narration** in `script.md`, then `.venv/Scripts/python.exe tts.py 04` to
  regenerate only scene 04 (timing for all scenes is rebuilt). Spell hard words for the voice ("B M twenty-five");
  `CAPTION_FIXES` in `tts.py` maps them back to the written form for captions. Kokoro also accepts inline phoneme
  hints such as `[Refuse](/ɹəfjˈuz/)`.
- **Visuals:** each scene is an entry in `SCENES` in `kt-video.html`: `build` creates the DOM, `beats` names the
  narration phrases that trigger animations (matched against the word timestamps, so they follow the audio), and
  `render(t)` sets every style from the scene-local time. Keep it deterministic: no CSS transitions, timers or
  randomness.
- **Preview:** `node preview.mjs`, then open the printed URL. Play and scrub; audio plays once `out/narration.wav`
  exists.
- **Check frames:** `node render.mjs --stills 12,40.5` writes PNGs to `out/stills/` without a full render.
- **Re-render:** `node render.mjs` (add `--crf 24` if the MP4 grows past 20 MB).

Fonts are the Windows system fonts Bahnschrift, Segoe UI and Consolas, with fallbacks for other systems, so a render
on macOS or Linux will look slightly different.
