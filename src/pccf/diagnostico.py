"""Comprobación de lo que la app lleva dentro (sin Qt): catálogo, apartados, esquemas, plantilla, tipografías y la
clave del catálogo publicado. Además genera un PCCF de verdad con una carpeta de datos vacía: todo pendiente.

La usa la prueba de arranque de la app compilada (`PCCF_PRUEBA_DE_ARRANQUE`, `compilar.yml`): que el ejecutable exista
no basta, también tiene que encontrar y leer sus datos. Cada línea que devuelve va al registro con la marca
`MARCA_DATOS`, y la CI la busca.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from pccf import apartados, documento, esquemas, firma
from pccf.catalogo import Catalogo
from pccf.datos import CarpetaDatos
from pccf.rutas import recursos

MARCA_DATOS = "PRUEBA DE ARRANQUE: datos empaquetados"
PARTES_PLANTILLA = ("[Content_Types].xml", "_rels/.rels", "word/document.xml", "word/_rels/document.xml.rels")


def comprobar_datos(catalogo: Catalogo | None = None) -> list[str]:
    """Lee todo lo empaquetado y devuelve una línea por pieza. Lanza una excepción si falta algo."""
    cat = catalogo or Catalogo()
    siglas = cat.siglas()
    if not siglas:
        raise FileNotFoundError(f"El catálogo de {cat.carpeta} no tiene ciclos")
    muestra = next((s for s in siglas if cat.ciclo(s)["grado"] in ("GM", "GS")), None)
    if muestra is None:
        raise FileNotFoundError("El catálogo no tiene ningún ciclo de grado medio o superior")
    n_apartados = len(apartados.apartados(cat.ciclo(muestra)["grado"]))
    paquete = documento.cargar_plantilla()
    faltan = [p for p in PARTES_PLANTILLA if p not in paquete.partes]
    if faltan:  # «_rels/.rels» empieza por punto: un empaquetador que se salte los ocultos la rompe
        raise FileNotFoundError(f"A la plantilla le faltan {', '.join(faltan)}")
    for nombre in ("bloque", "equipo", "departamentos"):
        esquemas.errores(nombre, {}, nombre)   # carga el esquema: si no está, lanza
    with tempfile.TemporaryDirectory(prefix="pccf-diagnostico-") as tmp:
        res = documento.generar(cat, CarpetaDatos(Path(tmp)), muestra, "2030-2031")
    fuentes = sorted(p.name for p in (recursos() / "fuentes").glob("*.ttf"))
    if not fuentes:
        raise FileNotFoundError("No hay tipografías en los recursos")
    clave = firma.clave_publica()
    if firma.verificar({"prueba": 1}, "AAAA"):   # además carga cryptography, que la app compilada tiene que llevar
        raise ValueError("Una firma falsa del catálogo se ha dado por buena")
    return [
        f"catálogo {cat.version}: {len(siglas)} ciclos",
        f"{n_apartados} apartados de {cat.ciclo(muestra)['grado']}; esquemas de bloque, equipo y departamentos",
        f"plantilla con {len(paquete.partes)} partes; PCCF de {muestra} generado ({len(res.docx) // 1024} KB, "
        f"{'borrador' if res.borrador else 'sin borrador'})",
        f"{len(fuentes)} tipografías",
        f"clave pública del catálogo publicado {firma.id_clave(clave)} (Ed25519, verificación lista)",
    ]
