PY ?= python

.PHONY: install demo data eval eval-faults test

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
