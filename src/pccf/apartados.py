"""Los apartados del PCCF por grado, con sus títulos literales (`recursos/apartados/`). Nada los da por supuestos."""
from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

CARPETA = Path(__file__).resolve().parent / "recursos" / "apartados"
ARCHIVO_POR_GRADO = {"GM": "gm-gs.yaml", "GS": "gm-gs.yaml"}


@dataclass(frozen=True)
class Apartado:
    n: int
    titulo: str
    tipos: tuple[str, ...]


@cache
def apartados(grado: str) -> tuple[Apartado, ...]:
    """Los apartados de un grado («GM», «GS»). Grado básico llega con la F4: hasta entonces, KeyError."""
    if grado not in ARCHIVO_POR_GRADO:
        raise KeyError(f"Sin lista de apartados para el grado {grado}")
    with open(CARPETA / ARCHIVO_POR_GRADO[grado], encoding="utf-8") as f:
        d = yaml.safe_load(f)
    return tuple(Apartado(n=a["n"], titulo=a["titulo"], tipos=tuple(a["tipos"])) for a in d["apartados"])


def apartado(grado: str, n: int) -> Apartado:
    for a in apartados(grado):
        if a.n == n:
            return a
    raise KeyError(f"El grado {grado} no tiene apartado {n}")
