"""Plantilla del PCCF a partir de la de Programaciones (ADR-013): la misma identidad del centro, otra portada.

    python scripts/plantilla.py crear <carpeta «es» de la plantilla de Programaciones>
    python scripts/plantilla.py comprobar

De la plantilla de las programaciones se conservan estilos, numeración, tema, fuentes, encabezados, pies y la sección de
la portada. Cambia:
- la portada: «PROYECTO CURRICULAR DE CICLO FORMATIVO», departamento, horas del ciclo, jefatura y curso;
- la franja del encabezado: «Proyecto curricular» en lugar de «Programación didáctica»;
- el cuerpo: el título «ÍNDICE:», la marca `{{indice}}` (el índice lo escribe documento.py), un salto de página y la
  marca `{{cuerpo}}` (los apartados los escribe documento.py).
La plantilla generada no se edita a mano: se cambia este script y se vuelve a crear.
"""
from __future__ import annotations

import copy
import datetime as dt
import re
import sys
from pathlib import Path

import yaml
from lxml import etree

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pccf import ooxml  # noqa: E402
from pccf.ooxml import W  # noqa: E402

DESTINO = RAIZ / "src" / "pccf" / "recursos" / "plantilla"
MARCAS = {"familia", "grado", "ciclo", "departamento", "horas", "jefatura", "curso_escolar", "indice", "cuerpo",
          "correo_pie"}
RE_MARCA = re.compile(r"\{\{([^}]+)\}\}")


def _poner_texto(contenedor, texto: str) -> None:
    """Deja el texto en el primer w:t del contenedor y vacía los demás (conserva el formato del primer run)."""
    ts = list(contenedor.iter(W + "t"))
    ts[0].text = texto
    for t in ts[1:]:
        t.getparent().getparent().remove(t.getparent())


def _celdas(tabla) -> list[list]:
    return [tr.findall(W + "tc") for tr in tabla.findall(W + "tr")]


def _parrafo_marca(marca: str, estilo: str | None):
    p = etree.Element(W + "p")
    if estilo:
        ooxml.hijo(ooxml.ppr(p), "pStyle", ooxml.ORDEN_PPR, val=estilo)
    p.append(ooxml.run("{{%s}}" % marca))
    return p


def crear(origen: Path) -> None:
    pq = ooxml.Paquete.desde_carpeta(origen)
    doc = pq.xml("word/document.xml")
    body = doc.find(W + "body")
    hijos = list(body)
    texto = lambda e: ooxml.texto(e).strip()

    titulo = next(e for e in hijos if e.tag == W + "p" and texto(e) == "PROGRAMACIÓN DIDÁCTICA")
    tablas = [e for e in hijos if e.tag == W + "tbl"][:2]
    seccion = next(e for e in hijos if e.tag == W + "p" and e.find(f"{W}pPr/{W}sectPr") is not None)
    indice = next(e for e in hijos if e.tag == W + "p" and texto(e) == "ÍNDICE:")
    salto = next(e for e in hijos[hijos.index(indice):] if e.tag == W + "p"
                 and e.find(f".//{W}br[@{W}type='page']") is not None and not texto(e))
    final = hijos[-1]
    assert final.tag == W + "sectPr"

    _poner_texto(titulo, "PROYECTO CURRICULAR")   # en dos líneas: en una, Word lo parte con guion
    r = next(titulo.iter(W + "r"))
    r2 = copy.deepcopy(r)
    etree.SubElement(r, W + "br")
    r.addnext(r2)
    next(r2.iter(W + "t")).text = "DE CICLO FORMATIVO"
    a = _celdas(tablas[0])   # familia · ciclo · módulo → departamento · horas del módulo → del ciclo
    _poner_texto(a[2][0], "Departamento:")
    _poner_texto(a[2][1], "{{departamento}}")
    _poner_texto(a[3][0], "Horas del ciclo:")
    b = _celdas(tablas[1])   # profesorado → jefatura de departamento · curso académico
    _poner_texto(b[0][0], "Jefatura de departamento:")
    _poner_texto(b[0][1], "{{jefatura}}")

    portada = hijos[:hijos.index(seccion) + 1]
    for e in hijos:
        body.remove(e)
    body.extend(portada)
    body.append(indice)
    body.append(_parrafo_marca("indice", "TDC2"))
    body.append(copy.deepcopy(salto))
    body.append(_parrafo_marca("cuerpo", None))
    body.append(final)
    ooxml.limpiar_ids(body)
    pq.quitar_relaciones_huerfanas("word/document.xml")

    for n in sorted(pq.partes):
        if re.fullmatch(r"word/header\d+\.xml", n):
            raiz = pq.xml(n)
            for t in raiz.iter(W + "t"):
                if t.text and "Programación didáctica" in t.text:
                    t.text = t.text.replace("Programación didáctica", "Proyecto curricular")
    core = pq.xml("docProps/core.xml")
    for e in core.iter():
        if e.text and "Programación didáctica" in e.text:
            e.text = "Proyecto curricular de ciclo formativo"
        elif e.text == "Programaciones":   # autor y última modificación
            e.text = "PCCF"

    if DESTINO.exists():
        import shutil
        shutil.rmtree(DESTINO / "es", ignore_errors=True)
    pq.a_carpeta(DESTINO / "es")
    meta = {"version": dt.date.today().isoformat(),
            "origen": "Plantilla de Programaciones (src/programaciones/recursos/plantilla/es), portada del PCCF",
            "idiomas": ["es"], "vinetas": "8"}
    with open(DESTINO / "plantilla.yaml", "w", encoding="utf-8") as f:
        f.write("# Generado por scripts/plantilla.py crear: no se edita a mano.\n")
        yaml.safe_dump(meta, f, allow_unicode=True, sort_keys=False)
    errores = comprobar()
    print("Plantilla creada" if not errores else "\n".join(errores))


def comprobar() -> list[str]:
    """Marcas conocidas y enteras (cada una en un solo w:t), y nada de la programación didáctica."""
    pq = ooxml.Paquete.desde_carpeta(DESTINO / "es")
    errores = []
    vistas = set()
    for n in sorted(pq.partes):
        if not n.endswith(".xml"):
            continue
        raiz = pq.xml(n)
        for t in raiz.iter(W + "t"):
            for m in RE_MARCA.findall(t.text or ""):
                vistas.add(m)
                if m not in MARCAS:
                    errores.append(f"{n}: marca desconocida {{{{{m}}}}}")
        plano = "".join(raiz.itertext())
        if "{{" in plano and "{{" not in "".join(t.text or "" for t in raiz.iter(W + "t")):
            errores.append(f"{n}: marca partida en varios runs")
        if "Programación didáctica" in plano or "PROGRAMACIÓN DIDÁCTICA" in plano:
            errores.append(f"{n}: queda texto de la programación didáctica")
    faltan = MARCAS - vistas
    if faltan:
        errores.append(f"Faltan marcas: {sorted(faltan)}")
    return errores


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "crear":
        crear(Path(sys.argv[2]))
    elif len(sys.argv) == 2 and sys.argv[1] == "comprobar":
        errs = comprobar()
        print("\n".join(errs) or "Plantilla correcta")
        sys.exit(1 if errs else 0)
    else:
        print(__doc__)
        sys.exit(2)
