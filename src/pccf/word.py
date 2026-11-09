"""Un bloque en Word (ADR-020): exportarlo para que alguien del equipo lo escriba o lo revise en Word, e importarlo de
vuelta; también cualquier Word con texto para un bloque nuevo. Sin Qt: solo lxml y zipfile.

- **Exportar** da un `.docx` sencillo con el texto del bloque (subtítulos en Título 2, viñetas, negrita, enlaces y las
  notas internas sombreadas) y, en sus propiedades personalizadas, la cabecera del bloque y el nombre de su archivo,
  que Word y LibreOffice conservan al guardar. Así se devuelve a su sitio al importarlo.
- **Importar** lee de cualquier Word lo que el documento del PCCF sabe escribir: títulos → subtítulos; listas (con
  viñetas o números) → viñetas; negrita; hipervínculos; el estilo «Nota interna» → nota. Lo demás (letra, tamaño,
  color, cursiva, imágenes) se descarta; el texto de las tablas entra como párrafos, con un aviso.
"""
from __future__ import annotations

import html
import io
import re
import zipfile
from dataclasses import dataclass, field

from lxml import etree

from pccf.texto import Parrafo, Trozo, de_trozos, limpio, trozos

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PR = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_CUSTOM = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
NS_VT = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
W = "{%s}" % NS_W
R = "{%s}" % NS_R

PROP_CABECERA = "PCCF bloque"
PROP_ARCHIVO = "PCCF archivo"
ESTILO_NOTA = "Nota interna"
ESTILO_AVISO = "PCCF aviso"     # el párrafo de arriba que explica el archivo: no se importa
FUENTE = "Calibri"


class WordNoValido(ValueError):
    pass


@dataclass
class Importado:
    parrafos: list[Parrafo]
    cabecera: str | None = None        # YAML de la cabecera del bloque, si el Word viene de «Exportar»
    archivo: str | None = None         # nombre del archivo del bloque
    avisos: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------------------------------------------------
# Exportar
# ---------------------------------------------------------------------------------------------------------------------
def _x(t: str) -> str:
    return html.escape(t, quote=True)


def _runs(texto: str, rels: list[str], negrita: bool = False) -> str:
    out = []
    for t in trozos(texto):
        rpr = "<w:rPr><w:b/></w:rPr>" if (t.negrita or negrita) and not t.url else ""
        run = f'<w:r>{rpr}<w:t xml:space="preserve">{_x(t.texto)}</w:t></w:r>'
        if t.url:
            rels.append(t.url)
            run = (f'<w:hyperlink r:id="rIdEnlace{len(rels)}" w:history="1"><w:r><w:rPr><w:rStyle w:val="Hyperlink"/>'
                   f'</w:rPr><w:t xml:space="preserve">{_x(t.texto)}</w:t></w:r></w:hyperlink>')
        out.append(run)
    return "".join(out)


def _p(estilo: str | None, cuerpo: str) -> str:
    ppr = f'<w:pPr><w:pStyle w:val="{estilo}"/></w:pPr>' if estilo else ""
    return f"<w:p>{ppr}{cuerpo}</w:p>"


ESTILOS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{NS_W}">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{FUENTE}" w:hAnsi="{FUENTE}" w:cs="{FUENTE}"/>
<w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="es-ES"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>
<w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="240" w:after="80"/><w:outlineLvl w:val="1"/>
</w:pPr><w:rPr><w:b/><w:color w:val="2C7A3A"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:basedOn w:val="Normal"/>
<w:qFormat/><w:pPr><w:numPr><w:numId w:val="1"/></w:numPr><w:spacing w:after="60"/></w:pPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="NotaInterna"><w:name w:val="{ESTILO_NOTA}"/>
<w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:shd w:val="clear" w:color="auto" w:fill="F2ECF8"/>
<w:ind w:left="170" w:right="170"/></w:pPr><w:rPr><w:i/><w:color w:val="5E3D78"/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="PCCFAviso"><w:name w:val="{ESTILO_AVISO}"/>
<w:basedOn w:val="Normal"/><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="4" w:space="6" w:color="BFC8C1"/></w:pBdr>
<w:spacing w:after="240"/></w:pPr><w:rPr><w:color w:val="5D6B60"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr>
</w:style>
<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/><w:rPr><w:color w:val="0563C1"/>
<w:u w:val="single"/></w:rPr></w:style>
</w:styles>"""

NUMERACION = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="{NS_W}"><w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="singleLevel"/>
<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/>
<w:pPr><w:ind w:left="360" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum>
<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>"""

TIPOS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/>
</Types>"""

RAIZ_RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{NS_PR}">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties" Target="docProps/custom.xml"/>
</Relationships>"""  # noqa: E501


def exportar(parrafos: list[Parrafo], titulo: str, aviso: str, cabecera: str | None = None,
             archivo: str | None = None) -> bytes:
    """El `.docx` de un bloque: arriba, el aviso (no se importa); debajo, el texto. `cabecera` y `archivo` viajan en
    las propiedades personalizadas para devolverlo a su sitio."""
    rels: list[str] = []
    cuerpo = [_p("PCCFAviso", _runs(aviso, rels))]
    for p in parrafos:
        estilo = {"subtitulo": "Heading2", "vineta": "ListBullet", "nota": "NotaInterna"}.get(p.clase)
        cuerpo.append(_p(estilo, _runs(p.texto, rels)))
    if len(cuerpo) == 1:
        cuerpo.append(_p(None, ""))
    documento = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document xmlns:w="{NS_W}" '
                 f'xmlns:r="{NS_R}"><w:body>{"".join(cuerpo)}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
                 '<w:pgMar w:top="1418" w:right="1418" w:bottom="1418" w:left="1418" w:header="709" w:footer="709" '
                 'w:gutter="0"/></w:sectPr></w:body></w:document>')
    doc_rels = [f'<Relationship Id="rIdEstilos" Type="{NS_R}/styles" Target="styles.xml"/>',
                f'<Relationship Id="rIdNumeracion" Type="{NS_R}/numbering" Target="numbering.xml"/>']
    doc_rels += [f'<Relationship Id="rIdEnlace{i}" Type="{NS_R}/hyperlink" Target="{_x(u)}" TargetMode="External"/>'
                 for i, u in enumerate(rels, 1)]
    props = []
    for i, (nombre, valor) in enumerate(((PROP_CABECERA, cabecera), (PROP_ARCHIVO, archivo)), 2):
        if valor:
            props.append(f'<property fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" pid="{i}" name="{nombre}">'
                         f"<vt:lpwstr>{_x(valor)}</vt:lpwstr></property>")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<cp:coreProperties xmlns:cp="http://schemas.'
            'openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">'
            f"<dc:title>{_x(titulo)}</dc:title><dc:creator>PCCF</dc:creator></cp:coreProperties>")
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", TIPOS)
        z.writestr("_rels/.rels", RAIZ_RELS)
        z.writestr("word/document.xml", documento)
        z.writestr("word/styles.xml", ESTILOS)
        z.writestr("word/numbering.xml", NUMERACION)
        z.writestr("word/_rels/document.xml.rels", f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                   f'<Relationships xmlns="{NS_PR}">{"".join(doc_rels)}</Relationships>')
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/custom.xml", f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                   f'<Properties xmlns="{NS_CUSTOM}" xmlns:vt="{NS_VT}">{"".join(props)}</Properties>')
    return salida.getvalue()


# ---------------------------------------------------------------------------------------------------------------------
# Importar
# ---------------------------------------------------------------------------------------------------------------------
def _xml(z: zipfile.ZipFile, nombre: str) -> etree._Element | None:
    try:
        datos = z.read(nombre)
    except KeyError:
        return None
    return etree.fromstring(datos, etree.XMLParser(resolve_entities=False, no_network=True))


def _activo(e: etree._Element | None) -> bool:
    """`<w:b/>` o `<w:b w:val="1"/>` (no `0`, `false` ni `off`)."""
    return e is not None and e.get(W + "val", "1").lower() not in ("0", "false", "off", "none")


@dataclass
class _Estilo:
    nombre: str
    titulo: bool
    lista: bool
    negrita: bool


def _estilos(z: zipfile.ZipFile) -> dict[str, _Estilo]:
    raiz = _xml(z, "word/styles.xml")
    if raiz is None:
        return {}
    crudos = {}
    for s in raiz.findall(W + "style"):
        sid = s.get(W + "styleId")
        nombre = (s.find(W + "name").get(W + "val") if s.find(W + "name") is not None else sid) or ""
        base = s.find(W + "basedOn")
        ppr, rpr = s.find(W + "pPr"), s.find(W + "rPr")
        crudos[sid] = {
            "nombre": nombre,
            "base": base.get(W + "val") if base is not None else None,
            "titulo": ppr is not None and ppr.find(W + "outlineLvl") is not None
            and ppr.find(W + "outlineLvl").get(W + "val") not in ("9", None),
            "lista": ppr is not None and ppr.find(W + "numPr") is not None,
            "negrita": rpr is not None and _activo(rpr.find(W + "b")),
        }

    def resolver(sid: str, prof: int = 0) -> dict:
        c = dict(crudos.get(sid, {}))
        if c.get("base") and prof < 10:
            b = resolver(c["base"], prof + 1)
            for k in ("titulo", "lista", "negrita"):
                c[k] = c.get(k) or b.get(k, False)
        return c

    out = {}
    for sid in crudos:
        c = resolver(sid)
        n = c["nombre"].lower()
        titulo = c["titulo"] or bool(re.match(r"^(heading|t[ií]tulo|title)\b", n)) or n in ("title", "subtitle")
        out[sid] = _Estilo(c["nombre"], titulo, c["lista"] or n.startswith(("list bullet", "list number")), c["negrita"])
    return out


def _texto_run(r: etree._Element) -> str:
    out = []
    for e in r:
        if e.tag == W + "t":
            out.append(e.text or "")
        elif e.tag in (W + "tab", W + "br", W + "cr"):
            out.append(" ")
        elif e.tag == W + "noBreakHyphen":
            out.append("-")
    return "".join(out)


def _trozos_parrafo(p: etree._Element, enlaces: dict[str, str], estilos: dict[str, _Estilo],
                    negrita_parrafo: bool) -> list[Trozo]:
    out: list[Trozo] = []

    def run(r: etree._Element, url: str | None) -> None:
        t = _texto_run(r)
        if not t:
            return
        rpr = r.find(W + "rPr")
        b = negrita_parrafo
        if rpr is not None:
            if rpr.find(W + "b") is not None:
                b = _activo(rpr.find(W + "b"))
            elif rpr.find(W + "rStyle") is not None:
                e = estilos.get(rpr.find(W + "rStyle").get(W + "val"))
                b = b or bool(e and (e.negrita or e.nombre.lower() in ("strong", "negrita", "texto en negrita")))
        out.append(Trozo(t, b, url))

    def recorrer(e: etree._Element, url: str | None) -> None:
        for h in e:
            if h.tag == W + "r":
                run(h, url)
            elif h.tag == W + "hyperlink":
                destino = enlaces.get(h.get(R + "id", "")) if h.get(R + "id") else None
                recorrer(h, destino if destino and re.match(r"https?://", destino) else None)
            elif h.tag in (W + "ins", W + "smartTag", W + "fldSimple", W + "sdt", W + "sdtContent"):
                recorrer(h, url)
            # w:del (texto borrado con control de cambios), w:pPr y lo demás: fuera

    recorrer(p, None)
    return out


def importar(datos: bytes) -> Importado:
    """Los párrafos de un Word, con la cabecera y el archivo del bloque si los lleva (exportado desde la app)."""
    try:
        z = zipfile.ZipFile(io.BytesIO(datos))
        doc = _xml(z, "word/document.xml")
    except (zipfile.BadZipFile, etree.XMLSyntaxError) as e:
        raise WordNoValido(f"No es un documento de Word (.docx) válido: {e}") from e
    if doc is None:
        raise WordNoValido("No es un documento de Word (.docx): le falta el texto (word/document.xml)")
    estilos = _estilos(z)
    enlaces = {}
    rels = _xml(z, "word/_rels/document.xml.rels")
    if rels is not None:
        for r in rels:
            if r.get("TargetMode") == "External":
                enlaces[r.get("Id")] = r.get("Target")
    props = {}
    custom = _xml(z, "docProps/custom.xml")
    if custom is not None:
        for p in custom:
            v = next(iter(p), None)
            props[p.get("name")] = (v.text or "") if v is not None else ""

    res = Importado(parrafos=[], cabecera=props.get(PROP_CABECERA) or None, archivo=props.get(PROP_ARCHIVO) or None)
    cuerpo = doc.find(W + "body")
    if cuerpo is None:
        return res
    hay_tablas = False
    for p in cuerpo.iter(W + "p"):
        ancestros = [a.tag for a in p.iterancestors()]
        if any(str(a).endswith("}Fallback") for a in ancestros):   # copia de un cuadro de texto para Word antiguo
            continue
        if W + "tbl" in ancestros:
            hay_tablas = True
        ppr = p.find(W + "pPr")
        sid = ppr.find(W + "pStyle").get(W + "val") if ppr is not None and ppr.find(W + "pStyle") is not None else ""
        est = estilos.get(sid)
        nombre = est.nombre if est else sid
        if nombre == ESTILO_AVISO:
            continue
        if nombre == ESTILO_NOTA:
            clase = "nota"
        elif (est and est.titulo) or (ppr is not None and ppr.find(W + "outlineLvl") is not None):
            clase = "subtitulo"
        elif (est and est.lista) or (ppr is not None and ppr.find(W + "numPr") is not None):
            clase = "vineta"
        else:
            clase = "parrafo"
        ts = _trozos_parrafo(p, enlaces, estilos, bool(est and est.negrita and clase != "subtitulo"))
        t = de_trozos(ts, negrita=clase != "subtitulo")
        if clase == "vineta":
            t = re.sub(r"^[•·▪◦‣\-–]\s+", "", t)
        if limpio(t.replace("**", "")):
            res.parrafos.append(Parrafo(clase, t))
    if hay_tablas:
        res.avisos.append("El Word tiene tablas: su texto entra como párrafos sueltos (los bloques no llevan tablas)")
    if not res.parrafos:
        res.avisos.append("El Word no tiene texto")
    return res
