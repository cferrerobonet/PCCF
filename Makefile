# Entorno fuera de iCloud, como Programaciones (ARCHITECTURE.md §1).
VENV := $(HOME)/.venvs/pccf
PY := $(VENV)/bin/python

.PHONY: venv comprobar

venv:
	@test -x "$(PY)" || python3.11 -m venv "$(VENV)"
	$(PY) -m pip install --upgrade pip setuptools
	$(PY) -m pip install -r requirements-dev.txt

comprobar:
	$(PY) --version
	$(PY) -c "import PyQt6.QtCore as q, yaml, jsonschema, lxml, certifi, cryptography; print('PyQt6', q.PYQT_VERSION_STR, '· Qt', q.QT_VERSION_STR)"
	$(VENV)/bin/pytest --version
	$(VENV)/bin/ruff --version
