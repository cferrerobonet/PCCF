"""El Word del PCCF con la carpeta de datos y el catálogo ficticios."""
from __future__ import annotations

import io
import zipfile

import pytest
from lxml import etree

import plantilla
from pccf import apartados, documento, ooxml
from pccf.ooxml import W

from .conftest import CURSO


def partes(docx: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(docx)) as z:
        return {n: z.read(n) for n in z.namelist()}


def cuerpo(docx: bytes):
    return etree.fromstring(partes(docx)["word/document.xml"]).find(W + "body")


def textos(body, estilos: tuple[str, ...]) -> list[str]:
    return [ooxml.normal(ooxml.texto(p)) for p in body.iter(W + "p") if ooxml.estilo(p) in estilos]


@pytest.fixture
def res(cat, datos):
    return documento.generar(cat, datos, "PRU", CURSO)


def test_plantilla_correcta():
    assert plantilla.comprobar() == []


def test_sin_marcas_y_con_los_18_apartados_en_orden(res):
    for n, x in partes(res.docx).items():
        if n.endswith(".xml"):
            assert b"{{" not in x, n
    body = cuerpo(res.docx)
    principales = textos(body, ("Ttulo2",))
    assert principales == [f"{a.n}. {a.titulo}" for a in apartados.apartados("GS")]


def test_indice_con_una_entrada_enlazada_por_titulo(res):
    body = cuerpo(res.docx)
    titulos = textos(body, ("Ttulo2", "Ttulo3"))
    entradas = [p for p in body.iter(W + "p") if ooxml.estilo(p) in ("TDC2", "TDC3") and p.find(W + "hyperlink") is not None]
    assert [ooxml.normal(ooxml.texto(p)) for p in entradas] == titulos
    marcas = {b.get(W + "name") for b in body.iter(W + "bookmarkStart")}
    assert {p.find(W + "hyperlink").get(W + "anchor") for p in entradas} <= marcas
    instr = " ".join(t.text for t in body.iter(W + "instrText"))
    assert instr.count("TOC ") == 1 and instr.count("PAGEREF") == len(entradas)
    assert b"updateFields" in partes(res.docx)["word/settings.xml"]


def test_portada(res):
    plano = ooxml.texto(cuerpo(res.docx))
    for x in ("PROYECTO CURRICULAR", "Departamento de Pruebas", "Jefa Ficticia", "Grado Superior",
              "PRU – Pruebas automatizadas", "333", CURSO):
        assert x in plano, x


def test_apartado_1_equipo_y_pendientes(res):
    plano = ooxml.texto(cuerpo(res.docx))
    assert "Docente Uno / Docente Dos" in plano and "1PRU: Docente Uno" in plano
    assert any("OPT-PRU-B" in a for a in res.avisos)    # optativa sin docente


def test_apartado_2_normas_enlazadas(res):
    rels = partes(res.docx)["word/_rels/document.xml.rels"].decode()
    assert "https://www.boe.es/buscar/doc.php?id=BOE-A-2000-1" in rels and "https://dogv.gva.es/" in rels
    assert "2029-2030" not in ooxml.texto(cuerpo(res.docx))   # la resolución de otro curso no entra


def test_apartado_4_tabla_de_contribucion(res):
    body = cuerpo(res.docx)
    tabla = next(t for t in body.iter(W + "tbl") if "Módulo profesional" in ooxml.texto(t) and " a " in
                 " " + " ".join(ooxml.texto(c) for c in t.find(W + "tr").iter(W + "tc")) + " ")
    marcas = sum(1 for c in tabla.iter(W + "tc") if ooxml.texto(c) == "X")
    assert marcas == 3   # 9001: a y b; 9002: c


def test_bloques_y_borrador(res):
    plano = ooxml.texto(cuerpo(res.docx))
    assert "Texto ficticio de atención a la diversidad." in plano
    assert "Pendiente." in plano
    assert res.borrador and any("diversidad.md" in a and "borrador" in a for a in res.avisos)
    assert any(b"MarcaBorrador" in x for n, x in partes(res.docx).items() if "header" in n)


def test_sin_borrador_si_se_pide(cat, datos):
    r = documento.generar(cat, datos, "PRU", CURSO, documento.Opciones(borrador=False))
    assert not r.borrador and not any(b"MarcaBorrador" in x for x in partes(r.docx).values())


def test_correo_del_pie(cat, datos):
    r = documento.generar(cat, datos, "PRU", CURSO, documento.Opciones(correo_pie="dpto@example.com"))
    assert any(b"dpto@example.com" in x for n, x in partes(r.docx).items() if "footer" in n)


def test_markdown_de_un_bloque(cat, datos):
    e = documento.Escritor(documento.cargar_plantilla(), "8")
    subtitulos: list[int] = []
    elems = e.markdown("Uno **dos** [tres](https://example.com).\n\n> [!WARNING] Nota interna\n\n### Sub\n- viñeta\n",
                       16, subtitulos)
    textos_ = [ooxml.texto(x) for x in elems]
    assert textos_ == ["Uno dos tres.", "16.1. Sub", "viñeta"]
    assert elems[0].find(f".//{W}hyperlink") is not None and elems[0].find(f".//{W}b") is not None
    assert ooxml.estilo(elems[1]) == "Ttulo3" and ooxml.numeracion(elems[2]) == ("8", 0)


def test_mismo_contenido_mismos_bytes(cat, datos):
    import datetime as dt
    op = documento.Opciones(fecha=dt.date(2030, 1, 1))
    assert documento.generar(cat, datos, "PRU", CURSO, op).docx == documento.generar(cat, datos, "PRU", CURSO, op).docx
