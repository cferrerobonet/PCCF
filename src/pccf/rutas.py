"""Dónde vive cada cosa: la carpeta propia de la app en este equipo y lo que va dentro de la app (también congelada)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

CARPETA = "PCCF"


def congelada() -> bool:
    """True dentro del ejecutable de PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def recursos() -> Path:
    """Tipografías, imágenes, plantilla y apartados: dentro del paquete o de la app congelada."""
    if congelada():
        return Path(sys._MEIPASS) / "pccf" / "recursos"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent / "recursos"


def carpeta_app() -> Path:
    """Carpeta de trabajo de la app en este equipo (conversión a PDF, vista previa). No guarda datos del PCCF: esos
    están en la carpeta de datos. `PCCF_APP` la cambia (pruebas)."""
    propia = os.environ.get("PCCF_APP")
    if propia:
        base = Path(propia)
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / CARPETA
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home()) / CARPETA
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / CARPETA
    base.mkdir(parents=True, exist_ok=True)
    return base
