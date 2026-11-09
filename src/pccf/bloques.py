"""Bloques de texto del PCCF: Markdown con cabecera YAML (tipo, apartado, origen, estado, autoría, fecha y citas)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pccf import esquemas, texto, word

RE_CABECERA = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.S)


class BloqueNoValido(ValueError):
    pass


@dataclass
class Bloque:
    ruta: Path
    tipo: str
    apartado: int
    origen: str
    estado: str
    aportado_por: str
    fecha: str
    cuerpo: str
    citas: list[dict] = field(default_factory=list)
    orden: int | None = None

    @property
    def confirmado(self) -> bool:
        return self.estado == "confirmado"


def leer(ruta: Path) -> Bloque:
    """Lee y valida un bloque. Un archivo sin cabecera o con la cabecera mal da BloqueNoValido con todos los errores."""
    texto = Path(ruta).read_text(encoding="utf-8").replace("\r\n", "\n")
    m = RE_CABECERA.match(texto)
    if not m:
        raise BloqueNoValido(f"{ruta}: falta la cabecera YAML entre «---»")
    try:
        cab = esquemas.sin_fechas(yaml.safe_load(m.group(1)) or {})
    except yaml.YAMLError as e:
        raise BloqueNoValido(f"{ruta}: cabecera YAML ilegible: {e}") from e
    errs = esquemas.errores("bloque", cab, str(ruta))
    if errs:
        raise BloqueNoValido("\n".join(errs))
    return Bloque(ruta=Path(ruta), tipo=cab["tipo"], apartado=cab["apartado"], origen=cab["origen"],
                  estado=cab["estado"], aportado_por=cab["aportado_por"], fecha=cab["fecha"],
                  cuerpo=m.group(2).strip(), citas=list(cab.get("citas", [])), orden=cab.get("orden"))


# ---------------------------------------------------------------------------------------------------------------------
# Escribir (la interfaz): se cambia la cabecera línea a línea, sin tocar comentarios, orden ni el resto de campos
# ---------------------------------------------------------------------------------------------------------------------
RE_PARTES = re.compile(r"\A(---\n)(.*?\n)(---\n?)(.*)\Z", re.S)


def poner(texto: str, clave: str, valor: str, despues_de: str) -> str:
    """Cambia `clave: …` en un YAML (o lo añade tras `despues_de`) sin tocar comentarios ni el resto."""
    rx = re.compile(rf"^{clave}:.*$", re.M)
    if rx.search(texto):
        return rx.sub(lambda _: f"{clave}: {valor}", texto, count=1)
    return re.sub(rf"^({despues_de}:.*)$", lambda m: f"{m.group(1)}\n{clave}: {valor}", texto, count=1, flags=re.M)


def _partes(ruta: Path) -> tuple[str, str, str, str]:
    texto = Path(ruta).read_text(encoding="utf-8").replace("\r\n", "\n")
    m = RE_PARTES.match(texto)
    if not m:
        raise BloqueNoValido(f"{ruta}: falta la cabecera YAML entre «---»")
    return m.group(1), m.group(2), m.group(3), m.group(4)


def _fechar(cab: str, hoy: str) -> str:
    cab = poner(cab, "fecha", hoy, "aportado_por")
    if re.search(r"^fecha_actualizacion:", cab, re.M):   # el campo de las notas de Documentos, si lo lleva
        cab = poner(cab, "fecha_actualizacion", hoy, "fecha")
    return cab


def _escribir(ruta: Path, texto: str) -> Bloque:
    """Escribe en un temporal, lo valida y solo entonces sustituye el archivo: nunca queda un bloque a medias."""
    tmp = ruta.with_name(f".{ruta.name}.tmp")
    tmp.write_text(texto, encoding="utf-8")
    try:
        leer(tmp)
    except BloqueNoValido:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(ruta)
    return leer(ruta)


def guardar(b: Bloque, cuerpo: str, hoy: str) -> Bloque:
    """Cambia el texto de un bloque. Un texto cambiado vuelve a borrador: hay que confirmarlo otra vez."""
    ab, cab, cierre, actual = _partes(b.ruta)
    if actual.strip() == cuerpo.strip():
        return b
    cab = _fechar(poner(cab, "estado", "borrador", "origen"), hoy)
    return _escribir(b.ruta, ab + cab + cierre + "\n" + cuerpo.strip() + "\n")


def confirmar(b: Bloque, hoy: str) -> Bloque:
    """El equipo da el bloque por bueno (también uno heredado: su origen se queda como historia)."""
    ab, cab, cierre, cuerpo = _partes(b.ruta)
    cab = _fechar(poner(cab, "estado", "confirmado", "origen"), hoy)
    return _escribir(b.ruta, ab + cab + cierre + cuerpo)


# ---------------------------------------------------------------------------------------------------------------------
# Word (ADR-020): el equipo escribe y revisa en Word; la carpeta de datos sigue en Markdown
# ---------------------------------------------------------------------------------------------------------------------
def cabecera(b: Bloque) -> str:
    """La cabecera YAML del bloque tal como está escrita (con sus comentarios)."""
    return _partes(b.ruta)[1]


def a_word(b: Bloque, titulo: str) -> bytes:
    """El `.docx` del bloque, con su cabecera y el nombre de su archivo dentro para devolverlo a su sitio."""
    _ab, cab, _cierre, cuerpo = _partes(b.ruta)
    aviso = (f"{titulo}. Escribe o corrige el texto debajo de esta línea, con los estilos de Word: Título 2 para los "
             "subtítulos, viñetas, negrita y enlaces. Los párrafos sombreados son notas internas: no salen en el PCCF. "
             "Guarda el archivo como Word y devuélvelo para importarlo en la app.")
    return word.exportar(texto.de_markdown(cuerpo), titulo, aviso, cabecera=cab, archivo=b.ruta.name)


def escribir_de_word(destino: Path, cabecera: str, parrafos: list[texto.Parrafo], hoy: str) -> Bloque:
    """Un bloque que vuelve de Word: su cabecera, con el texto nuevo, en borrador y con la fecha de hoy (hay que
    confirmarlo otra vez)."""
    cab = cabecera.replace("\r\n", "\n").strip("\n") + "\n"
    cab = _fechar(poner(cab, "estado", "borrador", "origen"), hoy)
    destino.parent.mkdir(parents=True, exist_ok=True)
    return _escribir(destino, "---\n" + cab + "---\n\n" + texto.a_markdown(parrafos) + "\n")
