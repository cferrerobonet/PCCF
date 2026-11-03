"""Utilidades de bajo nivel para el paquete de Word (.docx): partes, relaciones, tipos, párrafos y estilos de carácter.

Copia de `ooxml.py` de Programaciones (sin cambios de comportamiento). Sin dependencias de Qt: solo lxml. El paquete se guarda en memoria como {nombre de parte: bytes};
cada parte XML se analiza una vez y se vuelve a serializar al guardar.
"""
from __future__ import annotations

import copy
import io
import re
import unicodedata
import zipfile
from pathlib import Path

from lxml import etree

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "v": "urn:schemas-microsoft-com:vml",
    "o": "urn:schemas-microsoft-com:office:office",
}
W = "{%s}" % NS["w"]
R = "{%s}" % NS["r"]
PR = "{%s}" % NS["pr"]
CT = "{%s}" % NS["ct"]
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

TIPO_HIPERVINCULO = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
TIPO_CUSTOMXML = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXml"
TIPO_CUSTOMXML_PROPS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXmlProps"
CT_CUSTOMXML_PROPS = "application/vnd.openxmlformats-officedocument.customXmlProperties+xml"


def qn(nombre: str) -> str:
    """«w:p» → «{espacio}p»."""
    prefijo, local = nombre.split(":")
    return "{%s}%s" % (NS[prefijo], local)


def normal(s: str | None) -> str:
    """NFC, espacios no separables a espacios y blancos seguidos a uno solo."""
    s = unicodedata.normalize("NFC", s or "").replace(" ", " ").replace("­", "")
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------------------------------------------------
# Paquete
# ---------------------------------------------------------------------------------------------------------------------
class Paquete:
    """Un .docx en memoria. Las partes XML se analizan bajo demanda y se serializan al guardar."""

    def __init__(self, partes: dict[str, bytes]):
        self.partes = dict(partes)
        self._xml: dict[str, etree._Element] = {}

    # -- carga y guardado --------------------------------------------------------------------------------------------
    @classmethod
    def desde_docx(cls, origen: bytes | str | Path) -> Paquete:
        datos = Path(origen).read_bytes() if isinstance(origen, (str, Path)) else origen
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            return cls({n: z.read(n) for n in z.namelist() if not n.endswith("/")})

    @classmethod
    def desde_carpeta(cls, carpeta: Path) -> Paquete:
        partes = {}
        for p in sorted(carpeta.rglob("*")):
            if p.is_file() and p.name != ".DS_Store" and not p.name.startswith("._"):   # «.rels» sí
                partes[p.relative_to(carpeta).as_posix()] = p.read_bytes()
        return cls(partes)

    def _volcar(self) -> None:
        for nombre, raiz in self._xml.items():
            self.partes[nombre] = etree.tostring(raiz, xml_declaration=True, encoding="UTF-8", standalone=True)

    def a_bytes(self) -> bytes:
        """Zip del .docx: [Content_Types].xml primero y fecha fija (el mismo contenido da los mismos bytes)."""
        self._volcar()
        salida = io.BytesIO()
        orden = ["[Content_Types].xml", "_rels/.rels"] + sorted(n for n in self.partes if n not in (
            "[Content_Types].xml", "_rels/.rels"))
        with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
            for n in orden:
                if n in self.partes:
                    info = zipfile.ZipInfo(n, date_time=(2026, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    z.writestr(info, self.partes[n])
        return salida.getvalue()

    def a_carpeta(self, carpeta: Path) -> None:
        self._volcar()
        for n, datos in self.partes.items():
            destino = carpeta / n
            destino.parent.mkdir(parents=True, exist_ok=True)
            if not destino.is_file() or destino.read_bytes() != datos:   # sin reescrituras inútiles (iCloud)
                destino.write_bytes(datos)

    # -- partes XML --------------------------------------------------------------------------------------------------
    def xml(self, nombre: str) -> etree._Element:
        if nombre not in self._xml:
            parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False, no_network=True)
            self._xml[nombre] = etree.fromstring(self.partes[nombre], parser)
        return self._xml[nombre]

    def poner_xml(self, nombre: str, raiz: etree._Element) -> None:
        self._xml[nombre] = raiz

    def quitar(self, nombre: str) -> None:
        self.partes.pop(nombre, None)
        self._xml.pop(nombre, None)

    def existe(self, nombre: str) -> bool:
        return nombre in self.partes or nombre in self._xml

    # -- relaciones --------------------------------------------------------------------------------------------------
    @staticmethod
    def nombre_rels(parte: str) -> str:
        carpeta, _, archivo = parte.rpartition("/")
        return f"{carpeta}/_rels/{archivo}.rels" if carpeta else f"_rels/{archivo}.rels"

    def rels(self, parte: str) -> etree._Element:
        nombre = self.nombre_rels(parte)
        if not self.existe(nombre):
            self.poner_xml(nombre, etree.Element(PR + "Relationships", nsmap={None: NS["pr"]}))
        return self.xml(nombre)

    def relacion(self, parte: str, tipo: str, destino: str, externa: bool = False) -> str:
        """Id de una relación de `parte` con `destino`; la crea si no existe."""
        raiz = self.rels(parte)
        for r in raiz:
            if r.get("Type") == tipo and r.get("Target") == destino:
                return r.get("Id")
        usados = {r.get("Id") for r in raiz}
        n = 1
        while f"rId{n}" in usados:
            n += 1
        e = etree.SubElement(raiz, PR + "Relationship", Id=f"rId{n}", Type=tipo, Target=destino)
        if externa:
            e.set("TargetMode", "External")
        return f"rId{n}"

    def quitar_relaciones_huerfanas(self, parte: str, tipos: tuple[str, ...] = (TIPO_HIPERVINCULO,)) -> int:
        """Quita las relaciones de esos tipos que ya no usa ningún r:id de la parte."""
        usados = {v for e in self.xml(parte).iter() for k, v in e.attrib.items() if k.startswith(R)}
        quitadas = 0
        for r in list(self.rels(parte)):
            if r.get("Type") in tipos and r.get("Id") not in usados:
                r.getparent().remove(r)
                quitadas += 1
        return quitadas

    # -- tipos de contenido ------------------------------------------------------------------------------------------
    def tipo_override(self, nombre: str, tipo: str | None) -> None:
        """Pone (o quita, con tipo None) el Override de una parte en [Content_Types].xml."""
        raiz = self.xml("[Content_Types].xml")
        nombre_parte = "/" + nombre.lstrip("/")
        for o in raiz.findall(CT + "Override"):
            if o.get("PartName") == nombre_parte:
                raiz.remove(o)
        if tipo:
            etree.SubElement(raiz, CT + "Override", PartName=nombre_parte, ContentType=tipo)


# ---------------------------------------------------------------------------------------------------------------------
# Texto de párrafos y tablas
# ---------------------------------------------------------------------------------------------------------------------
def texto(e: etree._Element) -> str:
    """Texto de un elemento (párrafo, celda…): w:t, con las tabulaciones como espacio. Sin normalizar."""
    partes = []
    for x in e.iter(W + "t", W + "tab", W + "br", W + "delText"):
        if x.tag == W + "t":
            partes.append(x.text or "")
        elif x.tag in (W + "tab", W + "br"):
            partes.append(" ")
    return "".join(partes)


def estilo(p: etree._Element) -> str:
    st = p.find(f"{W}pPr/{W}pStyle")
    return st.get(W + "val") if st is not None else ""


def es_titulo(p: etree._Element) -> bool:
    return p.tag == W + "p" and estilo(p) in ("Ttulo1", "Ttulo2", "Ttulo3", "Heading1", "Heading2", "Heading3")


def numeracion(p: etree._Element) -> tuple[str, int] | None:
    n = p.find(f"{W}pPr/{W}numPr")
    if n is None or n.find(W + "numId") is None:
        return None
    lvl = n.find(W + "ilvl")
    return n.find(W + "numId").get(W + "val"), int(lvl.get(W + "val")) if lvl is not None else 0


# ---------------------------------------------------------------------------------------------------------------------
# Orden de los hijos de pPr, rPr y tcPr (el esquema de OOXML exige una secuencia)
# ---------------------------------------------------------------------------------------------------------------------
ORDEN_RPR = ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline", "shadow",
             "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing", "w", "kern",
             "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs",
             "em", "lang", "eastAsianLayout", "specVanish", "oMath"]
ORDEN_PPR = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
             "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
             "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid",
             "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection",
             "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"]
ORDEN_TCPR = ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar",
              "textDirection", "tcFitText", "vAlign", "hideMark", "headers", "cellIns", "cellDel", "cellMerge",
              "tcPrChange"]


def ordenar(contenedor: etree._Element, orden: list[str]) -> None:
    hijos = list(contenedor)
    clave = {n: i for i, n in enumerate(orden)}
    hijos.sort(key=lambda e: clave.get(etree.QName(e).localname, len(orden)) if etree.QName(e).namespace == NS["w"]
               else len(orden))
    for h in hijos:
        contenedor.remove(h)
    contenedor.extend(hijos)


def hijo(contenedor: etree._Element, nombre: str, orden: list[str] | None = None, **atributos) -> etree._Element:
    """El hijo w:`nombre` de `contenedor`; lo crea (en su sitio según `orden`) si no existe."""
    e = contenedor.find(W + nombre)
    if e is None:
        e = etree.SubElement(contenedor, W + nombre)
        if orden:
            ordenar(contenedor, orden)
    for k, v in atributos.items():
        e.set(W + k, v)
    return e


def ppr(p: etree._Element) -> etree._Element:
    e = p.find(W + "pPr")
    if e is None:
        e = etree.Element(W + "pPr")
        p.insert(0, e)
    return e


def tcpr(tc: etree._Element) -> etree._Element:
    e = tc.find(W + "tcPr")
    if e is None:
        e = etree.Element(W + "tcPr")
        tc.insert(0, e)
    return e


def run(texto_run: str, rpr: etree._Element | None = None) -> etree._Element:
    r = etree.Element(W + "r")
    if rpr is not None and len(rpr):
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, W + "t")
    t.text = texto_run
    if texto_run != texto_run.strip() or "  " in texto_run:
        t.set(XML_SPACE, "preserve")
    return r


def rpr_enlace(rpr: etree._Element | None) -> etree._Element:
    """Formato de un hipervínculo de la plantilla: el del texto, con el estilo «Hipervínculo» y en cursiva."""
    e = copy.deepcopy(rpr) if rpr is not None else etree.Element(W + "rPr")
    e.tag = W + "rPr"
    hijo(e, "rStyle", ORDEN_RPR, val="Hipervnculo")
    hijo(e, "i", ORDEN_RPR)
    hijo(e, "iCs", ORDEN_RPR)
    for quitar in ("color", "u"):   # el color y el subrayado los pone el estilo
        x = e.find(W + quitar)
        if x is not None:
            e.remove(x)
    return e


def rpr_texto(rpr: etree._Element | None) -> etree._Element | None:
    """Formato de texto normal a partir del de un hipervínculo: sin el estilo «Hipervínculo» ni la cursiva."""
    if rpr is None:
        return None
    e = copy.deepcopy(rpr)
    for quitar in ("rStyle", "i", "iCs"):
        x = e.find(W + quitar)
        if x is not None and (quitar != "rStyle" or x.get(W + "val") == "Hipervnculo"):
            e.remove(x)
    return e


def limpiar_ids(e: etree._Element) -> None:
    """Quita de un elemento copiado lo que Word quiere único: los w14:paraId y w14:textId y los marcadores."""
    for x in list(e.iter()):
        for a in ("{%s}paraId" % NS["w14"], "{%s}textId" % NS["w14"]):
            if a in x.attrib:
                del x.attrib[a]
        if x.tag in (W + "bookmarkStart", W + "bookmarkEnd") and x.getparent() is not None:
            x.getparent().remove(x)


# ---------------------------------------------------------------------------------------------------------------------
# Geometría de las anclas de encabezados y pies (EMU: 914 400 por pulgada, 36 000 por milímetro)
# ---------------------------------------------------------------------------------------------------------------------
EMU_TWIP = 635
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"


def _pagina(doc: etree._Element) -> dict:
    """Medidas de la última sección del documento (la de las páginas con encabezado) en EMU."""
    sect = list(doc.iter(W + "sectPr"))[-1]
    sz, mar = sect.find(W + "pgSz"), sect.find(W + "pgMar")
    return {"ancho": int(sz.get(W + "w")) * EMU_TWIP, "alto": int(sz.get(W + "h")) * EMU_TWIP,
            "izq": int(mar.get(W + "left")) * EMU_TWIP, "der": int(mar.get(W + "right")) * EMU_TWIP,
            "arriba": int(mar.get(W + "top")) * EMU_TWIP, "abajo": int(mar.get(W + "bottom")) * EMU_TWIP,
            "encabezado": int(mar.get(W + "header")) * EMU_TWIP, "pie": int(mar.get(W + "footer")) * EMU_TWIP}


def anclas(parte: etree._Element, doc: etree._Element, es_pie: bool = False) -> list[dict]:
    """Rectángulos de las anclas (wp:anchor) de un encabezado o pie, en coordenadas de página (EMU).

    Vale para lo que usa la plantilla: posición horizontal con desplazamiento respecto a página, columna o margen, o
    alineada a la derecha del margen izquierdo; vertical con desplazamiento respecto a página o al párrafo, que en un
    encabezado se toma a la altura del encabezado y en un pie a la del pie (aproximación suficiente aquí)."""
    pg = _pagina(doc)
    out = []
    for a in parte.iter(WP + "anchor"):
        ext = a.find(WP + "extent")
        cx, cy = int(ext.get("cx")), int(ext.get("cy"))
        ph, pv = a.find(WP + "positionH"), a.find(WP + "positionV")
        off = ph.find(WP + "posOffset")
        rel = ph.get("relativeFrom")
        if off is not None:
            x = int(off.text) + {"page": 0, "column": pg["izq"], "margin": pg["izq"], "leftMargin": 0}.get(rel, 0)
        else:
            alin = ph.find(WP + "align").text
            ancho_ref = pg["izq"] if rel == "leftMargin" else pg["ancho"]
            x = {"right": ancho_ref - cx, "left": 0, "center": (ancho_ref - cx) // 2}[alin]
        off_v = pv.find(WP + "posOffset")
        y_ref = 0 if pv.get("relativeFrom") == "page" else (pg["alto"] - pg["pie"] if es_pie else pg["encabezado"])
        y = y_ref + (int(off_v.text) if off_v is not None else 0)
        nombre = a.find(WP + "docPr").get("name") if a.find(WP + "docPr") is not None else ""
        xfrm = a.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}xfrm")
        giro = int(xfrm.get("rot", "0")) // 60000 % 180 if xfrm is not None else 0
        if giro == 90:   # forma girada un cuarto de vuelta: el extent es la caja sin girar, con el mismo centro
            mx, my = x + cx // 2, y + cy // 2
            cx, cy = cy, cx
            x, y = mx - cx // 2, my - cy // 2
        out.append({"nombre": nombre, "x0": x, "y0": y, "x1": x + cx, "y1": y + cy,
                    "texto": normal(texto(a)), "imagen": a.find(".//{%s}blip" % "http://schemas.openxmlformats.org/drawingml/2006/main") is not None})
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Fuente con la que se ve cada texto
# ---------------------------------------------------------------------------------------------------------------------
def _fuente_rfonts(rpr: etree._Element | None, tema: dict[str, str], ranura: str = "ascii") -> str | None:
    """La fuente que fija un `w:rPr` en una ranura («ascii»: U+0000–U+007F; «hAnsi»: el resto del alfabeto latino,
    con las tildes, «→» o «·»), o None si no la fija. La del tema gana a la escrita."""
    rf = rpr.find(W + "rFonts") if rpr is not None else None
    if rf is None:
        return None
    if rf.get(W + ranura + "Theme"):
        nombre = rf.get(W + ranura + "Theme")
        return tema.get(nombre[:5], nombre)
    return rf.get(W + ranura)


def fuentes_de_texto(pq: Paquete, parte: str = "word/document.xml") -> list[tuple[str, str, str]]:
    """(fuente, ranura, texto) de cada run con texto, resolviendo como Word cada ranura (`ascii` para lo ASCII,
    `hAnsi` para el resto y `eastAsia`, que Word usa para símbolos como «→» y que se mira siempre): `rFonts` del run, su estilo de carácter, el estilo del párrafo (o el estilo por defecto) con sus
    `basedOn` y, al final, `docDefaults`; las fuentes del tema («minorHAnsi»…) se traducen con `theme1.xml`. Sin
    nada que la fije, Word usa Times New Roman."""
    estilos = pq.xml("word/styles.xml")
    por_id = {s.get(W + "styleId"): s for s in estilos.iter(W + "style")}
    defecto_p = next((s.get(W + "styleId") for s in estilos.iter(W + "style")
                      if s.get(W + "type") == "paragraph" and s.get(W + "default") == "1"), None)
    tema = {}
    if "word/theme/theme1.xml" in pq.partes:
        a = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
        t = pq.xml("word/theme/theme1.xml")
        for clave in ("major", "minor"):
            latin = t.find(f".//{a}{clave}Font/{a}latin")
            if latin is not None:
                tema[clave] = latin.get("typeface")
    base = estilos.find(f"{W}docDefaults/{W}rPrDefault/{W}rPr")

    def del_estilo(sid: str | None, ranura: str, vistos=()) -> str | None:
        s = por_id.get(sid)
        if s is None or sid in vistos:
            return None
        propia = _fuente_rfonts(s.find(W + "rPr"), tema, ranura)
        if propia:
            return propia
        padre = s.find(W + "basedOn")
        return del_estilo(padre.get(W + "val"), ranura, (*vistos, sid)) if padre is not None else None

    out = []
    for p in pq.xml(parte).iter(W + "p"):
        pstyle = p.find(f"{W}pPr/{W}pStyle")
        sid_p = pstyle.get(W + "val") if pstyle is not None else defecto_p
        for r in p.iter(W + "r"):
            t = "".join(x.text or "" for x in r.findall(W + "t"))
            if not t.strip():
                continue
            rpr = r.find(W + "rPr")
            rstyle = rpr.find(W + "rStyle") if rpr is not None else None
            for ranura, trozo in (("ascii", "".join(c for c in t if ord(c) < 128)),
                                  ("hAnsi", "".join(c for c in t if ord(c) >= 128)), ("eastAsia", t)):
                if not trozo.strip():
                    continue
                fuente = (_fuente_rfonts(rpr, tema, ranura)
                          or (del_estilo(rstyle.get(W + "val"), ranura) if rstyle is not None else None)
                          or del_estilo(sid_p, ranura) or _fuente_rfonts(base, tema, ranura) or "Times New Roman")
                out.append((fuente, ranura, t))
    return out
