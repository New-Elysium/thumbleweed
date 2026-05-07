UV := /root/.local/bin/uv
PY := $(UV) run python

.PHONY: sync test prepare dist upload

sync:
	$(UV) sync --group dev --group bench
	$(UV) run maturin develop --release

test:
	$(UV) run pytest -q
	cargo test

prepare:
	$(PY) scripts/update_claude.py

dist:
	$(UV) run maturin build --release --compatibility off --out dist

upload:
	$(UV) run twine upload dist/*
