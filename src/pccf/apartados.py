"""Los apartados del PCCF por grado, con sus títulos literales y el punto de la guía de la DGFP que dice qué pide cada uno
(`recursos/apartados/`, ADR-014). Nada los da por supuestos.

Cada apartado tiene su **clave** (`n`), la numeración de GM y GS, con la que lo citan los bloques y los datos, y su
**número** (`numero`), el que se ve en la app y en el documento. En GM y GS son iguales; en grado básico, que no tiene
el de Digitalización y Sostenibilidad, el número corre uno desde la tutoría (ADR-023)."""
from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

CARPETA = Path(__file__).resolve().parent / "recursos" / "apartados"
ARCHIVO_POR_GRADO = {"GB": "gb.yaml", "GM": "gm-gs.yaml", "GS": "gm-gs.yaml"}


@dataclass(frozen=True)
class Apartado:
    n: int                  # clave: la numeración de GM y GS
    titulo: str
    tipos: tuple[str, ...]
    guia: str               # punto de la guía de la DGFP: «2.3.3»
    pide: str               # lo que pide la guía, en una frase
    origen: str = "norma"   # «norma» (art. 8.4 del decreto del grado) o «guia» (lo añade la guía)
    numero: int = 0         # el que se ve; 0 = el de la clave
    decreto: str = "Decreto 114/2025"   # el de currículos de su grado, que fija los apartados (art. 8.4)

    def __post_init__(self):
        if not self.numero:
            object.__setattr__(self, "numero", self.n)


@cache
def apartados(grado: str) -> tuple[Apartado, ...]:
    """Los apartados de un grado («GB», «GM», «GS»), en su orden."""
    if grado not in ARCHIVO_POR_GRADO:
        raise KeyError(f"Sin lista de apartados para el grado {grado}")
    with open(CARPETA / ARCHIVO_POR_GRADO[grado], encoding="utf-8") as f:
        d = yaml.safe_load(f)
    return tuple(Apartado(n=a["n"], titulo=a["titulo"], tipos=tuple(a["tipos"]), guia=a["guia"], pide=a["pide"],
                          origen=a.get("origen", "norma"), numero=a.get("numero", 0), decreto=d["decreto"])
                 for a in d["apartados"])


@cache
def norma(grado: str) -> str:
    """Id de la norma que fija los apartados del grado (el decreto de currículos: art. 8.4)."""
    if grado not in ARCHIVO_POR_GRADO:
        raise KeyError(f"Sin lista de apartados para el grado {grado}")
    with open(CARPETA / ARCHIVO_POR_GRADO[grado], encoding="utf-8") as f:
        return yaml.safe_load(f)["norma"]


def decreto(grado: str) -> str:
    """«Decreto 114/2025» (GM y GS) o «Decreto 117/2025» (GB): el que fija los apartados del grado."""
    return apartados(grado)[0].decreto


def numero(grado: str, n: int) -> int:
    """El número que se ve del apartado de clave `n` en ese grado."""
    return apartado(grado, n).numero


def apartado(grado: str, n: int) -> Apartado:
    for a in apartados(grado):
        if a.n == n:
            return a
    raise KeyError(f"El grado {grado} no tiene apartado {n}")
