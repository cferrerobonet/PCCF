"""El Word del PCCF (diseño propio, ADR-015) con la carpeta de datos y el catálogo ficticios."""
from __future__ import annotations

import datetime as dt
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


def test_plantilla_correcta_con_fuentes_incrustadas():
    assert plantilla.comprobar() == []


def test_fuentes_incrustadas_y_recuperables(res):
    p = partes(res.docx)
    assert b"embedTrueTypeFonts" in p["word/settings.xml"]
    tf = etree.fromstring(p["word/fontTable.xml"])
    rels = {r.get("Id"): r.get("Target") for r in etree.fromstring(p["word/_rels/fontTable.xml.rels"])}
    claves = [(e.get(ooxml.R + "id"), e.get(W + "fontKey")) for e in tf.iter() if
              isinstance(e.tag, str) and e.tag.split("}")[1].startswith("embed")]
    assert len(claves) == len(plantilla.FUENTES)
    for rid, clave in claves:
        assert plantilla.ofuscar(p["word/" + rels[rid]], clave)[:4] == b"\x00\x01\x00\x00"


def test_sin_marcas_y_con_los_apartados_en_orden(res):
    for n, x in partes(res.docx).items():
        if n.endswith(".xml"):
            assert b"{{" not in x, n
    titulos = textos(cuerpo(res.docx), ("ApTitulo",))
    esperados = [a.titulo for a in apartados.apartados("GS")]
    assert titulos[:2] == ["Control del documento", "Contenido"]
    assert titulos[2:2 + len(esperados)] == esperados
    assert len(titulos) == 2 + len(esperados) + 2   # y los anexos A y B
    numeros = [x for x in textos(cuerpo(res.docx), ("ApNumero",)) if x]
    assert numeros == [str(a.n) for a in apartados.apartados("GS")] + ["A", "B"]


def test_contenido_con_una_entrada_enlazada_por_apartado_y_anexo(res):
    body = cuerpo(res.docx)
    entradas = [p for p in body.iter(W + "p") if ooxml.estilo(p) == "IndiceEntrada"]
    assert len(entradas) == len(apartados.apartados("GS")) + 2
    marcas = {b.get(W + "name") for b in body.iter(W + "bookmarkStart")}
    assert {p.find(W + "hyperlink").get(W + "anchor") for p in entradas} <= marcas
    instr = " ".join(t.text for t in body.iter(W + "instrText"))
    assert "TOC " not in instr and instr.count("PAGEREF") == len(entradas)
    assert b"updateFields" in partes(res.docx)["word/settings.xml"]
    pendientes = [p for p in entradas if "pendiente" in ooxml.texto(p)]
    assert pendientes and all("Atención a la Diversidad" not in ooxml.texto(p) for p in pendientes)


def test_portada_y_secciones(res):
    body = cuerpo(res.docx)
    plano = ooxml.texto(body)
    for x in ("Proyecto curricular", "de ciclo formativo", "PRU", "Departamento de Pruebas", "Jefa Ficticia",
              "Grado Superior", f"Curso {CURSO}", "Borrador · pendiente de aprobación"):
        assert x in plano, x
    sects = list(body.iter(W + "sectPr"))
    portada = sects[0]
    assert portada.find(W + "pgMar").get(W + "left") == "0"
    assert portada.find(W + "footerReference").get(ooxml.R + "id") == "rIdPiePortada"
    assert any(s.find(W + "pgSz").get(W + "orient") == "landscape" for s in sects)   # la matriz del 4


def test_apartado_1_equipo_y_pendientes(res):
    plano = ooxml.texto(cuerpo(res.docx))
    assert "Docente Uno / Docente Dos" in plano and "1PRU: Docente Uno" in plano
    assert any("OPT-PRU-B" in a for a in res.avisos)    # optativa sin docente


def test_apartado_2_normas_enlazadas(res):
    rels = partes(res.docx)["word/_rels/document.xml.rels"].decode()
    assert "https://www.boe.es/buscar/doc.php?id=BOE-A-2000-1" in rels and "https://dogv.gva.es/" in rels
    normas = " ".join(textos(cuerpo(res.docx), ("Vineta",)))
    assert "2029-2030" not in normas   # la resolución de otro curso no entra


def test_apartado_4_matriz_con_celdas_rellenas(res):
    body = cuerpo(res.docx)
    verde = documento.metadatos_plantilla()["colores"]["v7"]
    rellenas = [s for s in body.iter(W + "shd") if s.get(W + "fill") == verde]
    assert len(rellenas) == 3   # 9001: a y b; 9002: c


def test_pendiente_dice_lo_que_pide_la_guia(res):
    plano = ooxml.texto(cuerpo(res.docx))
    assert f"La guía pide: {apartados.apartado('GS', 6).pide}" in plano
    assert "Guía DGFP · 2.3.5" in plano


def test_bloques_y_borrador(res):
    plano = ooxml.texto(cuerpo(res.docx))
    assert "Texto ficticio de atención a la diversidad." in plano
    assert res.borrador and any("diversidad.md" in a and "borrador" in a for a in res.avisos)
    encabezado = partes(res.docx)["word/header1.xml"].decode()
    assert ">Borrador<" in encabezado
    assert not any(b"MarcaBorrador" in x for x in partes(res.docx).values())   # sin marca de agua


def test_sin_borrador_si_se_pide(cat, datos):
    r = documento.generar(cat, datos, "PRU", CURSO, documento.Opciones(borrador=False))
    assert not r.borrador
    assert "Borrador" not in partes(r.docx)["word/header1.xml"].decode()
    assert "pendiente de aprobación" not in ooxml.texto(cuerpo(r.docx))


def test_correo_del_pie_de_portada(cat, datos):
    r = documento.generar(cat, datos, "PRU", CURSO, documento.Opciones(correo_pie="dpto@example.com"))
    assert b"dpto@example.com" in partes(r.docx)["word/footer2.xml"]


def test_markdown_de_un_bloque():
    e = documento.Escritor(documento.cargar_plantilla())
    subtitulos: list[int] = []
    elems = e.markdown("Uno **dos** [tres](https://example.com).\n\n> [!WARNING] Nota interna\n\n### Sub\n- viñeta\n",
                       16, subtitulos)
    textos_ = [ooxml.normal(ooxml.texto(x)) for x in elems]
    assert textos_ == ["Uno dos tres.", "16.1 Sub", "viñeta"]
    assert elems[0].find(f".//{W}hyperlink") is not None
    assert [ooxml.estilo(x) for x in elems] == ["Texto", "Subapartado", "Vineta"]


def test_mismo_contenido_mismos_bytes(cat, datos):
    op = documento.Opciones(fecha=dt.date(2030, 1, 1))
    assert documento.generar(cat, datos, "PRU", CURSO, op).docx == documento.generar(cat, datos, "PRU", CURSO, op).docx
