"""Los apartados del PCCF por grado, con sus títulos literales y el punto de la guía de la DGFP que dice qué pide cada uno
(`recursos/apartados/`, ADR-014). Nada los da por supuestos."""
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
    guia: str               # punto de la guía de la DGFP: «2.3.3»
    pide: str               # lo que pide la guía, en una frase
    origen: str = "norma"   # «norma» (art. 8.4 del decreto del grado) o «guia» (lo añade la guía)


@cache
def apartados(grado: str) -> tuple[Apartado, ...]:
    """Los apartados de un grado («GM», «GS»). Grado básico llega con la F4: hasta entonces, KeyError."""
    if grado not in ARCHIVO_POR_GRADO:
        raise KeyError(f"Sin lista de apartados para el grado {grado}")
    with open(CARPETA / ARCHIVO_POR_GRADO[grado], encoding="utf-8") as f:
        d = yaml.safe_load(f)
    return tuple(Apartado(n=a["n"], titulo=a["titulo"], tipos=tuple(a["tipos"]), guia=a["guia"], pide=a["pide"],
                          origen=a.get("origen", "norma")) for a in d["apartados"])


@cache
def norma(grado: str) -> str:
    """Id de la norma que fija los apartados del grado (el decreto de currículos: art. 8.4)."""
    if grado not in ARCHIVO_POR_GRADO:
        raise KeyError(f"Sin lista de apartados para el grado {grado}")
    with open(CARPETA / ARCHIVO_POR_GRADO[grado], encoding="utf-8") as f:
        return yaml.safe_load(f)["norma"]


def apartado(grado: str, n: int) -> Apartado:
    for a in apartados(grado):
        if a.n == n:
            return a
    raise KeyError(f"El grado {grado} no tiene apartado {n}")
