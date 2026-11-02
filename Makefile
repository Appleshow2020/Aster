# Aster 개발용 Makefile
PY ?= python3

.PHONY: test demo repl clean tokens
test:
	$(PY) Tools/runtests.py
demo:
	$(PY) run.py Lib/test/demo.ast
repl:
	$(PY) run.py
tokens:
	$(PY) run.py --tokens Lib/test/demo.ast | head -40
clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
