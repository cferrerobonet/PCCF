"""El Word del PCCF con diseño propio (ADR-015; DESIGN.md § Documento): la plantilla de `scripts/plantilla.py` (estilos,
encabezado, pie y fuentes incrustadas) y el cuerpo escrito aquí.

- Portada (sección sin márgenes): bloque verde con las siglas, banda de borrador y ficha del ciclo; el escudo, en su pie.
- Control del documento: elaboración, coordinación, aprobación, PGA, evaluación, registro de revisiones y firmas.
- Contenido: entradas enlazadas a una marca en cada título, con su página en un campo PAGEREF (Word lo actualiza al
  abrir: `updateFields`).
- Apartados del grado (ADR-014): apertura con el número en la columna de margen y la base (norma · guía · origen); del
  MVP salen calculados el 1, el 2, el 4, el 7 y el 20; los demás llevan sus bloques de texto o «Pendiente» con lo que
  pide la guía. El 4, con su matriz, en una sección apaisada.
- Anexos A (ficha de empresa, guía anexo III) y B (programa formativo personalizado, guía anexo IV).
- Bloques (Markdown): párrafos, «### Subtítulo», viñetas «- », **negrita** y [enlaces](url). Las citas «> …» son notas
  para quien edita los datos: no van al documento.
- Borrador (si queda algo pendiente o en borrador, salvo que se pida otra cosa): banda en la portada y etiqueta en el
  encabezado. Sin marca de agua.
"""
from __future__ import annotations

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
from pccf.texto import RE_EN_LINEA

PLANTILLA = Path(__file__).resolve().parent / "recursos" / "plantilla"
RE_MARCA = re.compile(r"\{\{(\w+)\}\}")
PENDIENTE = "Pendiente"
GUIA = "Guía DGFP"
R_ID = "{%s}id" % NS["r"]


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


@dataclass(frozen=True)
class Estilo:
    """Texto con un estilo de carácter de la plantilla («Codigo», «MarcaPendiente»…)."""
    texto: str
    estilo: str


@dataclass
class Opciones:
    borrador: bool | None = None    # None: según haya pendientes o bloques en borrador
    correo_pie: str = ""            # correo del pie de la portada (Ajustes); vacío por defecto (repositorio público)
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
# Piezas
# ---------------------------------------------------------------------------------------------------------------------
def _e(nombre: str, padre=None, **atr):
    """w:`nombre` con atributos w:… (los que llevan «r_» van en el espacio r:)."""
    attrs = {(R_ID if k == "r_id" else W + k): str(v) for k, v in atr.items()}
    return etree.SubElement(padre, W + nombre, attrs) if padre is not None else etree.Element(W + nombre, attrs)


def _borde(padre, lados: dict[str, tuple[int, str]], nombre: str = "tcBorders"):
    """Bordes {lado: (grosor en octavos de punto, color)}; los que no están, sin borde."""
    b = _e(nombre, padre)
    for lado in ("top", "left", "bottom", "right"):
        if lado in lados:
            sz, color = lados[lado]
            _e(lado, b, val="single", sz=sz, space=0, color=color)
        else:
            _e(lado, b, val="nil")
    return b


class Escritor:
    """Construye párrafos y tablas con los estilos de la plantilla y lleva la cuenta de marcas y de entradas del
    contenido."""

    def __init__(self, pq: ooxml.Paquete):
        self.pq = pq
        m = metadatos_plantilla()
        self.c = m["colores"]
        self.f = m["fuentes"]
        self.ancho = m["ancho"]
        self.col = m["col_margen"]
        self.sangria = m["sangria"]
        self.margenes = m["margenes"]
        self.entradas: list[tuple[str, str, str, bool, str | None]] = []   # (número, título, marca, pendiente, grupo)
        self._marcas = 0

    # -- runs y párrafos ---------------------------------------------------------------------------------------------
    def rpr(self, fuente: str | None = None, sz: float | None = None, color: str | None = None, b: bool = False,
            i: bool = False, caps: bool = False, esp: int | None = None, estilo: str | None = None):
        r = etree.Element(W + "rPr")
        if estilo:
            _e("rStyle", r, val=estilo)
        if fuente:
            _e("rFonts", r, ascii=fuente, hAnsi=fuente, cs=fuente)
        if b:
            _e("b", r)
            _e("bCs", r)
        if i:
            _e("i", r)
            _e("iCs", r)
        if caps:
            _e("caps", r)
        if color:
            _e("color", r, val=self.c.get(color, color))
        if esp:
            _e("spacing", r, val=esp)
        if sz:
            _e("sz", r, val=round(sz * 2))
            _e("szCs", r, val=round(sz * 2))
        return r

    def _runs(self, p, segmentos, rpr_base=None) -> None:
        if isinstance(segmentos, (str, Enlace, Negrita, Cursiva, Estilo)):
            segmentos = [segmentos]
        for s in segmentos:
            if isinstance(s, Enlace):
                rid = self.pq.relacion("word/document.xml", ooxml.TIPO_HIPERVINCULO, s.url, externa=True)
                h = _e("hyperlink", p, r_id=rid)
                h.append(ooxml.run(s.texto, self.rpr(estilo="Hipervnculo")))
                continue
            if isinstance(s, Negrita):
                r = self.rpr(estilo="Destacado")
            elif isinstance(s, Cursiva):
                r = self.rpr(i=True)
            elif isinstance(s, Estilo):
                r = self.rpr(estilo=s.estilo)
            else:
                r = rpr_base
            texto = s if isinstance(s, str) else s.texto
            p.append(ooxml.run(texto, r))

    def parrafo(self, segmentos=(), estilo: str | None = "Texto", jc: str | None = None, rpr_base=None,
                antes: int | None = None, despues: int | None = None, ind: tuple[int, int] | None = None,
                keep: bool = False):
        p = etree.Element(W + "p")
        pp = _e("pPr", p)
        if estilo:
            _e("pStyle", pp, val=estilo)
        if keep:
            _e("keepNext", pp)
        if antes is not None or despues is not None:
            sp = _e("spacing", pp)
            if antes is not None:
                sp.set(W + "before", str(antes))
            if despues is not None:
                sp.set(W + "after", str(despues))
        if ind is not None:
            _e("ind", pp, left=ind[0], right=ind[1])
        if jc:
            _e("jc", pp, val=jc)
        self._runs(p, segmentos, rpr_base)
        return p

    def separador(self, alto: int = 0):
        """Párrafo mínimo: separa dos tablas (Word las uniría) y da aire (`alto`, en twips)."""
        p = etree.Element(W + "p")
        pp = _e("pPr", p)
        _e("spacing", pp, before=0, after=alto, line=40, lineRule="exact")
        return p

    def salto_pagina(self):
        p = etree.Element(W + "p")
        r = _e("r", p)
        _e("br", r, type="page")
        return p

    def marca(self, p, prefijo: str = "_PccfAp") -> str:
        self._marcas += 1
        nombre = f"{prefijo}{self._marcas:03d}"
        ppr = p.find(W + "pPr")
        ini = etree.Element(W + "bookmarkStart", {W + "id": str(900 + self._marcas), W + "name": nombre})
        (ppr.addnext if ppr is not None else lambda x: p.insert(0, x))(ini)
        p.append(etree.Element(W + "bookmarkEnd", {W + "id": str(900 + self._marcas)}))
        return nombre

    # -- tablas ------------------------------------------------------------------------------------------------------
    def tabla(self, anchos: list[int], filas: list[list], sangria: int = 0, cabecera: bool = False,
              filete_sup: bool = False):
        """Tabla sin rejilla (DESIGN.md: «Tabla»). `filas`: listas de celdas; cada celda es un elemento o lista de
        elementos de párrafo, o un dict {"p": …, "fondo": color, "span": n, "bordes": {…}, "mar": {…}, "va": …}.
        Con `cabecera`, la primera fila se repite en cada página y lleva el filete verde."""
        t = etree.Element(W + "tbl")
        tp = _e("tblPr", t)
        _e("tblW", tp, w=sum(anchos), type="dxa")
        if sangria:
            _e("tblInd", tp, w=sangria, type="dxa")
        _e("tblLayout", tp, type="fixed")
        mar = _e("tblCellMar", tp)
        for lado, v in (("top", 70), ("left", 0), ("bottom", 70), ("right", 113)):
            _e(lado, mar, w=v, type="dxa")
        grid = _e("tblGrid", t)
        for a in anchos:
            _e("gridCol", grid, w=a)
        for nf, fila in enumerate(filas):
            tr = _e("tr", t)
            trp = _e("trPr", tr)
            _e("cantSplit", trp)
            es_cab = cabecera and nf == 0
            if es_cab:
                _e("tblHeader", trp)
            col = 0
            for celda in fila:
                d = celda if isinstance(celda, dict) else {"p": celda}
                span = d.get("span", 1)
                tc = _e("tc", tr)
                tcp = _e("tcPr", tc)
                _e("tcW", tcp, w=sum(anchos[col:col + span]), type="dxa")
                if span > 1:
                    _e("gridSpan", tcp, val=span)
                if "bordes" in d:
                    bordes = d["bordes"]
                elif es_cab:
                    bordes = {"bottom": (10, self.c["v7"])}
                else:
                    bordes = {"bottom": (4, self.c["l"])}
                if filete_sup and nf == 0 and not es_cab:
                    bordes = {**bordes, "top": (10, self.c["v7"])}
                _borde(tcp, bordes)
                if d.get("fondo"):
                    _e("shd", tcp, val="clear", color="auto", fill=self.c.get(d["fondo"], d["fondo"]))
                if d.get("mar"):
                    m = _e("tcMar", tcp)
                    for lado in ("top", "left", "bottom", "right"):
                        if lado in d["mar"]:
                            _e(lado, m, w=d["mar"][lado], type="dxa")
                _e("vAlign", tcp, val=d.get("va", "bottom" if es_cab else "top"))
                contenido = d.get("p")
                if contenido is None or contenido == "":
                    contenido = self.parrafo((), "TablaTexto")
                if not isinstance(contenido, list):
                    contenido = [contenido]
                tc.extend(contenido)
                col += span
        return t

    def celda(self, segmentos, estilo: str = "TablaTexto", jc: str | None = None):
        return self.parrafo(segmentos, estilo, jc=jc)

    # -- piezas del diseño -------------------------------------------------------------------------------------------
    def apertura(self, numero: str, titulo: str, base: list[str], ancho: int | None = None,
                 pendiente: bool = False, grupo: str | None = "norma", indice: bool = True) -> list:
        """Número en la columna de margen con su filete de oro; título y base a la derecha."""
        ancho = ancho or self.ancho
        num = self.parrafo(numero, "ApNumero") if numero else self.parrafo((), "ApNumero")
        regla = self.parrafo((), "ApRegla", ind=(0, self.col - 624))
        p_tit = self.parrafo(titulo, "ApTitulo")
        if indice:
            self.entradas.append((numero, titulo, self.marca(p_tit), pendiente, grupo))
        p_base = self.parrafo("  ·  ".join(base), "ApBase")
        sin = {}
        t = self.tabla([self.col, ancho - self.col], [[{"p": [num, regla], "bordes": sin, "mar": {"top": 0}},
                                                      {"p": [p_tit, p_base], "bordes": sin,
                                                       "mar": {"left": self.sangria - self.col, "top": 0}}]])
        for p in t.iter(W + "p"):
            ooxml.hijo(ooxml.ppr(p), "keepNext", ooxml.ORDEN_PPR)
        return [t, self.separador(260)]

    def subapartado(self, numero: str, titulo: str):
        p = self.parrafo((), "Subapartado")
        r = _e("r", p)
        _e("tab", r)
        if numero:
            p.append(ooxml.run(numero, self.rpr(estilo="SubNumero")))
        r = _e("r", p)
        _e("tab", r)
        p.append(ooxml.run(titulo))
        return p

    def aviso(self, etiqueta: str, lineas: list, ancho: int | None = None) -> list:
        """«Pendiente» o «Borrador»: filetes de oro arriba y abajo, etiqueta a la izquierda (sin caja ni barra)."""
        ancho = (ancho or self.ancho) - self.sangria
        oro = (7, self.c["oro"])
        bordes = {"top": oro, "bottom": oro}
        et = self.parrafo(Estilo(etiqueta, "MarcaPendiente"), "TablaTexto")
        cuerpo = [self.parrafo(x, "TablaTexto", despues=60) for x in lineas]
        t = self.tabla([1190, ancho - 1190], [[{"p": et, "bordes": bordes, "mar": {"top": 140, "bottom": 140}},
                                               {"p": cuerpo, "bordes": bordes, "mar": {"top": 140, "bottom": 140}}]],
                       sangria=self.sangria)
        return [t, self.separador(220)]

    def pendiente(self, pide: str, falta: str = "el texto acordado por el equipo docente") -> list:
        return self.aviso(PENDIENTE, [f"La guía pide: {pide}", Cursiva(f"Falta {falta}.")])

    def fuente(self, segmentos, sangria: int | None = None):
        p = self.parrafo(segmentos, "Fuente")
        if sangria:
            _e("ind", ooxml.ppr(p), left=sangria)
        return p

    def grupo(self, texto: str, n: int) -> list:
        return [{"p": self.celda(texto, "TablaGrupo"), "span": n, "bordes": {"bottom": (4, self.c["v7"])},
                 "mar": {"top": 170}}]

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
                out.append(self.subapartado(f"{apartado}.{len(subtitulos)}", s.lstrip("#").strip()))
            elif s.startswith(("- ", "* ")):
                cerrar()
                out.append(self.parrafo(en_linea(s[2:].strip()), "Vineta"))
            else:
                parrafo.append(s)
        cerrar()
        return out

    # -- secciones ---------------------------------------------------------------------------------------------------
    def fin_seccion(self, apaisada: bool = False, portada: bool = False, encabezados: bool = False):
        """Párrafo que cierra una sección (su sectPr define la sección que acaba en él)."""
        p = etree.Element(W + "p")
        pp = _e("pPr", p)
        s = _e("sectPr", pp)
        if portada:
            _e("headerReference", s, type="default", r_id="rIdEncabezadoPortada")
            _e("footerReference", s, type="default", r_id="rIdPiePortada")
        elif encabezados:
            _e("headerReference", s, type="default", r_id="rIdEncabezado")
            _e("footerReference", s, type="default", r_id="rIdPie")
        _e("type", s, val="nextPage")
        if apaisada:
            _e("pgSz", s, w=16838, h=11906, orient="landscape")
        else:
            _e("pgSz", s, w=11906, h=16838)
        m = self.margenes
        if portada:
            _e("pgMar", s, top=0, right=0, bottom=0, left=0, header=0, footer=680, gutter=0)
        elif apaisada:
            _e("pgMar", s, top=1247, right=1021, bottom=1247, left=1021, header=567, footer=510, gutter=0)
        else:
            _e("pgMar", s, top=m["top"], right=m["right"], bottom=m["bottom"], left=m["left"], header=m["header"],
               footer=m["footer"], gutter=0)
        _e("cols", s, space=708)
        return p


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


def cita(n: Norma) -> str:
    """«Decreto 114/2025, de 29 de julio» aunque el diario la titule en mayúsculas («DECRETO 114/2025…»)."""
    return re.sub(r"^([A-ZÁÉÍÓÚÑ]{3,})\b", lambda m: m.group(1).capitalize(), n.cita)


def _enlace_norma(n: Norma) -> Enlace:
    return Enlace(n.titulo.rstrip("."), n.enlace)


ANCHO_APAISADA = 16838 - 2 * 1021


# ---------------------------------------------------------------------------------------------------------------------
# Portada y control del documento
# ---------------------------------------------------------------------------------------------------------------------
def portada(e: Escritor, ident: derivados.Identificacion, cat: Catalogo, borrador: bool, fecha: dt.date) -> list:
    c, f = e.c, e.f
    blanco = "FFFFFF"
    ancho = 11906
    m_izq, m_der = e.margenes["left"], e.margenes["right"]
    sin = {}

    def p(texto, rpr, jc=None, antes=0, despues=0):
        return e.parrafo(texto, None, jc=jc, rpr_base=rpr, antes=antes, despues=despues)

    sup = e.rpr(f["cond_semi"], 8.4, "CFE0D0", caps=True, esp=24)
    tit = e.parrafo((), None)
    tit.append(ooxml.run("Proyecto curricular", e.rpr(f["cond_semi"], 23, blanco)))
    br = _e("r", tit)
    _e("br", br)
    tit.append(ooxml.run("de ciclo formativo", e.rpr(f["cond_semi"], 23, blanco)))
    _e("spacing", ooxml.ppr(tit), line=250, lineRule="auto")
    regla = e.parrafo((), None, antes=300, ind=(0, ancho - m_izq - m_der - 1474))
    pb = _e("pBdr", ooxml.ppr(regla))
    _e("top", pb, val="single", sz=12, space=1, color=c["oro"])
    ooxml.ordenar(ooxml.ppr(regla), ooxml.ORDEN_PPR)
    siglas = p(ident.sigla, e.rpr(f["cond_extra"], 178, blanco))
    nombre = p(ident.nombre, e.rpr(f["cond_semi"], 13, "E3EDE3"), jc="right")
    verde = {"fondo": "v9", "bordes": sin}

    def alto(tr_hijo, tw):
        trp = tr_hijo.find(W + "trPr")
        _e("trHeight", trp, val=tw, hRule="exact")

    filas = [
        [{**verde, "p": p("Escuelas Profesionales Luis Amigó", sup), "mar": {"top": 850, "left": m_izq}},
         {**verde, "p": p(f"Curso {ident.curso}", sup, jc="right"), "mar": {"top": 850, "right": m_der}}],
        [{**verde, "p": [tit, regla], "span": 2, "mar": {"top": 1250, "left": m_izq}}],
        [{**verde, "p": siglas, "va": "bottom", "mar": {"left": 936, "bottom": 0}},
         {**verde, "p": nombre, "va": "bottom", "mar": {"right": m_der, "bottom": 680}}],
    ]
    if borrador:
        filas.append([{"fondo": "oro", "bordes": sin, "span": 2, "va": "center", "mar": {"left": m_izq, "top": 0, "bottom": 0},
                       "p": p("Borrador · pendiente de aprobación por el departamento",
                              e.rpr(f["cond"], 8.4, "t", b=True, caps=True, esp=24))}])
    else:
        filas.append([{"fondo": "oro", "bordes": sin, "span": 2, "p": e.separador()}])
    t = e.tabla([6237, ancho - 6237], filas)
    for p_ in t.iter(W + "p"):   # sin guiones en la portada
        ooxml.hijo(ooxml.ppr(p_), "suppressAutoHyphens", ooxml.ORDEN_PPR)
    trs = t.findall(W + "tr")
    for tr, h in zip(trs, (1701, 3402, 4536, 397 if borrador else 113), strict=True):
        alto(tr, h)

    dep = ident.departamento
    norma_cur = cat.normas.get(apartados.norma(ident.grado))
    datos = [
        ("Título", ident.titulo), ("Grado", f"{ident.grado_largo} · {ident.horas_total} horas"),
        ("Familia profesional", ident.familia),
        ("Departamento", dep["nombre"] if dep else Estilo(PENDIENTE, "MarcaPendiente")),
        ("Jefatura del departamento", dep["jefatura"] if dep else Estilo(PENDIENTE, "MarcaPendiente")),
        ("Curso académico", ident.curso),
        ("Real decreto del título", cita(ident.rd) if ident.rd else Estilo(PENDIENTE, "MarcaPendiente")),
        ("Currículo", cita(norma_cur) if norma_cur else Estilo(PENDIENTE, "MarcaPendiente")),
        ("Revisión", f"0 · {fecha.isoformat()}" + (" · borrador" if borrador else "")),
    ]
    anchos = [3800, 2976, ancho - m_izq - m_der - 3800 - 2976]
    celdas = []
    for k, v in datos:
        et = e.parrafo(k, "TablaEtiqueta", despues=80)
        bdr = _e("pBdr", ooxml.ppr(et))
        _e("bottom", bdr, val="single", sz=4, space=3, color=c["l"])
        ooxml.ordenar(ooxml.ppr(et), ooxml.ORDEN_PPR)
        val = e.parrafo(v, "TablaTexto", despues=220, rpr_base=e.rpr(sz=9.6))
        ooxml.hijo(ooxml.ppr(val), "suppressAutoHyphens", ooxml.ORDEN_PPR)
        celdas.append({"p": [et, val], "bordes": sin, "mar": {"right": 397}})
    ficha = e.tabla(anchos, [celdas[0:3], celdas[3:6], celdas[6:9]], sangria=m_izq)
    return [t, e.separador(400), ficha, e.fin_seccion(portada=True)]


def control(e: Escritor, ident: derivados.Identificacion, borrador: bool, fecha: dt.date) -> list:
    dep = ident.departamento
    pend = Estilo(PENDIENTE, "MarcaPendiente")
    out = e.apertura("", "Control del documento", ["Instrucciones de inicio de curso · §6 y §19", f"{GUIA} · 2.2"],
                     indice=False)
    out.append(e.parrafo("El proyecto curricular recoge los acuerdos pedagógicos y organizativos comunes a todos los "
                         "módulos del ciclo. Su contenido es vinculante y no se repite en las programaciones "
                         "didácticas."))
    filas = [
        ("Elaboración", "Equipo docente del ciclo, con el profesorado de materias no profesionales que imparte "
                        "docencia en él"),
        ("Coordinación", f"Jefatura del departamento de {dep['nombre']}" if dep else pend),
        ("Aprobación", [pend, " · fecha y órgano"]),
        ("Incorporación a la PGA", "Jefatura de estudios de Formación Profesional"),
        ("Evaluación del PCCF", "Equipo educativo del ciclo, según el plan que la comisión de coordinación pedagógica "
                                "propone al claustro"),
        ("Vigencia", f"Curso {ident.curso}. Documento vivo: se revisa durante los dos cursos del ciclo y recoge las "
                     "propuestas de mejora de la memoria final"),
    ]
    out.append(e.tabla([1900, e.ancho - e.sangria - 1900],
                       [[e.celda(k, "TablaEtiqueta"), e.celda(v)] for k, v in filas], sangria=e.sangria))
    out.append(e.subapartado("", "Registro de revisiones"))
    cab = [e.celda(x, "TablaCabecera") for x in ("Rev.", "Fecha", "Apartados", "Motivo", "Estado")]
    rev = [e.celda(Estilo("0", "Codigo")), e.celda(Estilo(fecha.isoformat(), "Codigo")), e.celda("Todos y anexos"),
           e.celda("Primera redacción a partir del catálogo y de la carpeta de datos del ciclo"),
           e.celda("Borrador" if borrador else "Para aprobar")]
    vacias = [[e.celda("") for _ in range(5)] for _ in range(2)]
    resto = e.ancho - e.sangria
    out.append(e.tabla([620, 1250, 1500, resto - 620 - 1250 - 1500 - 1100, 1100], [cab, rev] + vacias,
                       sangria=e.sangria, cabecera=True))
    out.append(e.separador(900))
    firmas = []
    for quien in ("Jefatura del departamento", "Jefatura de estudios de FP", "Dirección"):
        firmas.append({"p": [e.celda(quien, "TablaCabecera"), e.celda("Firma y fecha", "Fuente")],
                       "bordes": {"top": (5, e.c["t3"])}, "mar": {"right": 397, "bottom": 1200}})
    tercio = resto // 3
    out.append(e.tabla([tercio, tercio, resto - 2 * tercio], [firmas], sangria=e.sangria))
    out.append(e.salto_pagina())
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Apartados
# ---------------------------------------------------------------------------------------------------------------------
def base(a: apartados.Apartado, origen: str | None = None) -> list[str]:
    b = ([f"Decreto 114/2025 · art. {'8.4'}"] if a.origen == "norma" else []) + [f"{GUIA} · {a.guia}"]
    return b + ([origen] if origen else [])


def apartado_1(e: Escritor, ident: derivados.Identificacion, avisos: list[str]) -> list:
    dep = ident.departamento
    if dep is None:
        avisos.append("Apartado 1: falta el departamento del ciclo (centro/departamentos.yaml)")
    if ident.tutorias is None:
        avisos.append("Apartado 1: faltan las tutorías (equipo.yaml del curso)")
    pend = Estilo(PENDIENTE, "MarcaPendiente")
    ficha = [
        ("Ciclo formativo", f"{ident.sigla} · {ident.nombre}"), ("Título", ident.titulo),
        ("Grado", ident.grado_largo), ("Familia profesional", ident.familia),
        ("Real decreto del título", _enlace_norma(ident.rd) if ident.rd else pend),
        ("Duración", f"{ident.horas_total} horas"),
        ("Centro", "Escuelas Profesionales Luis Amigó · Godella (Valencia)"),
        ("Departamento", dep["nombre"] if dep else pend),
        ("Jefatura del departamento", dep["jefatura"] if dep else pend),
        ("Curso académico", ident.curso),
        ("Tutorías", " · ".join(f"{g}: {n}" for g, n in ident.tutorias) if ident.tutorias else pend),
    ]
    out = [e.tabla([e.col, e.ancho - e.sangria - e.col],
                   [[e.celda(k, "TablaEtiqueta"), e.celda(v)] for k, v in ficha],
                   sangria=e.sangria, filete_sup=True)]
    out.append(e.subapartado("1.1", "Equipo docente"))
    sin = [m for m in ident.modulos if m.docentes is None]
    if sin:
        avisos.append(f"Apartado 1: sin profesorado en {len(sin)} módulos ({', '.join(m.clave for m in sin)})")
    resto = e.ancho - e.sangria
    anchos = [960, resto - 960 - 680 - 2300, 680, 2300]
    filas = [[e.celda(x, "TablaCabecera", jc="right" if x == "Horas" else None)
              for x in ("Código", "Módulo profesional", "Horas", "Profesorado")]]
    curso = None
    for m in ident.modulos:
        if m.curso != curso:
            filas.append(e.grupo(f"{m.curso}.º curso", 4))
            curso = m.curso
        filas.append([e.celda(Estilo(m.codigo, "Codigo")),
                      e.celda(m.nombre + (" (optativo)" if m.clave.startswith("OPT-") or m.tipo == "optativo" else "")),
                      e.celda(str(m.horas), jc="right"),
                      e.celda(" / ".join(m.docentes) if m.docentes else pend)])
    out.append(e.tabla(anchos, filas, sangria=e.sangria, cabecera=True))
    out.append(e.fuente([Negrita("Fuente: "), "catálogo curricular (horas del currículo) y equipo docente del curso. "
                         "Las optativas, una por fila."], e.sangria))
    if not ident.equipo_confirmado:
        avisos.append(f"Apartado 1: equipo docente sin confirmar{f' ({ident.equipo_origen})' if ident.equipo_origen else ''}")
        out += e.aviso(*_sin_confirmar("Equipo docente", ident.equipo_origen))
    return out


def _sin_confirmar(que: str, origen: str) -> tuple[str, list[str]]:
    """La etiqueta y el texto del aviso de algo sin confirmar: heredado del curso anterior o en borrador."""
    if origen.startswith("heredado del curso "):
        return "Heredado", [f"{que} heredado del curso {origen.rsplit(' ', 1)[-1]}: pendiente de revisar y confirmar "
                            "por el equipo docente y de aprobar por el departamento."]
    return "Borrador", [f"{que} en borrador: pendiente de revisar y confirmar por el equipo docente y de aprobar por "
                        "el departamento."]


def apartado_2(e: Escritor, marco: dict[str, list[Norma]]) -> list:
    out = [e.subapartado("2.1", "Normativa estatal")]
    out += [e.parrafo(_enlace_norma(n), "Vineta") for n in marco["estatal"]]
    out.append(e.subapartado("2.2", "Normativa autonómica (Comunitat Valenciana)"))
    out += [e.parrafo(_enlace_norma(n), "Vineta") for n in marco["autonomico"]]
    return out


def apartado_3(e: Escritor, a: apartados.Apartado, k: derivados.Contribucion) -> list:
    out = e.pendiente(a.pide, "el análisis del contexto y el peso de cada competencia profesional (suma 100 %)")
    resto = e.ancho - e.sangria
    filas = [[e.celda("Letra", "TablaCabecera"), e.celda("Competencia profesional del título", "TablaCabecera"),
              e.celda("Peso", "TablaCabecera", jc="right")]]
    for letra, texto in k.competencias:
        filas.append([e.celda(Estilo(letra, "Codigo")), e.celda(texto), e.celda("—", jc="right")])
    filas.append([{"p": e.celda(""), "bordes": {"top": (10, e.c["v7"])}},
                  {"p": e.celda(Negrita("Total (suma 100 %)")), "bordes": {"top": (10, e.c["v7"])}},
                  {"p": e.celda("—", jc="right"), "bordes": {"top": (10, e.c["v7"])}}])
    out.append(e.tabla([620, resto - 620 - 900, 900], filas, sangria=e.sangria, cabecera=True))
    return out


def apartado_4(e: Escritor, k: derivados.Contribucion, cat: Catalogo) -> list:
    """Matriz módulo × competencia en página apaisada: celda verde = contribuye (DESIGN.md: «Matriz»)."""
    letras = [x[0] for x in k.competencias]
    rd = cat.normas.get(k.fuente)
    w_letra, w_cod, w_cnt = 408, 900, 1250
    w_nom = ANCHO_APAISADA - w_cod - w_cnt - w_letra * len(letras)
    anchos = [w_cod, w_nom] + [w_letra] * len(letras) + [w_cnt]
    cab = [e.celda("Código", "TablaCabecera"), e.celda("Módulo profesional", "TablaCabecera")]
    cab += [e.celda(x, "TablaCabecera", jc="center") for x in letras]
    cab.append(e.celda("Competencias", "TablaCabecera", jc="right"))
    for c in cab[2:-1]:   # las letras, en minúscula y más grandes que el resto de la cabecera
        r = e.rpr(e.f["cond"], 9, "v9", b=True)
        r.find(W + "bCs").addnext(etree.Element(W + "caps", {W + "val": "0"}))
        c.find(f"{W}r").insert(0, r)
    filas = [cab]
    vistos: dict[tuple[str, str], int] = {}
    for fila, _ in k.filas:
        vistos[(fila.codigo, fila.nombre)] = vistos.get((fila.codigo, fila.nombre), 0) + 1
    hechos, curso = set(), None
    blanco = (8, "FFFFFF")
    for fila, ls in k.filas:
        clave = (fila.codigo, fila.nombre)
        if clave in hechos:
            continue
        hechos.add(clave)
        if fila.curso != curso:
            filas.append(e.grupo(f"{fila.curso}.º curso", len(anchos)))
            curso = fila.curso
        nombre = [fila.nombre] + ([Estilo("  (1.º y 2.º)", "PieTotal")] if vistos[clave] > 1 else [])
        celdas = [e.celda(Estilo(fila.codigo, "Codigo")), e.celda(nombre)]
        for x in letras:
            fondo = "v7" if x in ls else ("l2" if ls else None)
            celdas.append({"p": e.celda(""), "fondo": fondo,
                           "bordes": {"left": blanco, "right": blanco, "bottom": (4, e.c["l"] if not fondo else "FFFFFF")}})
        celdas.append(e.celda(str(len(ls)) if ls else Estilo("sin orientación", "MarcaPendiente"), jc="right"))
        filas.append(celdas)
    out = [e.tabla(anchos, filas, cabecera=True)]
    nota = [Negrita("Fuente: "), "orientaciones pedagógicas del real decreto del título"]
    if rd:
        nota += [" (", _enlace_norma(rd), ")"]
    nota.append(", módulo a módulo. Sin ajustes del equipo. Los módulos sin orientación (los nuevos de la LO 3/2022) "
                "no tienen competencias asignadas: su contribución la decide el equipo. El texto de cada competencia, "
                "en 4.1.")
    out.append(e.fuente(nota))
    return out


def competencias_4_1(e: Escritor, k: derivados.Contribucion) -> list:
    out = [e.subapartado("4.1", "Competencias profesionales, personales y sociales del título")]
    for x, t in k.competencias:
        p = e.parrafo([Negrita(f"{x})"), f" {t}"], despues=90)
        _e("ind", ooxml.ppr(p), left=e.sangria + 340, hanging=340)
        out.append(p)
    return out


def apartado_7(e: Escritor, a: apartados.Apartado, ident: derivados.Identificacion) -> list:
    out = e.pendiente(a.pide, "decidir si hay agrupaciones intermodulares (columna «Módulo del PCCF»)")
    resto = e.ancho - e.sangria
    anchos = [960, resto - 960 - 680 - 680 - 1700, 680, 680, 1700]
    filas = [[e.celda("Código", "TablaCabecera"), e.celda("Módulo del currículo", "TablaCabecera"),
              e.celda("Horas", "TablaCabecera", jc="right"), e.celda("H/sem.", "TablaCabecera", jc="right"),
              e.celda("Módulo del PCCF", "TablaCabecera")]]
    curso = None
    for m in ident.modulos:
        if m.curso != curso:
            filas.append(e.grupo(f"{m.curso}.º curso", 5))
            curso = m.curso
        filas.append([e.celda(Estilo(m.codigo, "Codigo")), e.celda(m.nombre), e.celda(str(m.horas), jc="right"),
                      e.celda(str(m.h_sem), jc="right"), e.celda("—")])
    out.append(e.tabla(anchos, filas, sangria=e.sangria, cabecera=True))
    out.append(e.fuente([Negrita("Fuente: "), "catálogo curricular (horas del currículo)."], e.sangria))
    return out


def apartado_20(e: Escritor, ident: derivados.Identificacion) -> list:
    out = [e.parrafo("Cada módulo tiene su programación didáctica, que se elabora teniendo en cuenta este proyecto "
                     "curricular (Decreto 114/2025, art. 8.3) y forma parte de la Programación General Anual. Lo "
                     "acordado aquí no se repite en ellas.")]
    resto = e.ancho - e.sangria
    filas = [[e.celda("Código", "TablaCabecera"), e.celda("Módulo profesional", "TablaCabecera"),
              e.celda("Curso", "TablaCabecera", jc="right")]]
    vistos = set()
    for m in ident.modulos:
        if (m.codigo, m.nombre) in vistos:
            continue
        vistos.add((m.codigo, m.nombre))
        filas.append([e.celda(Estilo(m.codigo, "Codigo")), e.celda(m.nombre), e.celda(f"{m.curso}.º", jc="right")])
    out.append(e.tabla([960, resto - 960 - 900, 900], filas, sangria=e.sangria, cabecera=True))
    return out


def bloques_de(e: Escritor, lista: list[Bloque], n: int, avisos: list[str], subtitulos: list[int]) -> list:
    out = []
    for b in sorted(lista, key=lambda b: (b.orden if b.orden is not None else 999, b.ruta.name)):
        out += e.markdown(b.cuerpo, n, subtitulos)
        if not b.confirmado:
            heredado = b.origen.startswith("heredado del curso ")
            avisos.append(f"Apartado {n}: «{b.ruta.name}» {b.origen if heredado else 'está en borrador'}, sin confirmar")
            out += e.aviso(*_sin_confirmar("Texto", b.origen))
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Anexos
# ---------------------------------------------------------------------------------------------------------------------
def _campos(e: Escritor, bloques: list[tuple[str, list[str]]]) -> etree._Element:
    resto = e.ancho - e.sangria
    puntos = {"bottom": (4, e.c["t3"])}
    filas = []
    for cat_, campos in bloques:
        for i, c in enumerate(campos):
            filas.append([{"p": e.celda(cat_ if i == 0 else "", "TablaGrupo"), "bordes": {}},
                          {"p": e.celda(c, "TablaEtiqueta"), "bordes": {}},
                          {"p": e.celda(""), "bordes": puntos}])
    return e.tabla([1700, 2300, resto - 4000], filas, sangria=e.sangria)


def anexo_a(e: Escritor, curso: str) -> list:
    out = [e.salto_pagina()]
    out += e.apertura("A", "Ficha de empresa u organismo equiparado colaborador",
                      [f"{GUIA} · anexo III", "Apartado 9"], grupo="anexo")
    out.append(e.parrafo("Una ficha por empresa. La actualiza la tutoría de la formación en empresa al terminar el "
                         "periodo lectivo, con el historial de colaboración y la valoración de la relación según el "
                         "alumnado que ha pasado por ella. Los datos de las empresas se guardan en la carpeta de datos "
                         "del ciclo."))
    out.append(_campos(e, [("Información general", ["Nombre de la empresa", "Sector o actividad principal",
                                                    "CIF/NIF", "Tamaño de la empresa", "Web"]),
                           ("Contacto", ["Persona de contacto", "Puesto o rol en la empresa", "Teléfono de contacto",
                                         "Correo electrónico"])]))
    out.append(e.subapartado("A.1", "Historial de colaboración y evaluación de la relación"))
    ini = int(curso[:4])
    resto = e.ancho - e.sangria
    filas = [[e.celda(x, "TablaCabecera") for x in ("Curso", "Alumnado", "RA trabajados en la empresa", "Valoración")]]
    for k in range(4):
        filas.append([e.celda(Estilo(f"{ini - k}-{ini - k + 1}", "Codigo")), e.celda(""), e.celda(""), e.celda("")])
    out.append(e.tabla([1250, 1900, resto - 1250 - 1900 - 1900, 1900], filas, sangria=e.sangria, cabecera=True))
    return out


def anexo_b(e: Escritor, ident: derivados.Identificacion) -> list:
    out = [e.salto_pagina()]
    out += e.apertura("B", "Programa formativo personalizado", [f"{GUIA} · anexo IV", "Apartado 10",
                                                                 "LO 3/2022 · art. 58"], grupo="anexo")
    out.append(e.parrafo("Uno por alumna o alumno, con el modelo de la guía. Lo preparan el profesorado de los módulos "
                         "y la tutoría con la empresa u organismo equiparado."))
    out.append(_campos(e, [
        ("Programa", ["Régimen", "Curso", "Grupo"]),
        ("Alumna o alumno", ["Nombre y apellidos", "DNI · NUSS", "Correo y teléfono", "Fecha de nacimiento",
                             "Nivel básico de PRL", "Otra certificación de PRL"]),
        ("Centro", ["Centro educativo · código", "Tutor/a del centro"]),
        ("Empresa", ["Denominación · CIF", "Tutor/a de empresa"]),
        ("Condiciones", ["Medidas o adaptaciones por discapacidad", "Autorizaciones extraordinarias",
                         "Intervalo de formación", "1.er periodo: calendario, horario y horas",
                         "2.º periodo: calendario, horario y horas", "Total de horas"])]))
    out.append(e.subapartado("B.1", "Reparto de los resultados de aprendizaje"))
    resto = e.ancho - e.sangria
    filas = [[e.celda(x, "TablaCabecera") for x in ("Código", "Módulo profesional", "RA", "Centro", "Empresa")]]
    vistos = set()
    for m in ident.modulos:
        if (m.codigo, m.nombre) in vistos or m.tipo in ("optativo",):
            continue
        vistos.add((m.codigo, m.nombre))
        filas.append([e.celda(Estilo(m.codigo, "Codigo")), e.celda(m.nombre), e.celda(""), e.celda(""), e.celda("")])
    out.append(e.tabla([960, resto - 960 - 3 * 1100, 1100, 1100, 1100], filas, sangria=e.sangria, cabecera=True))
    out.append(e.fuente([Negrita("Fuente: "), "módulos del catálogo curricular. En cada módulo se indica si se imparte "
                         "por completo en el centro o en colaboración con empresas y las horas en la empresa."],
                        e.sangria))
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Contenido (índice) y retoques
# ---------------------------------------------------------------------------------------------------------------------
def _fld(tipo: str):
    r = etree.Element(W + "r")
    etree.SubElement(r, W + "fldChar", {W + "fldCharType": tipo})
    return r


def _instr(texto: str):
    r = etree.Element(W + "r")
    t = etree.SubElement(r, W + "instrText", {ooxml.XML_SPACE: "preserve"})
    t.text = texto
    return r


GRUPOS = {"norma": "Apartados del Decreto 114/2025, art. 8.4", "guia": "Apartados que añade la guía de la DGFP",
          "anexo": "Anexos"}


def contenido(e: Escritor) -> list:
    """Entradas del contenido: número en la columna de margen, título enlazado, «pendiente» y página (PAGEREF)."""
    out, grupo = [], None
    for numero, titulo, marca, pendiente, g in e.entradas:
        if g != grupo:
            out.append(e.parrafo(GRUPOS[g], "IndiceGrupo"))
            grupo = g
        p = e.parrafo((), "IndiceEntrada")
        _e("tab", _e("r", p))
        p.append(ooxml.run(numero, e.rpr(estilo="IndiceNumero")))
        _e("tab", _e("r", p))
        h = _e("hyperlink", p, anchor=marca, history=1)
        h.append(ooxml.run(titulo))
        if pendiente:
            p.append(ooxml.run("  pendiente", e.rpr(estilo="MarcaPendiente")))
        _e("tab", _e("r", p))
        p.extend([_fld("begin"), _instr(f" PAGEREF {marca} \\h "), _fld("separate"),
                  ooxml.run("", e.rpr(estilo="IndicePagina")), _fld("end")])
        out.append(p)
    return out


def actualizar_campos(pq: ooxml.Paquete) -> None:
    """Que Word rehaga los números de página del contenido al abrir (w:updateFields, justo antes de w:compat, como
    pide el esquema)."""
    ajustes = pq.xml("word/settings.xml")
    uf = ooxml.hijo(ajustes, "updateFields", None, val="true")
    ajustes.remove(uf)
    compat = ajustes.find(W + "compat")
    (compat.addprevious if compat is not None else ajustes.append)(uf)


def rellenar_marcas(raiz, valores: dict[str, str]) -> None:
    for t in list(raiz.iter(W + "t")):
        if t.text and "{{" in t.text:
            t.text = RE_MARCA.sub(lambda m: valores.get(m.group(1), m.group(0)), t.text)
            if not t.text:   # marca vacía (sin borrador): fuera el run, con su fondo
                r = t.getparent()
                r.getparent().remove(r)
            elif t.text != t.text.strip():
                t.set(ooxml.XML_SPACE, "preserve")


def propiedades(pq: ooxml.Paquete, ident: derivados.Identificacion, cuando: dt.date) -> None:
    core = pq.xml("docProps/core.xml")
    ns = {"dc": "http://purl.org/dc/elements/1.1/", "dcterms": "http://purl.org/dc/terms/"}
    t = core.find("dc:title", ns)
    if t is not None:
        t.text = f"Proyecto curricular de ciclo formativo · {ident.sigla} · {ident.curso}"
    for nombre in ("created", "modified"):
        x = core.find(f"dcterms:{nombre}", ns)
        if x is not None:
            x.text = f"{cuando.isoformat()}T00:00:00Z"


def nombre_archivo(sigla: str, curso: str) -> str:
    return f"PCCF {sigla} {curso}.docx"


# ---------------------------------------------------------------------------------------------------------------------
# Generar
# ---------------------------------------------------------------------------------------------------------------------
def _borrador_previo(cat: Catalogo, datos: CarpetaDatos, sigla: str, curso: str, ident) -> bool:
    """¿Quedará algo pendiente o en borrador? (la portada lo necesita antes de escribir el cuerpo)."""
    todos = datos.bloques(sigla, curso)
    con_bloque = {b.apartado for b in todos}
    calculados = {1, 2, 4, 20}
    falta = any(a.n not in calculados and a.n not in con_bloque for a in apartados.apartados(ident.grado))
    return (falta or any(not b.confirmado for b in todos) or ident.departamento is None or ident.tutorias is None
            or not ident.equipo_confirmado)


def generar(cat: Catalogo, datos: CarpetaDatos, sigla: str, curso: str, opciones: Opciones | None = None) -> Resultado:
    opciones = opciones or Opciones()
    fecha = opciones.fecha or dt.date.today()
    avisos: list[str] = []
    ident = derivados.identificacion(cat, datos, sigla, curso)
    borrador = (_borrador_previo(cat, datos, sigla, curso, ident) if opciones.borrador is None
                else opciones.borrador)
    pq = cargar_plantilla()
    e = Escritor(pq)
    body = pq.xml("word/document.xml").find(W + "body")
    marca_cuerpo = next(p for p in body.findall(W + "p") if ooxml.texto(p).strip() == "{{cuerpo}}")

    cuerpo = portada(e, ident, cat, borrador, fecha)
    cuerpo += control(e, ident, borrador, fecha)
    cuerpo += e.apertura("", "Contenido", ["Apartados del proyecto curricular y anexos"], indice=False)
    marca_indice = e.separador()
    cuerpo.append(marca_indice)
    cuerpo.append(e.salto_pagina())

    todos = datos.bloques(sigla, curso)
    k = derivados.contribucion(cat, sigla)
    primera = True
    for a in apartados.apartados(ident.grado):
        propios = [b for b in todos if b.apartado == a.n]
        calculado = a.n in (1, 2, 4, 20)
        pendiente = not calculado and not propios
        grupo = "norma" if a.origen == "norma" else "guia"
        subtitulos: list[int] = []
        if a.n == 4:
            # sección apaisada solo para la matriz; el 4.1 vuelve a la vertical
            cuerpo.append(e.fin_seccion(encabezados=primera))
            primera = False
            cuerpo += e.apertura(str(a.n), a.titulo, base(a, "Se calcula del real decreto del título"),
                                 ancho=ANCHO_APAISADA, grupo=grupo)
            cuerpo += apartado_4(e, k, cat)
            cuerpo.append(e.fin_seccion(apaisada=True))
            cuerpo += competencias_4_1(e, k)
            subtitulos.append(1)
            cuerpo += bloques_de(e, propios, a.n, avisos, subtitulos)
            continue
        origen = {1: "Catálogo y carpeta de datos", 2: "Catálogo de normativa · vigía", 7: "Catálogo curricular",
                  20: "Catálogo curricular"}.get(a.n)
        if propios and not origen:
            tipos = {b.tipo for b in propios}
            origen = f"Bloque de {'centro' if tipos == {'centro'} else 'ciclo' if tipos == {'ciclo'} else 'equipo'}"
            if any(not b.confirmado for b in propios):
                origen += " · borrador"
        cuerpo += e.apertura(str(a.n), a.titulo, base(a, origen), pendiente=pendiente, grupo=grupo)
        if a.n == 1:
            cuerpo += apartado_1(e, ident, avisos)
            subtitulos.append(1)
        elif a.n == 2:
            cuerpo += apartado_2(e, derivados.marco_normativo(cat, sigla, curso))
            subtitulos += [1, 1]
        elif a.n == 3 and not propios:
            cuerpo += apartado_3(e, a, k)
            avisos.append("Apartado 3: pendiente")
        elif a.n == 7 and not propios:
            cuerpo += apartado_7(e, a, ident)
            avisos.append("Apartado 7: pendiente (agrupaciones)")
        elif a.n == 20:
            cuerpo += apartado_20(e, ident)
        elif pendiente:
            cuerpo += e.pendiente(a.pide)
            avisos.append(f"Apartado {a.n}: pendiente")
        cuerpo += bloques_de(e, propios, a.n, avisos, subtitulos)
        cuerpo.append(e.separador(300))
    cuerpo += anexo_a(e, ident.curso)
    cuerpo += anexo_b(e, ident)

    padre, i = marca_cuerpo.getparent(), marca_cuerpo.getparent().index(marca_cuerpo)
    padre.remove(marca_cuerpo)
    for j, x in enumerate(cuerpo):
        padre.insert(i + j, x)
    padre, i = marca_indice.getparent(), marca_indice.getparent().index(marca_indice)
    for j, x in enumerate(contenido(e)):
        padre.insert(i + j, x)

    valores = {"sigla": ident.sigla, "curso": ident.curso, "borrador": "Borrador" if borrador else "",
               "correo_pie": f" · {opciones.correo_pie}" if opciones.correo_pie else ""}
    for n in sorted(pq.partes):
        if re.fullmatch(r"word/(document|header\d+|footer\d+)\.xml", n):
            rellenar_marcas(pq.xml(n), valores)
    restos = RE_MARCA.findall(ooxml.texto(body))
    if restos:
        raise ValueError(f"Marcas sin rellenar: {restos[:5]}")
    actualizar_campos(pq)
    pq.quitar_relaciones_huerfanas("word/document.xml")
    propiedades(pq, ident, fecha)
    return Resultado(docx=pq.a_bytes(), avisos=avisos, borrador=borrador)
