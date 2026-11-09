"""El texto de un bloque como lista de párrafos (ADR-020): lo que el equipo ve en el editor y en Word, y lo que la
carpeta de datos guarda en Markdown.

Solo lo que el documento sabe escribir (`documento.Escritor.markdown`):

| Clase | En el editor y en Word | En la carpeta de datos |
| --- | --- | --- |
| `parrafo` | Párrafo | Párrafo separado por una línea en blanco |
| `subtitulo` | Subtítulo (Título 2 en Word) | `### Subtítulo` |
| `vineta` | Viñeta | `- Viñeta` |
| `nota` | Nota interna (sombreada): no sale en el PCCF | `> Nota` |

Dentro del párrafo, **negrita** (`**…**`) y enlaces (`[texto](https://…)`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

CLASES = ("parrafo", "subtitulo", "vineta", "nota")
RE_EN_LINEA = re.compile(r"\*\*(.+?)\*\*|\[([^\]]+)\]\((https?://[^)\s]+)\)")


@dataclass(frozen=True)
class Parrafo:
    clase: str
    texto: str          # con `**negrita**` y `[texto](url)`


@dataclass(frozen=True)
class Trozo:
    texto: str
    negrita: bool = False
    url: str | None = None


# ---------------------------------------------------------------------------------------------------------------------
# Markdown de la carpeta de datos ↔ párrafos
# ---------------------------------------------------------------------------------------------------------------------
def de_markdown(md: str) -> list[Parrafo]:
    """Los párrafos de un bloque, leídos como los lee el documento: las líneas seguidas forman un párrafo."""
    out: list[Parrafo] = []
    actual: list[str] = []
    clase_actual = "parrafo"

    def cerrar():
        nonlocal clase_actual
        if actual:
            out.append(Parrafo(clase_actual, " ".join(actual)))
            actual.clear()
        clase_actual = "parrafo"

    for linea in (md or "").replace("\r\n", "\n").splitlines():
        s = linea.strip()
        if not s:
            cerrar()
        elif s.startswith(">"):
            if clase_actual != "nota":
                cerrar()
                clase_actual = "nota"
            if s.lstrip(">").strip():
                actual.append(s.lstrip(">").strip())
        elif s.startswith("#"):
            cerrar()
            if s.lstrip("#").strip():
                out.append(Parrafo("subtitulo", s.lstrip("#").strip()))
        elif s.startswith(("- ", "* ")):
            cerrar()
            if s[2:].strip():
                out.append(Parrafo("vineta", s[2:].strip()))
        else:
            if clase_actual != "parrafo":
                cerrar()
            actual.append(s)
    cerrar()
    return out


def a_markdown(parrafos: list[Parrafo]) -> str:
    """El Markdown que se guarda: un párrafo por línea, con una línea en blanco entre ellos salvo entre viñetas."""
    lineas: list[str] = []
    anterior = None
    for p in parrafos:
        t = limpio(p.texto)
        if not t:
            continue
        if lineas and not (anterior == "vineta" and p.clase == "vineta"):
            lineas.append("")
        lineas.append({"subtitulo": "### ", "vineta": "- ", "nota": "> "}.get(p.clase, "") + t)
        anterior = p.clase
    return "\n".join(lineas)


def limpio(t: str) -> str:
    """Una sola línea, sin espacios de más (los saltos de línea dentro de un párrafo pasan a espacios)."""
    return re.sub(r"\s+", " ", (t or "").replace(" ", " ").replace(" ", " ")).strip()


# ---------------------------------------------------------------------------------------------------------------------
# Dentro del párrafo
# ---------------------------------------------------------------------------------------------------------------------
def trozos(texto: str) -> list[Trozo]:
    """`**negrita**` y `[texto](url)` como trozos con su formato."""
    out, pos = [], 0
    for m in RE_EN_LINEA.finditer(texto):
        if m.start() > pos:
            out.append(Trozo(texto[pos:m.start()]))
        out.append(Trozo(m.group(1), negrita=True) if m.group(1) else Trozo(m.group(2), url=m.group(3)))
        pos = m.end()
    if pos < len(texto):
        out.append(Trozo(texto[pos:]))
    return out


def de_trozos(ts: list[Trozo], negrita: bool = True) -> str:
    """El texto con sus marcas. Los trozos seguidos con el mismo formato se juntan; un enlace no lleva negrita.
    Con `negrita=False` (los subtítulos, que ya salen en negrita) no se marca la negrita."""
    juntos: list[Trozo] = []
    for t in ts:
        if not t.texto:
            continue
        n = negrita and t.negrita and not t.url and bool(t.texto.strip())
        if juntos and juntos[-1].url == t.url and juntos[-1].negrita == n:
            juntos[-1] = Trozo(juntos[-1].texto + t.texto, n, t.url)
        else:
            juntos.append(Trozo(t.texto, n, t.url))
    out = ""
    for t in juntos:
        m = re.match(r"^(\s*)(.*?)(\s*)$", t.texto, re.S)
        assert m is not None   # la expresión casa con cualquier texto
        antes, medio, despues = m.groups()
        if t.url and medio:
            out += f"{antes}[{medio}]({t.url}){despues}"
        elif t.negrita and medio:
            out += f"{antes}**{medio}**{despues}"
        else:
            out += t.texto
    return limpio(out)


def sin_marcas(texto: str) -> str:
    return "".join(t.texto for t in trozos(texto))
