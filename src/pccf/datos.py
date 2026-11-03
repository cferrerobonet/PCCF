"""La carpeta de datos del PCCF (ARCHITECTURE.md §4): la carga, la valida con los esquemas y da el modelo en memoria.

Solo lee. Lo que falta (un archivo que aún no existe) llega como None o lista vacía y el documento lo marca
«pendiente»; lo que está mal escrito es un error con su archivo, nunca un dato a medias.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pccf import bloques, esquemas

RAIZ = Path(__file__).resolve().parents[2]


class DatosNoValidos(ValueError):
    pass


def carpeta_por_defecto() -> Path:
    """`PCCF_DATOS` o, en desarrollo, `PCCF - DATOS/` junto al repositorio. En la app, la de Ajustes."""
    if os.environ.get("PCCF_DATOS"):
        return Path(os.environ["PCCF_DATOS"])
    return RAIZ.parent / "PCCF - DATOS"


def _leer_yaml(ruta: Path, esquema: str):
    try:
        with open(ruta, encoding="utf-8") as f:
            dato = esquemas.sin_fechas(yaml.safe_load(f))
    except yaml.YAMLError as e:
        raise DatosNoValidos(f"{ruta}: YAML ilegible: {e}") from e
    errs = esquemas.errores(esquema, dato, str(ruta))
    if errs:
        raise DatosNoValidos("\n".join(errs))
    return dato


@dataclass
class Equipo:
    """Equipo docente de un ciclo en un curso: quién imparte cada módulo y quién tiene cada tutoría."""
    ciclo: str
    curso: str
    estado: str
    docentes: dict[str, str]                      # código → nombre
    tutorias: list[dict] = field(default_factory=list)
    modulos: list[dict] = field(default_factory=list)

    def nombres(self, codigos: list[str]) -> list[str]:
        return [self.docentes[c] for c in codigos]

    def del_modulo(self, codigo: str) -> dict | None:
        """La fila del módulo por su clave del catálogo («0524», «0526p», «OPT-EE-IA»), o None si no está."""
        for m in self.modulos:
            if m["modulo"] == codigo:
                return m
        return None


class CarpetaDatos:
    def __init__(self, carpeta: Path | None = None):
        self.carpeta = Path(carpeta) if carpeta else carpeta_por_defecto()
        if not self.carpeta.is_dir():
            raise FileNotFoundError(f"No existe la carpeta de datos {self.carpeta}")

    # -- centro -------------------------------------------------------------------------------------------------------
    def departamentos(self) -> list[dict]:
        p = self.carpeta / "centro" / "departamentos.yaml"
        if not p.is_file():
            return []
        d = _leer_yaml(p, "departamentos")
        vistos: dict[str, str] = {}
        for dep in d["departamentos"]:
            for sigla in dep["ciclos"]:
                if sigla in vistos:
                    raise DatosNoValidos(f"{p}: {sigla} está en {vistos[sigla]} y en {dep['id']}")
                vistos[sigla] = dep["id"]
        return sorted(d["departamentos"], key=lambda x: x["orden"])

    def departamento_de(self, sigla: str) -> dict | None:
        return next((d for d in self.departamentos() if sigla in d["ciclos"]), None)

    # -- curso --------------------------------------------------------------------------------------------------------
    def equipo(self, curso: str, sigla: str) -> Equipo | None:
        p = self.carpeta / "cursos" / curso / sigla / "equipo.yaml"
        if not p.is_file():
            return None
        d = _leer_yaml(p, "equipo")
        if d["ciclo"] != sigla or d["curso"] != curso:
            raise DatosNoValidos(f"{p}: dice {d['ciclo']} {d['curso']} y está en la carpeta de {sigla} {curso}")
        docentes = {x["codigo"]: x["nombre"] for x in d["docentes"]}
        usados = [t["docente"] for t in d.get("tutorias", [])]
        for m in d["modulos"]:
            usados += m["docentes"]
        desconocidos = sorted(set(usados) - set(docentes))
        if desconocidos:
            raise DatosNoValidos(f"{p}: docentes sin ficha en «docentes»: {', '.join(desconocidos)}")
        return Equipo(ciclo=sigla, curso=curso, estado=d["estado"], docentes=docentes,
                      tutorias=list(d.get("tutorias", [])), modulos=list(d["modulos"]))

    # -- bloques ------------------------------------------------------------------------------------------------------
    def carpetas_de_bloques(self, sigla: str, curso: str) -> list[Path]:
        """De centro, de ciclo y del curso, en ese orden."""
        return [self.carpeta / "centro", self.carpeta / "ciclos" / sigla / "bloques",
                self.carpeta / "cursos" / curso / sigla / "bloques"]

    def bloques(self, sigla: str, curso: str, apartado: int | None = None) -> list[bloques.Bloque]:
        out = []
        for c in self.carpetas_de_bloques(sigla, curso):
            for p in sorted(c.glob("*.md")) if c.is_dir() else []:
                b = bloques.leer(p)
                if apartado is None or b.apartado == apartado:
                    out.append(b)
        return out

    def comprobar(self, sigla: str, curso: str) -> list[str]:
        """Todos los errores de la carpeta para un ciclo y un curso (vacía si está bien)."""
        errs: list[str] = []
        for llamada in (self.departamentos, lambda: self.equipo(curso, sigla)):
            try:
                llamada()
            except DatosNoValidos as e:
                errs += str(e).splitlines()
        for c in self.carpetas_de_bloques(sigla, curso):
            for p in sorted(c.glob("*.md")) if c.is_dir() else []:
                try:
                    bloques.leer(p)
                except bloques.BloqueNoValido as e:
                    errs += str(e).splitlines()
        return errs
