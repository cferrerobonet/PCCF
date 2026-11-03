"""Esquemas JSON de los archivos de la carpeta de datos y su validación."""
from __future__ import annotations

import datetime as dt
import json
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator

CARPETA = Path(__file__).resolve().parent


@cache
def validador(nombre: str) -> Draft202012Validator:
    with open(CARPETA / f"{nombre}.json", encoding="utf-8") as f:
        return Draft202012Validator(json.load(f))


def sin_fechas(dato):
    """YAML convierte «2026-11-03» en una fecha: para validar y guardar, se vuelve a texto AAAA-MM-DD."""
    if isinstance(dato, dict):
        return {k: sin_fechas(v) for k, v in dato.items()}
    if isinstance(dato, list):
        return [sin_fechas(v) for v in dato]
    if isinstance(dato, dt.date):
        return dato.isoformat()
    return dato


def errores(nombre: str, dato, origen: str) -> list[str]:
    """Los errores de `dato` contra el esquema `nombre`, uno por línea y con el archivo de origen."""
    out = []
    for e in sorted(validador(nombre).iter_errors(dato), key=lambda e: list(e.absolute_path)):
        ruta = "/".join(str(p) for p in e.absolute_path) or "(raíz)"
        out.append(f"{origen}: {ruta}: {e.message}")
    return out
