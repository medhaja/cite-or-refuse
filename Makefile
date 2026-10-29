PY ?= python
# Walkthrough video: Python 3.10-3.12 venv with Kokoro, relative to docs/kt-video (.venv/bin/python on macOS/Linux)
KT_PY ?= .venv/Scripts/python.exe

.PHONY: install demo data eval eval-faults test kt-video

install:
	$(PY) -m pip install -r requirements.txt

demo: install
	$(PY) run.py

data:
	$(PY) -m cite_or_refuse.generator

eval:
	$(PY) eval.py

eval-faults:
	$(PY) eval.py --inject-faults

test:
	$(PY) -m pytest -q

kt-video:
	cd docs/kt-video && $(KT_PY) tts.py && $(KT_PY) check_excerpts.py && npm install --no-audit --no-fund \
		&& npx playwright install chromium && node render.mjs
