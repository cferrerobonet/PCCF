"""Registro rotatorio de la aplicación y `faulthandler` (copia de `sistema.py` de Programaciones), en la carpeta de la
app de este equipo (`rutas.carpeta_app()/logs`)."""
from __future__ import annotations

import faulthandler
import logging
import logging.handlers
import sys
from datetime import date
from pathlib import Path

from pccf.rutas import carpeta_app

_falta = None


def configurar_registro() -> Path:
    global _falta
    carpeta = carpeta_app() / "logs"
    carpeta.mkdir(exist_ok=True)
    ruta = carpeta / f"app_{date.today():%Y%m%d}.log"
    manejador = logging.handlers.RotatingFileHandler(ruta, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    manejador.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    raiz.addHandler(manejador)
    if sys.stderr is not None and not getattr(sys, "frozen", False):
        raiz.addHandler(logging.StreamHandler())
    _falta = open(carpeta / "faulthandler.log", "a", encoding="utf-8")  # noqa: SIM115
    faulthandler.enable(_falta)
    return ruta
