# Entorno fuera de iCloud, como Programaciones (ARCHITECTURE.md §1).
VENV := $(HOME)/.venvs/pccf
PY := $(VENV)/bin/python

.PHONY: venv comprobar test lint

venv:
	@test -x "$(PY)" || python3.11 -m venv "$(VENV)"
	$(PY) -m pip install --upgrade pip setuptools
	$(PY) -m pip install -r requirements-dev.txt

test:
	$(VENV)/bin/pytest

lint:
	$(VENV)/bin/ruff check src scripts tests

comprobar:
	$(PY) --version
	$(PY) -c "import PyQt6.QtCore as q, yaml, jsonschema, lxml, certifi, cryptography; print('PyQt6', q.PYQT_VERSION_STR, '· Qt', q.QT_VERSION_STR)"
	$(VENV)/bin/pytest --version
	$(VENV)/bin/ruff --version
