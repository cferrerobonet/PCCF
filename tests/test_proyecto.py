"""Comprobaciones del repositorio: versión y términos vetados."""
from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path

import pccf

RAIZ = Path(__file__).resolve().parents[1]
# Huella SHA-256 de los términos vetados, para no escribirlos aquí.
VETADOS = {"0615570f9ea136946c5dc08a250010320707646f57f72cedab1dfb73d95eade6"}
TEXTO = {".py", ".md", ".toml", ".txt", ".yml", ".yaml", ".json", ".sh", ".ps1", ".iss", ".spec", ".xml", ""}
#: Lo que no se versiona (.git/info/exclude): no cuenta.
FUERA = {".git", ".ruff_cache", ".pytest_cache", "build", "dist",
         }


def test_version_igual_en_pyproject_y_paquete():
    with open(RAIZ / "pyproject.toml", "rb") as f:
        assert tomllib.load(f)["project"]["version"] == pccf.__version__


def test_sin_terminos_vetados():
    def palabras(texto: str) -> set[str]:
        return {hashlib.sha256(p.encode()).hexdigest() for p in re.findall(r"\w+", texto)}

    culpables = []
    for f in RAIZ.rglob("*"):
        partes = f.relative_to(RAIZ).parts
        if not f.is_file() or partes[0] in FUERA or "__pycache__" in partes:
            continue
        if f.suffix.lower() not in TEXTO:
            continue
        if palabras(f.read_text(encoding="utf-8", errors="ignore")) & VETADOS:
            culpables.append(str(f.relative_to(RAIZ)))
    assert not culpables, f"Término vetado en: {culpables}"
