"""Medidas de la portada (ADR-021), como en Programaciones (su ADR-049): las siglas del ciclo, a la medida de su celda,
y el nombre del ciclo a su derecha con el mismo alto que las siglas, de lo alto de sus mayúsculas a la base de su
última línea. Las medidas de la letra (anchos, alto de las mayúsculas) se leen de los archivos de Barlow que lleva la
app, sin dependencias.
"""
from __future__ import annotations

import struct
from functools import lru_cache
from pathlib import Path

FUENTES = Path(__file__).resolve().parent / "recursos" / "fuentes"
LETRAS = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZáéíóúüñÁÉÍÓÚÜÑàèòçÇ0123456789"
          " .,;:-–—()/'’«»\"ºª&+·")

SIGLAS_PT = 178.0            # la letra de las siglas, si caben en su celda
ALTO_FILA_PT = 226.8         # la fila de las siglas y el nombre (4536 twips)
ANCHO_SIGLAS_PT = (6237 - 936 - 113) / 20     # su celda menos los márgenes
LETRA_NOMBRE = (14.0, 64.0)  # pt
INTERLINEADO_NOMBRE = (1.0, 1.35)   # en veces la letra
#: Con interlineado exacto, Word y LibreOffice ponen la base de la línea al 80 % de su alto; bajo las siglas queda este
#: aire hasta la banda de oro (pt). Medido en Programaciones (ADR-049).
BASE_EXACTO = 0.8
AIRE_BAJO_SIGLAS = 22.0


def medidas_fuente(datos: bytes, letras: str = LETRAS) -> dict:
    """Alto de las mayúsculas y ancho de cada letra, en fracción de em, de las tablas del TrueType (head, hhea, hmtx,
    OS/2 y cmap formato 4). Copia de la función de Programaciones."""
    tablas = {}
    for i in range(struct.unpack(">H", datos[4:6])[0]):
        tag, _suma, inicio, _largo = struct.unpack(">4sIII", datos[12 + 16 * i:28 + 16 * i])
        tablas[tag.decode("latin-1")] = inicio
    upm = struct.unpack(">H", datos[tablas["head"] + 18:tablas["head"] + 20])[0]
    n_metricas = struct.unpack(">H", datos[tablas["hhea"] + 34:tablas["hhea"] + 36])[0]
    mayus = struct.unpack(">h", datos[tablas["OS/2"] + 88:tablas["OS/2"] + 90])[0]
    cmap = tablas["cmap"]
    sub = None
    for i in range(struct.unpack(">H", datos[cmap + 2:cmap + 4])[0]):
        plataforma, codif, desplaz = struct.unpack(">HHI", datos[cmap + 4 + 8 * i:cmap + 12 + 8 * i])
        if (plataforma, codif) in ((3, 1), (0, 3), (0, 4)) and \
                struct.unpack(">H", datos[cmap + desplaz:cmap + desplaz + 2])[0] == 4:
            sub = cmap + desplaz
            break
    if sub is None:
        raise ValueError("la fuente no tiene tabla Unicode de formato 4")
    n = struct.unpack(">H", datos[sub + 6:sub + 8])[0] // 2
    fin = struct.unpack(f">{n}H", datos[sub + 14:sub + 14 + 2 * n])
    ini = struct.unpack(f">{n}H", datos[sub + 16 + 2 * n:sub + 16 + 4 * n])
    delta = struct.unpack(f">{n}h", datos[sub + 16 + 4 * n:sub + 16 + 6 * n])
    rango_pos = sub + 16 + 6 * n
    rango = struct.unpack(f">{n}H", datos[rango_pos:rango_pos + 2 * n])

    def glifo(c: int) -> int:
        for k in range(n):
            if ini[k] <= c <= fin[k]:
                if rango[k] == 0:
                    return (c + delta[k]) & 0xFFFF
                pos = rango_pos + 2 * k + rango[k] + 2 * (c - ini[k])
                g = struct.unpack(">H", datos[pos:pos + 2])[0]
                return (g + delta[k]) & 0xFFFF if g else 0
        return 0

    def ancho(g: int) -> int:
        i = min(g, n_metricas - 1)
        return struct.unpack(">H", datos[tablas["hmtx"] + 4 * i:tablas["hmtx"] + 4 * i + 2])[0]

    return {"cap": round(mayus / upm, 4), "anchos": {c: round(ancho(glifo(ord(c))) / upm, 4) for c in letras}}


@lru_cache(maxsize=1)
def medidas() -> dict:
    return {"siglas": medidas_fuente((FUENTES / "BarlowCondensed-ExtraBold.ttf").read_bytes()),
            "nombre": medidas_fuente((FUENTES / "BarlowCondensed-SemiBold.ttf").read_bytes())}


def letra_siglas(siglas: str) -> float:
    """La letra de las siglas: 178 pt o la que quepa en su celda."""
    letras = medidas()["siglas"]["anchos"]
    em = sum(letras.get(c, 0.5) for c in siglas) or 1
    return min(SIGLAS_PT, int(ANCHO_SIGLAS_PT * 0.97 / em * 2) / 2)


#: Palabras que no se quedan solas en una línea del nombre
CORTAS = {"y", "e", "o", "u", "a", "de", "del", "la", "el", "en", "las", "los"}


def medida_nombre(nombre: str, ancho_pt: float, siglas_pt: float) -> tuple[float, float, list[str]]:
    """(letra, interlineado en pt, líneas) con los que el nombre ocupa el alto de las mayúsculas de las siglas. Se
    parte en líneas con los anchos de cada letra y un margen para LibreOffice, que la dibuja algo más ancha, sin dejar
    sola en una línea una palabra corta («y», «de»…). Si ninguna letra da justo ese alto con un interlineado entre 1 y
    1,35 veces la letra, se toma la más grande cuyo bloque no pasa de ese alto (la última línea sigue apoyada en la
    base de las siglas)."""
    m = medidas()
    letras = m["nombre"]["anchos"]
    ancho_max = ancho_pt * 0.9
    alto = siglas_pt * m["siglas"]["cap"]
    mayus = m["nombre"]["cap"]
    minimo, maximo = INTERLINEADO_NOMBRE

    def ancho(t: str, s: float) -> float:
        return sum(letras.get(c, 0.55) for c in t) * s

    def partir(s: float) -> list[str] | None:
        out: list[str] = []
        for palabra in nombre.split():
            if ancho(palabra, s) > ancho_max:
                return None
            if out and ancho(f"{out[-1]} {palabra}", s) <= ancho_max:
                out[-1] = f"{out[-1]} {palabra}"
            else:
                out.append(palabra)
        if len(out) > 1 and any(linea.lower() in CORTAS for linea in out):
            return None
        return out

    tamanos = [x / 2 for x in range(int(LETRA_NOMBRE[1] * 2), int(LETRA_NOMBRE[0] * 2) - 1, -1)]
    for s in tamanos:   # justo el alto de las siglas
        lineas = partir(s)
        if lineas and len(lineas) >= 2:
            interlineado = (alto - mayus * s) / (len(lineas) - 1)
            if minimo * s <= interlineado <= maximo * s:
                return s, interlineado, lineas
    for s in tamanos:   # sin pasar de ese alto
        lineas = partir(s)
        if not lineas:
            continue
        if len(lineas) == 1:
            if mayus * s <= alto:
                return s, s * 1.1, lineas
            continue
        interlineado = min(max((alto - mayus * s) / (len(lineas) - 1), minimo * s), maximo * s)
        if mayus * s + (len(lineas) - 1) * interlineado <= alto:
            return s, interlineado, lineas
    s = LETRA_NOMBRE[0]
    return s, s * 1.1, partir(s) or [nombre]


def colocacion(siglas: str, nombre: str, ancho_nombre_pt: float) -> dict:
    """Todo lo que necesita la portada: letra e interlineado de las siglas y del nombre, sus líneas, el margen superior
    común de las dos celdas y el espacio antes del nombre para que su última línea apoye en la base de las siglas."""
    sp = letra_siglas(siglas)
    s, interlineado, lineas = medida_nombre(nombre, ancho_nombre_pt, sp)
    linea_siglas = round(sp * 1.1, 1)
    desfase = BASE_EXACTO * linea_siglas - BASE_EXACTO * interlineado - (len(lineas) - 1) * interlineado
    return {"siglas_pt": sp, "linea_siglas": linea_siglas, "nombre_pt": s, "interlineado": interlineado,
            "lineas": lineas, "arriba": max(0.0, ALTO_FILA_PT - linea_siglas - AIRE_BAJO_SIGLAS),
            "antes_nombre": max(0.0, desfase)}
