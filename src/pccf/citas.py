"""Índice de citas (ARCHITECTURE.md §2): qué apartados y bloques del PCCF de un ciclo y un curso se apoyan en cada norma.

Dos clases de uso:
- **bloque**: la cabecera de un bloque de texto la cita (`citas:` con `norma` y `articulo`);
- **calculado**: un apartado que se calcula del catálogo depende de ella (1, del real decreto del título y del horario;
  2, de toda la normativa del ciclo; 3 y 4, de las competencias del título; 7, del horario; la lista de apartados, del
  decreto de currículos).

Un bloque cita por el id del catálogo («DOGV-C-2025-29742») o por el nombre («Decreto 114/2025», «Orden 20/2019»,
«Resolución de 16 de julio de 2026»). Una cita que no casa con una sola norma del catálogo queda **sin vigilar**: el
vigía no sabe nada de ella y lo dice; nunca se adivina a qué norma se refiere.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from pccf import apartados
from pccf.catalogo import Catalogo, Norma
from pccf.datos import CarpetaDatos


@dataclass(frozen=True)
class Uso:
    apartado: int | None    # None: la estructura del PCCF (la lista de apartados)
    titulo: str             # el del apartado, o «Estructura del PCCF»
    origen: str             # «bloque» o «calculado»
    detalle: str            # el bloque («centro/atencion-diversidad.md») o lo que se calcula («real decreto del título»)
    articulo: str = ""
    estado: str = ""        # el del bloque: «borrador» o «confirmado»


@dataclass
class Indice:
    usos: dict[str, list[Uso]] = field(default_factory=dict)          # id de la norma → usos
    sin_vigilar: dict[str, list[Uso]] = field(default_factory=dict)   # cita sin norma del catálogo → usos

    def anadir(self, ident: str, uso: Uso) -> None:
        lista = self.usos.setdefault(ident, [])
        if uso not in lista:
            lista.append(uso)


def _clave(t: str) -> str:
    """Para comparar una cita con un título: sin tildes, en minúsculas, sin la aclaración final entre paréntesis."""
    t = unicodedata.normalize("NFKD", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"\s*\([^)]*\)\s*$", "", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def candidatas(cat: Catalogo, cita: str) -> list[Norma]:
    """Las normas del catálogo que casan con una cita: por id o porque su título empieza por ella («Decreto 114/2025»
    casa con «DECRETO 114/2025, de 29 de julio…», no con «Real Decreto 114/2025» ni con «Decreto 114/20251»)."""
    if cita in cat.normas:
        return [cat.normas[cita]]
    k = _clave(cita)
    if not k:
        return []
    rx = re.compile(re.escape(k) + r"(?![\w/])")
    return [n for n in cat.normas.values() if rx.match(_clave(n.titulo))]


def resolver(cat: Catalogo, cita: str) -> Norma | None:
    """La norma de una cita si casa con una sola; si no casa con ninguna o con varias, None (sin vigilar)."""
    c = candidatas(cat, cita)
    return c[0] if len(c) == 1 else None


def indice(cat: Catalogo, datos: CarpetaDatos, sigla: str, curso: str) -> Indice:
    """El índice inverso norma → usos del PCCF de un ciclo y un curso."""
    ciclo = cat.ciclo(sigla)
    grado = ciclo["grado"]
    titulos = {a.n: a.titulo for a in apartados.apartados(grado)}
    idx = Indice()

    def calculado(ident: str | None, n: int | None, detalle: str) -> None:
        if not ident:
            return
        uso = Uso(apartado=n, titulo=titulos.get(n, "Estructura del PCCF"), origen="calculado", detalle=detalle)
        if ident in cat.normas:
            idx.anadir(ident, uso)
        else:
            idx.sin_vigilar.setdefault(ident, []).append(uso)

    calculado(apartados.norma(grado), None, "lista de apartados (art. 8.4)")
    rd = (ciclo.get("rd") or {}).get("id")
    fuentes = ciclo.get("fuentes") or {}
    calculado(rd, 1, "real decreto del título")
    calculado(fuentes.get("horario"), 1, "horas del currículo")
    for n in (3, 4):
        calculado(fuentes.get("competencias"), n, "competencias del título")
    calculado(fuentes.get("horario"), 7, "horas del currículo")
    for ambito in ("estatal", "autonomico"):
        for norma in cat.normativa(sigla, ambito, curso):
            calculado(norma.id, 2, "marco normativo del ciclo")

    for b in datos.bloques(sigla, curso):
        try:
            ruta = b.ruta.relative_to(datos.carpeta).as_posix()
        except ValueError:
            ruta = b.ruta.name
        for c in b.citas:
            uso = Uso(apartado=b.apartado, titulo=titulos.get(b.apartado, f"Apartado {b.apartado}"), origen="bloque",
                      detalle=ruta, articulo=str(c.get("articulo", "")), estado=b.estado)
            norma = resolver(cat, c["norma"])
            if norma:
                idx.anadir(norma.id, uso)
            else:
                idx.sin_vigilar.setdefault(c["norma"], []).append(uso)
    return idx
