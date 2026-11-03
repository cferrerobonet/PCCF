"""Bloques de texto del PCCF: Markdown con cabecera YAML (tipo, apartado, origen, estado, autoría, fecha y citas)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pccf import esquemas

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
