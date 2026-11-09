"""Plantilla del PCCF con diseño propio (ADR-015), construida desde cero: estilos, viñetas, encabezados, pies, escudo y
las fuentes Barlow incrustadas (licencia OFL). El diseño está en DESIGN.md § Documento.

    python scripts/plantilla.py crear
    python scripts/plantilla.py comprobar

La plantilla generada (`src/pccf/recursos/plantilla/es/`) no se edita a mano: se cambia este script y se vuelve a
crear. El cuerpo (portada, control del documento, contenido, apartados y anexos) lo escribe `documento.py`.
"""
from __future__ import annotations

import datetime as dt
import re
import shutil
import sys
import uuid
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pccf import ooxml  # noqa: E402
from pccf.ooxml import W  # noqa: E402

RECURSOS = RAIZ / "src" / "pccf" / "recursos"
DESTINO = RECURSOS / "plantilla"
MARCAS = {"sigla", "curso", "borrador", "cuerpo", "correo_pie", "decreto_pie"}
RE_MARCA = re.compile(r"\{\{([^}]+)\}\}")

# -- tokens (DESIGN.md § Documento) ----------------------------------------------------------------------------------
C = {"v9": "14401A", "v7": "206028", "oro": "C98A1E", "oro_t": "8A5A0B", "t": "1E2420", "t2": "47504A",
     "t3": "6E7771", "l": "D5DBD6", "l2": "ECEFEC", "blanco": "FFFFFF"}
#: Familias de Word (nombre 1 de la tabla «name» de cada archivo) y su ranura de incrustación
FUENTES = [("Barlow-Regular.ttf", "Barlow", "Regular"), ("Barlow-Bold.ttf", "Barlow", "Bold"),
           ("Barlow-Italic.ttf", "Barlow", "Italic"), ("Barlow-SemiBold.ttf", "Barlow SemiBold", "Regular"),
           ("BarlowCondensed-SemiBold.ttf", "Barlow Condensed SemiBold", "Regular"),
           ("BarlowCondensed-Bold.ttf", "Barlow Condensed", "Bold"),
           ("BarlowCondensed-ExtraBold.ttf", "Barlow Condensed ExtraBold", "Regular")]
TEXTO = "Barlow"
SEMI = "Barlow SemiBold"
COND = "Barlow Condensed"            # siempre en negrita (solo está la Bold)
COND_SEMI = "Barlow Condensed SemiBold"
COND_EXTRA = "Barlow Condensed ExtraBold"

# -- página (twips: 1 mm = 56,7) -------------------------------------------------------------------------------------
A4 = (11906, 16838)
MARGENES = {"top": 1361, "right": 1021, "bottom": 1361, "left": 1134, "header": 624, "footer": 567}   # 24·18·24·20
ANCHO = A4[0] - MARGENES["left"] - MARGENES["right"]          # 9751: 172 mm
COL_MARGEN = 1928                                             # 34 mm
SANGRIA = 2268                                                # 34 + 6 mm: columna de texto

NS_DECL = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')
NS_DIBUJO = ('xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
             'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
             'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')
TIPO_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'


def clave_fuente(archivo: str) -> str:
    """GUID fijo por archivo: la misma plantilla da los mismos bytes."""
    return "{%s}" % str(uuid.uuid5(uuid.NAMESPACE_URL, f"pccf/fuentes/{archivo}")).upper()


def ofuscar(datos: bytes, clave: str) -> bytes:
    """Fuente incrustada de Word (ECMA-376, parte 1, 17.8.1): los 32 primeros bytes, XOR con la clave al revés."""
    k = bytes.fromhex(clave.strip("{}").replace("-", ""))[::-1]
    b = bytearray(datos)
    for i in range(32):
        b[i] ^= k[i % 16]
    return bytes(b)


# -- estilos ---------------------------------------------------------------------------------------------------------
def rpr(fuente: str | None = None, sz: float | None = None, color: str | None = None, b: bool = False,
        i: bool = False, caps: bool = False, esp: int | None = None, u: bool = False) -> str:
    """rPr en el orden del esquema. `sz` en puntos; `esp`: espaciado entre letras en veinteavos de punto."""
    x = ""
    if fuente:
        x += f'<w:rFonts w:ascii="{fuente}" w:hAnsi="{fuente}" w:cs="{fuente}"/>'
    x += "<w:b/><w:bCs/>" if b else ""
    x += "<w:i/><w:iCs/>" if i else ""
    x += "<w:caps/>" if caps else ""
    x += f'<w:color w:val="{C.get(color, color)}"/>' if color else ""
    x += f'<w:spacing w:val="{esp}"/>' if esp else ""
    if sz:
        x += f'<w:sz w:val="{round(sz * 2)}"/><w:szCs w:val="{round(sz * 2)}"/>'
    x += '<w:u w:val="single"/>' if u else ""
    return f"<w:rPr>{x}</w:rPr>" if x else ""


def ppr(antes: int = 0, despues: int = 0, linea: int | None = None, ind: tuple[int, int] | None = None,
        tabs: list[tuple[str, int]] | None = None, keep: bool = False, nivel: int | None = None, borde: str = "",
        jc: str | None = None, sin_guiones: bool = False) -> str:
    """pPr en el orden del esquema. `linea`: interlineado en 240avos (auto); `ind`: (izquierda, francesa)."""
    x = "<w:keepNext/>" if keep else ""
    x += borde
    if tabs:
        x += "<w:tabs>" + "".join(f'<w:tab w:val="{v}" w:pos="{p}"/>' for v, p in tabs) + "</w:tabs>"
    x += "<w:suppressAutoHyphens/>" if sin_guiones else ""
    x += f'<w:spacing w:before="{antes}" w:after="{despues}"'
    x += f' w:line="{linea}" w:lineRule="auto"/>' if linea else "/>"
    if ind:
        x += f'<w:ind w:left="{ind[0]}"' + (f' w:hanging="{ind[1]}"/>' if ind[1] else "/>")
    x += f'<w:jc w:val="{jc}"/>' if jc else ""
    x += f'<w:outlineLvl w:val="{nivel}"/>' if nivel is not None else ""
    return f"<w:pPr>{x}</w:pPr>"


def estilo_p(sid: str, nombre: str, p: str, r: str, base: str = "Normal", sig: str | None = None) -> str:
    s = f'<w:style w:type="paragraph" w:customStyle="1" w:styleId="{sid}"><w:name w:val="{nombre}"/>'
    s += f'<w:basedOn w:val="{base}"/>' if base else ""
    s += f'<w:next w:val="{sig}"/>' if sig else ""
    return s + f'<w:qFormat/>{p}{r}</w:style>'


def estilo_c(sid: str, nombre: str, r: str) -> str:
    return f'<w:style w:type="character" w:customStyle="1" w:styleId="{sid}"><w:name w:val="{nombre}"/>{r}</w:style>'


def estilos() -> str:
    linea_inf = f'<w:pBdr><w:bottom w:val="single" w:sz="4" w:space="3" w:color="{C["l2"]}"/></w:pBdr>'
    out = [
        '<w:docDefaults><w:rPrDefault>' + rpr(TEXTO, 9.5, "t")[:-8] +
        '<w:lang w:val="es-ES" w:eastAsia="es-ES" w:bidi="ar-SA"/></w:rPr></w:rPrDefault>'
        '<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault>'
        '</w:docDefaults>',
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:widowControl/></w:pPr></w:style>',
        '<w:style w:type="character" w:default="1" w:styleId="Fuentedeprrafopredeter">'
        '<w:name w:val="Default Paragraph Font"/><w:uiPriority w:val="1"/><w:semiHidden/></w:style>',
        '<w:style w:type="table" w:default="1" w:styleId="Tablanormal"><w:name w:val="Normal Table"/>'
        '<w:semiHidden/><w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar>'
        '<w:top w:w="0" w:type="dxa"/><w:left w:w="0" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/>'
        '<w:right w:w="0" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>',
        '<w:style w:type="numbering" w:default="1" w:styleId="Sinlista"><w:name w:val="No List"/>'
        '<w:semiHidden/></w:style>',
        # texto
        estilo_p("Texto", "Texto", ppr(despues=150, linea=348, ind=(SANGRIA, 0)), ""),
        estilo_p("Vineta", "Viñeta", ppr(despues=70, linea=336, ind=(SANGRIA + 227, 227)).replace(
            "<w:pPr>", '<w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'), "", base="Texto"),
        estilo_p("Cita", "Cita de norma", ppr(antes=60, despues=60, linea=312, ind=(SANGRIA + 340, 0)),
                 rpr(i=True, color="t2", sz=9.3), base="Texto"),
        estilo_p("CitaFuente", "Fuente de la cita", ppr(despues=200, ind=(SANGRIA + 340, 0)),
                 rpr(COND_SEMI, 7.5, "v7", caps=True, esp=12)),
        estilo_p("Fuente", "Fuente de los datos", ppr(antes=100, despues=220, linea=264), rpr(sz=7.5, color="t3")),
        # apertura de apartado
        estilo_p("ApNumero", "Número de apartado", ppr(keep=True, linea=216), rpr(COND_EXTRA, 46, "v7")),
        estilo_p("ApRegla", "Filete de apartado", ppr(antes=40, keep=True, ind=(0, 0), borde=(
            f'<w:pBdr><w:top w:val="single" w:sz="10" w:space="1" w:color="{C["oro"]}"/></w:pBdr>')), rpr(sz=2)),
        estilo_p("ApTitulo", "Título de apartado", ppr(keep=True, linea=250, nivel=0, sin_guiones=True),
                 rpr(COND, 19, "v9", b=True), sig="ApBase"),
        estilo_p("ApBase", "Base del apartado", ppr(antes=90, keep=True, linea=264, sin_guiones=True), rpr(COND_SEMI, 7.5, "t3",
                                                                                         caps=True, esp=14)),
        estilo_p("Subapartado", "Subapartado", ppr(antes=340, despues=130, keep=True, ind=(SANGRIA, SANGRIA),
                                                   tabs=[("right", COL_MARGEN), ("left", SANGRIA)], nivel=1,
                                                   sin_guiones=True),
                 rpr(SEMI, 11, "t"), sig="Texto"),
        # tablas
        estilo_p("TablaTexto", "Texto de tabla", ppr(linea=252), rpr(sz=8.5)),
        estilo_p("TablaCabecera", "Cabecera de tabla", ppr(linea=240, sin_guiones=True), rpr(COND_SEMI, 7.5, "v9", caps=True, esp=12)),
        estilo_p("TablaGrupo", "Grupo de tabla", ppr(linea=240, sin_guiones=True), rpr(COND, 8, "v7", b=True, caps=True, esp=14)),
        estilo_p("TablaEtiqueta", "Etiqueta de ficha", ppr(linea=240, sin_guiones=True), rpr(COND_SEMI, 7.5, "v7", caps=True, esp=12)),
        # contenido
        estilo_p("IndiceEntrada", "Entrada del contenido", ppr(antes=50, despues=50, linea=252, ind=(SANGRIA, SANGRIA),
                 tabs=[("right", COL_MARGEN), ("left", SANGRIA), ("right", ANCHO)], borde=linea_inf), rpr(sz=9.3)),
        estilo_p("IndiceGrupo", "Grupo del contenido", ppr(antes=260, despues=40, ind=(SANGRIA, 0), keep=True),
                 rpr(COND_SEMI, 7.5, "t3", caps=True, esp=14)),
        # encabezado y pie
        estilo_p("Encabezado", "Encabezado PCCF", ppr(), rpr(COND_SEMI, 7.5, "v7", caps=True, esp=14)),
        estilo_p("Pie", "Pie PCCF", ppr(), rpr(sz=7.4, color="t3")),
        # caracteres
        estilo_c("Hipervnculo", "Hipervínculo", rpr(color="t")[:-8] + '<w:u w:val="single" w:color="9CC2A1"/></w:rPr>'),
        estilo_c("SubNumero", "Número de subapartado", rpr(COND, 11, "v7", b=True)),
        estilo_c("IndiceNumero", "Número del contenido", rpr(COND, 12, "v7", b=True)),
        estilo_c("IndicePagina", "Página del contenido", rpr(COND_SEMI, 9.5, "t2")),
        estilo_c("MarcaPendiente", "Marca pendiente", rpr(COND, 7, "oro_t", b=True, caps=True, esp=14)),
        estilo_c("Codigo", "Código", rpr(COND_SEMI, 8, "t2")),
        estilo_c("PieNumero", "Número de página", rpr(COND, 15, "v7", b=True)),
        estilo_c("PieTotal", "Total de páginas", rpr(COND_SEMI, 8, "t3")),
        estilo_c("Destacado", "Destacado", rpr(b=True, color="v9")),
    ]
    return XML + f'<w:styles {NS_DECL}>' + "".join(out) + "</w:styles>"


def numeracion() -> str:
    return (XML + f'<w:numbering {NS_DECL}><w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="singleLevel"/>'
            '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/>'
            f'<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="{SANGRIA + 227}" w:hanging="227"/></w:pPr>'
            f'{rpr(TEXTO, color="v7")}</w:lvl></w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
            '</w:numbering>')


def ajustes() -> str:
    return (XML + f'<w:settings {NS_DECL}><w:zoom w:percent="100"/><w:embedTrueTypeFonts/>'
            '<w:defaultTabStop w:val="709"/><w:autoHyphenation/><w:hyphenationZone w:val="425"/>'
            '<w:characterSpacingControl w:val="doNotCompress"/><w:compat>'
            '<w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/>'
            '</w:compat><w:themeFontLang w:val="es-ES"/><w:decimalSymbol w:val=","/><w:listSeparator w:val=";"/>'
            '</w:settings>')


def tabla_fuentes(ids: dict[str, list[tuple[str, str, str]]]) -> str:
    """fontTable con las fuentes incrustadas: {familia: [(ranura, rId, clave)]}."""
    out = []
    for familia, lista in ids.items():
        x = f'<w:font w:name="{familia}"><w:charset w:val="00"/><w:family w:val="swiss"/><w:pitch w:val="variable"/>'
        for ranura in ("Regular", "Bold", "Italic", "BoldItalic"):
            for r, rid, clave in lista:
                if r == ranura:
                    x += f'<w:embed{ranura} r:id="{rid}" w:fontKey="{clave}"/>'
        out.append(x + "</w:font>")
    return XML + f'<w:fonts {NS_DECL}>' + "".join(out) + "</w:fonts>"


# -- encabezados y pies ----------------------------------------------------------------------------------------------
def _p(texto: str, estilo: str | None = None, r: str = "", p_extra: str = "") -> str:
    ps = f'<w:pStyle w:val="{estilo}"/>' if estilo else ""
    pp = f"<w:pPr>{ps}{p_extra}</w:pPr>" if ps or p_extra else ""
    t = f'<w:r>{r}<w:t xml:space="preserve">{texto}</w:t></w:r>' if texto else ""
    return f"<w:p>{pp}{t}</w:p>"


def _campo(instr: str, r: str = "", muestra: str = "1") -> str:
    return (f'<w:r>{r}<w:fldChar w:fldCharType="begin"/></w:r><w:r>{r}<w:instrText xml:space="preserve"> {instr} '
            f'</w:instrText></w:r><w:r>{r}<w:fldChar w:fldCharType="separate"/></w:r><w:r>{r}<w:t>{muestra}</w:t></w:r>'
            f'<w:r>{r}<w:fldChar w:fldCharType="end"/></w:r>')


def _tabla_2(c1: str, c2: str, ancho2: int, abajo: bool = False, borde_inf: bool = False) -> str:
    """Tabla al 100 % de la caja de la sección, sin bordes salvo el inferior opcional."""
    bi = (f'<w:tcBorders><w:bottom w:val="single" w:sz="4" w:space="0" w:color="{C["l"]}"/></w:tcBorders>'
          if borde_inf else "")
    va = '<w:vAlign w:val="bottom"/>' if abajo else ""
    mar = '<w:tcMar><w:bottom w:w="45" w:type="dxa"/></w:tcMar>' if borde_inf else ""
    return ('<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/><w:tblLayout w:type="autofit"/></w:tblPr>'
            f'<w:tblGrid><w:gridCol w:w="{ANCHO - ancho2}"/><w:gridCol w:w="{ancho2}"/></w:tblGrid><w:tr>'
            f'<w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/>{bi}{mar}{va}</w:tcPr>{c1}</w:tc>'
            f'<w:tc><w:tcPr><w:tcW w:w="{ancho2}" w:type="dxa"/>{bi}{mar}{va}</w:tcPr>{c2}</w:tc></w:tr></w:tbl>')


def encabezado() -> str:
    marca = rpr(COND, 7.5, "t", b=True, caps=True, esp=14)[:-8] + f'<w:shd w:val="clear" w:color="auto" w:fill="{C["oro"]}"/></w:rPr>'
    c1 = _p("Proyecto curricular · {{sigla}} · {{curso}}", "Encabezado")
    c2 = _p("{{borrador}}", "Encabezado", marca, '<w:jc w:val="right"/>')
    return (XML + f'<w:hdr {NS_DECL}>' + _tabla_2(c1, c2, 2835, borde_inf=True) +
            _p("", None, "", '<w:spacing w:after="0" w:line="120" w:lineRule="exact"/>') + "</w:hdr>")


def pie() -> str:
    r_pie = '<w:rPr><w:rStyle w:val="PieNumero"/></w:rPr>'
    r_tot = '<w:rPr><w:rStyle w:val="PieTotal"/></w:rPr>'
    c1 = ('<w:p><w:pPr><w:pStyle w:val="Pie"/></w:pPr>' + _campo('STYLEREF "Título de apartado"', "", " ") +
          "</w:p>")
    regla = (f'<w:p><w:pPr><w:pStyle w:val="Pie"/><w:pBdr><w:top w:val="single" w:sz="7" w:space="1" '
             f'w:color="{C["oro"]}"/></w:pBdr><w:spacing w:before="0" w:after="0" w:line="60" w:lineRule="exact"/>'
             f'<w:ind w:left="{2268 - 510}"/></w:pPr></w:p>')
    numero = ('<w:p><w:pPr><w:pStyle w:val="Pie"/><w:jc w:val="right"/></w:pPr>' + _campo('PAGE \\# "00"', r_pie, "01")
              + f'<w:r>{r_tot}<w:t xml:space="preserve"> / </w:t></w:r>' + _campo("NUMPAGES", r_tot, "1") + "</w:p>")
    return XML + f'<w:ftr {NS_DECL}>' + _tabla_2(c1, regla + numero, 2268, abajo=True) + "</w:ftr>"


def pie_portada(rid_escudo: str) -> str:
    """Escudo, centro y base normativa al pie de la portada (sección sin márgenes: la tabla lleva su sangría)."""
    alto = 964   # 17 mm
    ancho = round(alto * 580 / 600)
    emu = lambda tw: tw * 635  # noqa: E731
    dibujo = (f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" {NS_DIBUJO}>'
              f'<wp:extent cx="{emu(ancho)}" cy="{emu(alto)}"/><wp:docPr id="1" name="Escudo"/>'
              '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
              '<pic:nvPicPr><pic:cNvPr id="1" name="escudo.png"/><pic:cNvPicPr/></pic:nvPicPr>'
              f'<pic:blipFill><a:blip r:embed="{rid_escudo}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
              f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{emu(ancho)}" cy="{emu(alto)}"/></a:xfrm>'
              '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
              '</wp:inline></w:drawing></w:r>')
    r_nom = rpr(COND, 9, "v9", b=True, caps=True, esp=10)
    r_txt = rpr(sz=7.3, color="t3")
    centro = (f'<w:p>{ppr(linea=252)}<w:r>{r_nom}<w:t>Escuelas Profesionales Luis Amigó</w:t></w:r></w:p>'
              f'<w:p>{ppr(linea=252)}<w:r>{r_txt}<w:t xml:space="preserve">Carretera de Bétera s/n · 46110 Godella '
              f'(Valencia)</w:t></w:r></w:p><w:p>{ppr(linea=252)}<w:r>{r_txt}<w:t xml:space="preserve">Centro '
              'concertado · Formación Profesional{{correo_pie}}</w:t></w:r></w:p>')
    norma = (f'<w:p>{ppr(linea=252, jc="right")}<w:r>{r_txt}<w:t xml:space="preserve">{{{{decreto_pie}}}}, art. 8. '
             'Elaborado por el equipo docente del ciclo, bajo la coordinación de la jefatura del departamento '
             '(instrucciones de inicio de curso, §6.2).</w:t></w:r></w:p>')
    sin = '<w:tcBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/></w:tcBorders>'
    celdas = [(ancho + 227, f"<w:p>{ppr()}{dibujo}</w:p>"), (4400, centro), (ANCHO - ancho - 227 - 4400, norma)]
    tc = "".join(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{sin}<w:vAlign w:val="bottom"/></w:tcPr>{x}</w:tc>'
                 for w, x in celdas)
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w, _ in celdas)
    return (XML + f'<w:ftr {NS_DECL}><w:tbl><w:tblPr><w:tblW w:w="{ANCHO}" w:type="dxa"/>'
            f'<w:tblInd w:w="{MARGENES["left"]}" w:type="dxa"/><w:tblLayout w:type="fixed"/></w:tblPr>'
            f'<w:tblGrid>{grid}</w:tblGrid><w:tr>{tc}</w:tr></w:tbl>'
            + _p("", None, "", '<w:spacing w:after="0" w:line="120" w:lineRule="exact"/>') + "</w:ftr>")


def documento() -> str:
    """Cuerpo mínimo: la marca {{cuerpo}} y la sección de las páginas interiores (A4 vertical)."""
    m = MARGENES
    sect = (f'<w:sectPr><w:headerReference w:type="default" r:id="rIdEncabezado"/>'
            f'<w:footerReference w:type="default" r:id="rIdPie"/><w:pgSz w:w="{A4[0]}" w:h="{A4[1]}"/>'
            f'<w:pgMar w:top="{m["top"]}" w:right="{m["right"]}" w:bottom="{m["bottom"]}" w:left="{m["left"]}" '
            f'w:header="{m["header"]}" w:footer="{m["footer"]}" w:gutter="0"/><w:cols w:space="708"/></w:sectPr>')
    return XML + f'<w:document {NS_DECL}><w:body>{_p("{{cuerpo}}", "Texto")}{sect}</w:body></w:document>'


def crear() -> None:
    partes: dict[str, bytes] = {}
    tipos = {"word/document.xml": "document.main", "word/styles.xml": "styles", "word/settings.xml": "settings",
             "word/fontTable.xml": "fontTable", "word/numbering.xml": "numbering", "word/header1.xml": "header",
             "word/header2.xml": "header", "word/footer1.xml": "footer", "word/footer2.xml": "footer"}
    ct = (XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
          '<Default Extension="odttf" ContentType="application/vnd.openxmlformats-officedocument.obfuscatedFont"/>'
          + "".join(f'<Override PartName="/{n}" ContentType="application/vnd.openxmlformats-officedocument.'
                    f'wordprocessingml.{t}+xml"/>' for n, t in tipos.items())
          + '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.'
          'core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/'
          'vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>')
    partes["[Content_Types].xml"] = ct.encode()
    partes["_rels/.rels"] = (
        XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{TIPO_REL}officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/'
        'core-properties" Target="docProps/core.xml"/>'
        f'<Relationship Id="rId3" Type="{TIPO_REL}extended-properties" Target="docProps/app.xml"/>'
        '</Relationships>').encode()
    partes["docProps/core.xml"] = (
        XML + '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>Proyecto curricular de ciclo formativo'
        '</dc:title><dc:creator>PCCF</dc:creator><cp:lastModifiedBy>PCCF</cp:lastModifiedBy>'
        '<dc:language>es-ES</dc:language><dcterms:created xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z'
        '</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z</dcterms:modified>'
        '</cp:coreProperties>').encode()
    partes["docProps/app.xml"] = (
        XML + '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
        '<Application>PCCF</Application></Properties>').encode()
    partes["word/_rels/document.xml.rels"] = (
        XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rIdEstilos" Type="{TIPO_REL}styles" Target="styles.xml"/>'
        f'<Relationship Id="rIdAjustes" Type="{TIPO_REL}settings" Target="settings.xml"/>'
        f'<Relationship Id="rIdFuentes" Type="{TIPO_REL}fontTable" Target="fontTable.xml"/>'
        f'<Relationship Id="rIdNumeracion" Type="{TIPO_REL}numbering" Target="numbering.xml"/>'
        f'<Relationship Id="rIdEncabezado" Type="{TIPO_REL}header" Target="header1.xml"/>'
        f'<Relationship Id="rIdPie" Type="{TIPO_REL}footer" Target="footer1.xml"/>'
        f'<Relationship Id="rIdEncabezadoPortada" Type="{TIPO_REL}header" Target="header2.xml"/>'
        f'<Relationship Id="rIdPiePortada" Type="{TIPO_REL}footer" Target="footer2.xml"/>'
        '</Relationships>').encode()
    partes["word/_rels/footer2.xml.rels"] = (
        XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rIdEscudo" Type="{TIPO_REL}image" Target="media/escudo.png"/></Relationships>').encode()
    partes["word/media/escudo.png"] = (RECURSOS / "imagenes" / "escudo.png").read_bytes()
    partes["word/document.xml"] = documento().encode()
    partes["word/styles.xml"] = estilos().encode()
    partes["word/numbering.xml"] = numeracion().encode()
    partes["word/settings.xml"] = ajustes().encode()
    partes["word/header1.xml"] = encabezado().encode()
    partes["word/header2.xml"] = (XML + f'<w:hdr {NS_DECL}>{_p("")}</w:hdr>').encode()
    partes["word/footer1.xml"] = pie().encode()
    partes["word/footer2.xml"] = pie_portada("rIdEscudo").encode()

    ids: dict[str, list[tuple[str, str, str]]] = {}
    rels = []
    for n, (archivo, familia, ranura) in enumerate(FUENTES, 1):
        clave = clave_fuente(archivo)
        partes[f"word/fonts/font{n}.odttf"] = ofuscar((RECURSOS / "fuentes" / archivo).read_bytes(), clave)
        rels.append(f'<Relationship Id="rIdF{n}" Type="{TIPO_REL}font" Target="fonts/font{n}.odttf"/>')
        ids.setdefault(familia, []).append((ranura, f"rIdF{n}", clave))
    partes["word/fontTable.xml"] = tabla_fuentes(ids).encode()
    partes["word/_rels/fontTable.xml.rels"] = (
        XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(rels) + "</Relationships>").encode()

    shutil.rmtree(DESTINO / "es", ignore_errors=True)
    ooxml.Paquete(partes).a_carpeta(DESTINO / "es")
    meta = {"version": dt.date.today().isoformat(), "origen": "scripts/plantilla.py crear (diseño propio, ADR-015)",
            "idiomas": ["es"], "vinetas": "1", "ancho": ANCHO, "col_margen": COL_MARGEN, "sangria": SANGRIA,
            "margenes": MARGENES, "colores": C,
            "fuentes": {"texto": TEXTO, "semi": SEMI, "cond": COND, "cond_semi": COND_SEMI, "cond_extra": COND_EXTRA}}
    with open(DESTINO / "plantilla.yaml", "w", encoding="utf-8") as f:
        f.write("# Generado por scripts/plantilla.py crear: no se edita a mano.\n")
        yaml.safe_dump(meta, f, allow_unicode=True, sort_keys=False)
    errores = comprobar()
    print("Plantilla creada" if not errores else "\n".join(errores))


def comprobar() -> list[str]:
    """Marcas conocidas y enteras, estilos del diseño y fuentes incrustadas que se pueden recuperar."""
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
        if "Programación didáctica" in plano or "PROGRAMACIÓN DIDÁCTICA" in plano:
            errores.append(f"{n}: queda texto de la programación didáctica")
    if MARCAS - vistas:
        errores.append(f"Faltan marcas: {sorted(MARCAS - vistas)}")
    sids = {s.get(W + "styleId") for s in pq.xml("word/styles.xml").iter(W + "style")}
    for s in ("Texto", "Vineta", "ApNumero", "ApTitulo", "ApBase", "Subapartado", "TablaTexto", "TablaCabecera",
              "IndiceEntrada", "Encabezado", "Pie", "Hipervnculo", "MarcaPendiente"):
        if s not in sids:
            errores.append(f"Falta el estilo {s}")
    tf = pq.xml("word/fontTable.xml")
    rels = {r.get("Id"): r.get("Target") for r in pq.xml("word/_rels/fontTable.xml.rels")}
    incrustadas = 0
    for e in tf.iter():
        if etree_local(e).startswith("embed"):
            rid, clave = e.get(ooxml.R + "id"), e.get(W + "fontKey")
            datos = ofuscar(pq.partes["word/" + rels[rid]], clave)
            if datos[:4] != b"\x00\x01\x00\x00":
                errores.append(f"Fuente {rels[rid]}: no se recupera con su clave")
            incrustadas += 1
    if incrustadas != len(FUENTES):
        errores.append(f"Fuentes incrustadas: {incrustadas} de {len(FUENTES)}")
    if pq.xml("word/settings.xml").find(W + "embedTrueTypeFonts") is None:
        errores.append("settings.xml sin embedTrueTypeFonts")
    return errores


def etree_local(e) -> str:
    return e.tag.rsplit("}", 1)[-1] if isinstance(e.tag, str) else ""


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "crear":
        crear()
    elif len(sys.argv) == 2 and sys.argv[1] == "comprobar":
        errs = comprobar()
        print("\n".join(errs) or "Plantilla correcta")
        sys.exit(1 if errs else 0)
    else:
        print(__doc__)
        sys.exit(2)
