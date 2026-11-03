"""El Word del PCCF: la plantilla del centro (`recursos/plantilla/`, de `scripts/plantilla.py`) con la portada rellena y
el cuerpo escrito aquí, apartado por apartado (ADR-013).

- Portada: marcas `{{nombre}}` de un solo run.
- Índice: entradas con hipervínculo a una marca en cada título y su número de página en un campo PAGEREF; Word los
  actualiza al abrir (`updateFields`).
- Cuerpo: los apartados del grado con su título literal. Del MVP salen calculados el 1, el 2 y el 4; los demás llevan
  sus bloques de texto o, si no hay, «Pendiente».
- Bloques (Markdown): párrafos, «### Subtítulo», viñetas «- », **negrita** y [enlaces](url). Las citas «> …» son notas
  para quien edita los datos: no van al documento.
- Si queda algo pendiente o en borrador, la marca de agua «BORRADOR» (salvo que se pida otra cosa).
"""
from __future__ import annotations

import copy
import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from lxml import etree

from pccf import apartados, derivados, ooxml
from pccf.bloques import Bloque
from pccf.catalogo import Catalogo, Norma
from pccf.datos import CarpetaDatos
from pccf.ooxml import NS, W

PLANTILLA = Path(__file__).resolve().parent / "recursos" / "plantilla"
RE_MARCA = re.compile(r"\{\{(\w+)\}\}")
RE_EN_LINEA = re.compile(r"\*\*(.+?)\*\*|\[([^\]]+)\]\((https?://[^)\s]+)\)")
PENDIENTE = "Pendiente"


@dataclass(frozen=True)
class Enlace:
    texto: str
    url: str


@dataclass(frozen=True)
class Negrita:
    texto: str


@dataclass(frozen=True)
class Cursiva:
    texto: str


@dataclass
class Opciones:
    borrador: bool | None = None    # None: según haya pendientes o bloques en borrador
    correo_pie: str = ""            # correo del pie (Ajustes); vacío por defecto (repositorio público)
    fecha: dt.date | None = None


@dataclass
class Resultado:
    docx: bytes
    avisos: list[str] = field(default_factory=list)   # lo pendiente y lo que está en borrador, para la interfaz
    borrador: bool = False


def metadatos_plantilla() -> dict:
    with open(PLANTILLA / "plantilla.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cargar_plantilla() -> ooxml.Paquete:
    return ooxml.Paquete.desde_carpeta(PLANTILLA / "es")


# ---------------------------------------------------------------------------------------------------------------------
# Piezas del cuerpo
# ---------------------------------------------------------------------------------------------------------------------
class Escritor:
    """Construye párrafos y tablas con los estilos de la plantilla."""

    def __init__(self, pq: ooxml.Paquete, vinetas: str):
        self.pq = pq
        self.vinetas = vinetas

    def _runs(self, p, segmentos, rpr_base=None) -> None:
        if isinstance(segmentos, (str, Enlace, Negrita, Cursiva)):
            segmentos = [segmentos]
        for s in segmentos:
            if isinstance(s, Enlace):
                rid = self.pq.relacion("word/document.xml", ooxml.TIPO_HIPERVINCULO, s.url, externa=True)
                h = etree.SubElement(p, W + "hyperlink", {"{%s}id" % NS["r"]: rid})
                h.append(ooxml.run(s.texto, ooxml.rpr_enlace(rpr_base)))
                continue
            rpr = etree.Element(W + "rPr") if rpr_base is None else copy.deepcopy(rpr_base)
            if isinstance(s, Negrita):
                ooxml.hijo(rpr, "b", ooxml.ORDEN_RPR)
            elif isinstance(s, Cursiva):
                ooxml.hijo(rpr, "i", ooxml.ORDEN_RPR)
            p.append(ooxml.run(s if isinstance(s, str) else s.texto, rpr if len(rpr) else None))

    def parrafo(self, segmentos, estilo: str | None = None, vineta: bool = False, centrado: bool | None = None,
                rpr_base=None):
        p = etree.Element(W + "p")
        if estilo or vineta:
            ooxml.hijo(ooxml.ppr(p), "pStyle", ooxml.ORDEN_PPR, val=estilo or "Prrafodelista")
        if vineta:
            num = ooxml.hijo(ooxml.ppr(p), "numPr", ooxml.ORDEN_PPR)
            ooxml.hijo(num, "ilvl", None, val="0")
            ooxml.hijo(num, "numId", None, val=self.vinetas)
        if centrado is not None:
            ooxml.hijo(ooxml.ppr(p), "jc", ooxml.ORDEN_PPR, val="center" if centrado else "left")
        self._runs(p, segmentos, rpr_base)
        return p

    def titulo(self, texto: str, nivel: int):
        return self.parrafo(texto, "Ttulo2" if nivel == 1 else "Ttulo3")

    def pendiente(self, motivo: str = ""):
        return self.parrafo(Cursiva(f"{PENDIENTE}{': ' + motivo if motivo else ''}."))

    def tabla(self, filas: list[list], cabecera: list[str] | None = None, anchos: list[int] | None = None,
              tamano: int | None = None, centrar_desde: int | None = None):
        """Tabla a todo el ancho con el estilo «Tabla con cuadrícula». `anchos`, en cincuentavos de punto porcentual
        (5000 = 100 %); `tamano`, en medios puntos; `centrar_desde`: columnas centradas a partir de esa."""
        t = etree.Element(W + "tbl")
        tblpr = etree.SubElement(t, W + "tblPr")
        etree.SubElement(tblpr, W + "tblStyle", {W + "val": "Tablaconcuadrcula"})
        etree.SubElement(tblpr, W + "tblW", {W + "w": "5000", W + "type": "pct"})
        etree.SubElement(tblpr, W + "tblLayout", {W + "type": "fixed" if anchos else "autofit"})
        n = len(cabecera or filas[0])
        grid = etree.SubElement(t, W + "tblGrid")
        for i in range(n):
            etree.SubElement(grid, W + "gridCol", {W + "w": str(int(9638 * (anchos[i] if anchos else 5000 // n) / 5000))})
        rpr = None
        if tamano:
            rpr = etree.Element(W + "rPr")
            ooxml.hijo(rpr, "sz", ooxml.ORDEN_RPR, val=str(tamano))
            ooxml.hijo(rpr, "szCs", ooxml.ORDEN_RPR, val=str(tamano))
        todas = ([(cabecera, True)] if cabecera else []) + [(f, False) for f in filas]
        for celdas, es_cabecera in todas:
            tr = etree.SubElement(t, W + "tr")
            trpr = etree.SubElement(tr, W + "trPr")
            etree.SubElement(trpr, W + "cantSplit")
            if es_cabecera:
                etree.SubElement(trpr, W + "tblHeader")
            for i, valor in enumerate(celdas):
                tc = etree.SubElement(tr, W + "tc")
                tcpr = ooxml.tcpr(tc)
                ancho = anchos[i] if anchos else 5000 // n
                ooxml.hijo(tcpr, "tcW", ooxml.ORDEN_TCPR, w=str(ancho), type="pct")
                if es_cabecera:
                    ooxml.hijo(tcpr, "shd", ooxml.ORDEN_TCPR, val="clear", color="auto", fill="D9D9D9")
                ooxml.hijo(tcpr, "vAlign", ooxml.ORDEN_TCPR, val="center")
                seg = Negrita(valor) if es_cabecera and isinstance(valor, str) else valor
                centrado = centrar_desde is not None and i >= centrar_desde
                tc.append(self.parrafo(seg, centrado=centrado, rpr_base=rpr))
        return t

    def markdown(self, texto: str, apartado: int, subtitulos: list[int]) -> list:
        """Elementos de un bloque. `subtitulos` lleva la cuenta de los «### » del apartado (n.1, n.2…)."""
        out, parrafo = [], []

        def cerrar():
            if parrafo:
                out.append(self.parrafo(en_linea(" ".join(parrafo))))
                parrafo.clear()

        for linea in texto.splitlines():
            s = linea.strip()
            if not s or s.startswith(">"):
                cerrar()
                continue
            if s.startswith("#"):
                cerrar()
                subtitulos.append(1)
                out.append(self.titulo(f"{apartado}.{len(subtitulos)}. {s.lstrip('#').strip()}", 2))
            elif s.startswith(("- ", "* ")):
                cerrar()
                out.append(self.parrafo(en_linea(s[2:].strip()), vineta=True))
            else:
                parrafo.append(s)
        cerrar()
        return out


def en_linea(texto: str) -> list:
    """**negrita** y [texto](url) de una línea de Markdown."""
    out, pos = [], 0
    for m in RE_EN_LINEA.finditer(texto):
        if m.start() > pos:
            out.append(texto[pos:m.start()])
        out.append(Negrita(m.group(1)) if m.group(1) else Enlace(m.group(2), m.group(3)))
        pos = m.end()
    if pos < len(texto):
        out.append(texto[pos:])
    return out


def _enlace_norma(n: Norma) -> Enlace:
    return Enlace(n.titulo.rstrip("."), n.enlace)


# ---------------------------------------------------------------------------------------------------------------------
# Apartados
# ---------------------------------------------------------------------------------------------------------------------
def apartado_1(e: Escritor, ident: derivados.Identificacion, avisos: list[str]) -> list:
    dep = ident.departamento
    if dep is None:
        avisos.append("Apartado 1: falta el departamento del ciclo (centro/departamentos.yaml)")
    if ident.tutorias is None:
        avisos.append("Apartado 1: faltan las tutorías (equipo.yaml del curso)")
    pend = Cursiva(PENDIENTE)
    filas = [
        ["Ciclo formativo", f"{ident.sigla} – {ident.nombre}"],
        ["Título", ident.titulo],
        ["Grado", ident.grado_largo],
        ["Familia profesional", ident.familia],
        ["Real decreto del título", _enlace_norma(ident.rd) if ident.rd else pend],
        ["Duración", f"{ident.horas_total} horas"],
        ["Departamento", dep["nombre"] if dep else pend],
        ["Jefatura de departamento", dep["jefatura"] if dep else pend],
        ["Curso académico", ident.curso],
        ["Tutorías", "; ".join(f"{g}: {n}" for g, n in ident.tutorias) if ident.tutorias else pend],
    ]
    out = [e.tabla(filas, anchos=[1500, 3500])]
    out.append(e.titulo("1.1. Equipo docente", 2))
    sin = [m for m in ident.modulos if m.docentes is None]
    if sin:
        avisos.append(f"Apartado 1: sin profesorado en {len(sin)} módulos ({', '.join(m.clave for m in sin)})")
    filas = [[f"{m.curso}.º", m.codigo, m.nombre + (" (optativo)" if m.clave.startswith("OPT-") else ""),
              str(m.horas), " / ".join(m.docentes) if m.docentes else pend] for m in ident.modulos]
    out.append(e.tabla(filas, cabecera=["Curso", "Código", "Módulo profesional", "Horas", "Profesorado"],
                       anchos=[500, 750, 2050, 550, 1150], tamano=18))
    return out


def apartado_2(e: Escritor, marco: dict[str, list[Norma]]) -> list:
    out = [e.titulo("2.1. Normativa estatal", 2)]
    out += [e.parrafo(_enlace_norma(n), vineta=True) for n in marco["estatal"]]
    out.append(e.titulo("2.2. Normativa autonómica (Comunitat Valenciana)", 2))
    out += [e.parrafo(_enlace_norma(n), vineta=True) for n in marco["autonomico"]]
    return out


def apartado_4(e: Escritor, k: derivados.Contribucion, cat: Catalogo) -> list:
    letras = [x[0] for x in k.competencias]
    rd = cat.normas.get(k.fuente)
    out = []
    if rd:
        out.append(e.parrafo(["Contribución de cada módulo a las competencias profesionales, personales y sociales "
                              "del título, según su real decreto (", _enlace_norma(rd), ")."]))
    filas = [[f"{f.curso}.º", f"{f.codigo} {f.nombre}"] + ["X" if x in ls else "" for x in letras] for f, ls in k.filas]
    resto = 5000 - 450 - 1550
    ancho = resto // len(letras)
    out.append(e.tabla(filas, cabecera=["Curso", "Módulo profesional"] + letras,
                       anchos=[450, 1550 + resto - ancho * len(letras)] + [ancho] * len(letras), tamano=14,
                       centrar_desde=2))
    if any(not ls for _, ls in k.filas):
        out.append(e.parrafo(Cursiva("Los módulos sin marcas no tienen competencias asignadas en el real decreto "
                                     "del título.")))
    out.append(e.titulo("4.1. Competencias profesionales, personales y sociales del título", 2))
    out += [e.parrafo([Negrita(f"{x})"), f" {t}"]) for x, t in k.competencias]
    return out


def bloques_de(e: Escritor, lista: list[Bloque], n: int, avisos: list[str], subtitulos: list[int]) -> list:
    out = []
    for b in sorted(lista, key=lambda b: (b.orden if b.orden is not None else 999, b.ruta.name)):
        if not b.confirmado:
            avisos.append(f"Apartado {n}: «{b.ruta.name}» está en borrador")
        out += e.markdown(b.cuerpo, n, subtitulos)
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Índice y retoques (de Programaciones)
# ---------------------------------------------------------------------------------------------------------------------
def _fld(tipo: str):
    """Run con un w:fldChar («begin», «separate» o «end»)."""
    r = etree.Element(W + "r")
    etree.SubElement(r, W + "fldChar", {W + "fldCharType": tipo})
    return r


def _instr(texto: str):
    r = etree.Element(W + "r")
    t = etree.SubElement(r, W + "instrText", {ooxml.XML_SPACE: "preserve"})
    t.text = texto
    return r


def indice(body, p_marca) -> int:
    """Sustituye el párrafo `{{indice}}` por el índice de los títulos (nivel 2 y 3 de Word), cada entrada enlazada a
    una marca nueva en su título. Devuelve cuántas entradas tiene."""
    titulos = [p for p in body.iter(W + "p") if ooxml.estilo(p) in ("Ttulo2", "Ttulo3")]
    entradas = []
    for n, p in enumerate(titulos, 1):
        nombre = f"_TocPccf{n:03d}"
        ini = etree.Element(W + "bookmarkStart", {W + "id": str(900 + n), W + "name": nombre})
        ppr = p.find(W + "pPr")
        if ppr is not None:
            ppr.addnext(ini)
        else:
            p.insert(0, ini)
        p.append(etree.Element(W + "bookmarkEnd", {W + "id": str(900 + n)}))
        e = etree.Element(W + "p")
        ooxml.hijo(ooxml.ppr(e), "pStyle", ooxml.ORDEN_PPR, val="TDC2" if ooxml.estilo(p) == "Ttulo2" else "TDC3")
        if n == 1:
            e.extend([_fld("begin"), _instr(' TOC \\o "2-3" \\h \\z \\u '), _fld("separate")])
        h = etree.SubElement(e, W + "hyperlink", {W + "anchor": nombre, W + "history": "1"})
        h.append(ooxml.run(ooxml.normal(ooxml.texto(p))))
        r = etree.SubElement(h, W + "r")
        etree.SubElement(r, W + "tab")
        h.extend([_fld("begin"), _instr(f" PAGEREF {nombre} \\h "), _fld("separate"), ooxml.run(""), _fld("end")])
        entradas.append(e)
    fin = etree.Element(W + "p")
    ooxml.hijo(ooxml.ppr(fin), "pStyle", ooxml.ORDEN_PPR, val="TDC2")
    fin.append(_fld("end"))
    padre = p_marca.getparent()
    i = padre.index(p_marca)
    padre.remove(p_marca)
    for j, x in enumerate(entradas + [fin]):
        padre.insert(i + j, x)
    return len(entradas)


def mantener_titulos(body) -> None:
    """keepNext en los títulos: ninguno se queda solo al pie de una página."""
    for p in body.iter(W + "p"):
        if ooxml.es_titulo(p):
            ooxml.hijo(ooxml.ppr(p), "keepNext", ooxml.ORDEN_PPR)


def actualizar_campos(pq: ooxml.Paquete) -> None:
    """Que Word rehaga el índice y los números de página al abrir (w:updateFields, tras w:zoom si lo hay)."""
    ajustes = pq.xml("word/settings.xml")
    uf = ooxml.hijo(ajustes, "updateFields", None, val="true")
    ajustes.remove(uf)
    zoom = ajustes.find(W + "zoom")
    if zoom is not None:
        zoom.addnext(uf)
    else:
        ajustes.insert(0, uf)


MARCA_AGUA = (
    '<w:p xmlns:w="{w}" xmlns:v="{v}" xmlns:o="{o}"><w:pPr><w:pStyle w:val="Encabezado"/></w:pPr><w:r><w:pict>'
    '<v:shapetype id="_x0000_t136" coordsize="21600,21600" o:spt="136" adj="10800" path="m@7,l@8,m@5,21600l@6,21600e">'
    '<v:formulas><v:f eqn="sum #0 0 10800"/><v:f eqn="prod #0 2 1"/><v:f eqn="sum 21600 0 @1"/>'
    '<v:f eqn="sum 0 0 @2"/><v:f eqn="sum 21600 0 @3"/><v:f eqn="if @0 @3 0"/><v:f eqn="if @0 21600 @1"/>'
    '<v:f eqn="if @0 0 @2"/><v:f eqn="if @0 @4 21600"/><v:f eqn="mid @5 @6"/><v:f eqn="mid @8 @5"/>'
    '<v:f eqn="mid @7 @8"/><v:f eqn="mid @6 @7"/><v:f eqn="sum @6 0 @5"/></v:formulas>'
    '<v:path textpathok="t" o:connecttype="custom" o:connectlocs="@9,0;@10,10800;@11,21600;@12,10800" '
    'o:connectangles="270,180,90,0"/><v:textpath on="t" fitshape="t"/>'
    '<o:lock v:ext="edit" text="t" shapetype="t"/></v:shapetype>'
    '<v:shape id="MarcaBorrador" o:spid="_x0000_s2049" type="#_x0000_t136" style="position:absolute;'
    'margin-left:0;margin-top:0;width:468pt;height:117pt;rotation:315;z-index:-251657216;'
    'mso-position-horizontal:center;mso-position-horizontal-relative:margin;mso-position-vertical:center;'
    'mso-position-vertical-relative:margin" o:allowincell="f" fillcolor="silver" stroked="f">'
    '<v:fill opacity=".5"/><v:textpath style="font-family:&quot;Calibri&quot;;font-size:1pt" string="BORRADOR"/>'
    '</v:shape></w:pict></w:r></w:p>')


def marca_borrador(pq: ooxml.Paquete) -> None:
    """«BORRADOR» en diagonal en el encabezado de las páginas con encabezado (copia de Programaciones)."""
    xml = MARCA_AGUA.format(w=NS["w"], v=NS["v"], o=NS["o"])
    for n in sorted(pq.partes):
        if re.fullmatch(r"word/header\d+\.xml", n):
            raiz = pq.xml(n)
            if ooxml.texto(raiz).strip():   # solo el encabezado con contenido (el de la portada está vacío)
                raiz.append(etree.fromstring(xml))


def rellenar_marcas(raiz, valores: dict[str, str]) -> None:
    for t in raiz.iter(W + "t"):
        if t.text and "{{" in t.text:
            t.text = RE_MARCA.sub(lambda m: valores.get(m.group(1), m.group(0)), t.text)
            if t.text != t.text.strip():
                t.set(ooxml.XML_SPACE, "preserve")


def propiedades(pq: ooxml.Paquete, ident: derivados.Identificacion, cuando: dt.date) -> None:
    core = pq.xml("docProps/core.xml")
    ns = {"dc": "http://purl.org/dc/elements/1.1/", "dcterms": "http://purl.org/dc/terms/"}
    t = core.find("dc:title", ns)
    if t is not None:
        t.text = f"Proyecto curricular de ciclo formativo · {ident.sigla} · {ident.curso}"
    for nombre in ("created", "modified"):
        e = core.find(f"dcterms:{nombre}", ns)
        if e is not None:
            e.text = f"{cuando.isoformat()}T00:00:00Z"


def nombre_archivo(sigla: str, curso: str) -> str:
    return f"PCCF {sigla} {curso}.docx"


# ---------------------------------------------------------------------------------------------------------------------
# Generar
# ---------------------------------------------------------------------------------------------------------------------
def generar(cat: Catalogo, datos: CarpetaDatos, sigla: str, curso: str, opciones: Opciones | None = None) -> Resultado:
    opciones = opciones or Opciones()
    avisos: list[str] = []
    ident = derivados.identificacion(cat, datos, sigla, curso)
    pq = cargar_plantilla()
    e = Escritor(pq, str(metadatos_plantilla()["vinetas"]))
    body = pq.xml("word/document.xml").find(W + "body")
    marcas = {ooxml.texto(p).strip(): p for p in body.findall(W + "p") if ooxml.texto(p).strip() in
              ("{{indice}}", "{{cuerpo}}")}

    todos = datos.bloques(sigla, curso)
    cuerpo = []
    for a in apartados.apartados(ident.grado):
        cuerpo.append(e.titulo(f"{a.n}. {a.titulo}", 1))
        subtitulos: list[int] = []
        if a.n == 1:
            cuerpo += apartado_1(e, ident, avisos)
            subtitulos.append(1)
        elif a.n == 2:
            cuerpo += apartado_2(e, derivados.marco_normativo(cat, sigla, curso))
            subtitulos += [1, 1]
        elif a.n == 4:
            cuerpo += apartado_4(e, derivados.contribucion(cat, sigla), cat)
            subtitulos.append(1)
        propios = [b for b in todos if b.apartado == a.n]
        cuerpo += bloques_de(e, propios, a.n, avisos, subtitulos)
        if a.n not in (1, 2, 4) and not propios:
            cuerpo.append(e.pendiente())
            avisos.append(f"Apartado {a.n}: pendiente")

    p = marcas["{{cuerpo}}"]
    padre, i = p.getparent(), p.getparent().index(p)
    padre.remove(p)
    for j, x in enumerate(cuerpo):
        padre.insert(i + j, x)

    dep = ident.departamento
    valores = {"familia": ident.familia, "grado": ident.grado_largo, "ciclo": f"{ident.sigla} – {ident.nombre}",
               "departamento": dep["nombre"] if dep else PENDIENTE, "horas": str(ident.horas_total),
               "jefatura": dep["jefatura"] if dep else PENDIENTE, "curso_escolar": ident.curso,
               "correo_pie": opciones.correo_pie}
    for n in sorted(pq.partes):
        if re.fullmatch(r"word/(document|header\d+|footer\d+)\.xml", n):
            rellenar_marcas(pq.xml(n), valores)
    indice(body, marcas["{{indice}}"])
    restos = RE_MARCA.findall(ooxml.texto(body))
    if restos:
        raise ValueError(f"Marcas sin rellenar: {restos[:5]}")
    mantener_titulos(body)
    actualizar_campos(pq)
    borrador = bool(avisos) if opciones.borrador is None else opciones.borrador
    if borrador:
        marca_borrador(pq)
    pq.quitar_relaciones_huerfanas("word/document.xml")
    propiedades(pq, ident, opciones.fecha or dt.date.today())
    return Resultado(docx=pq.a_bytes(), avisos=avisos, borrador=borrador)
