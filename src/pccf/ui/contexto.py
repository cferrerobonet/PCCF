"""Lo que comparte la interfaz: catálogo, carpeta de datos, ciclo y curso elegidos, el estado de sus apartados y el
último informe del vigía. Cuando algo cambia (otro ciclo, un bloque confirmado), se recalcula y avisa con `cambiado`.

Los ajustes del equipo (carpeta de datos, catálogo, último ciclo y curso, formato de exportación) van en `QSettings`;
`PCCF_DATOS` y `PCCF_CATALOGO` mandan sobre ellos (pruebas y desarrollo).
"""
from __future__ import annotations

import datetime as dt
import logging
import os
from pathlib import Path

from PyQt6.QtCore import QObject, QSettings, pyqtSignal

from pccf import apartados, estado, vigia
from pccf.bloques import BloqueNoValido
from pccf.catalogo import Catalogo, texto
from pccf.catalogo import carpeta_por_defecto as catalogo_por_defecto
from pccf.datos import CarpetaDatos, DatosNoValidos
from pccf.datos import carpeta_por_defecto as datos_por_defecto

logger = logging.getLogger(__name__)


def ajustes() -> QSettings:
    return QSettings("EPLA", "PCCF")


def carpeta_datos() -> Path:
    if os.environ.get("PCCF_DATOS"):
        return Path(os.environ["PCCF_DATOS"])
    valor = ajustes().value("carpeta_datos", "", str)
    return Path(valor) if valor else datos_por_defecto()


def carpeta_catalogo() -> Path:
    if os.environ.get("PCCF_CATALOGO"):
        return Path(os.environ["PCCF_CATALOGO"])
    valor = ajustes().value("catalogo", "", str)
    return Path(valor) if valor else catalogo_por_defecto()


def curso_de_hoy(hoy: dt.date | None = None) -> str:
    """El curso escolar de una fecha: desde septiembre, el que empieza ese año."""
    hoy = hoy or dt.date.today()
    a = hoy.year if hoy.month >= 9 else hoy.year - 1
    return f"{a}-{a + 1}"


class Contexto(QObject):
    cambiado = pyqtSignal()          # ciclo, curso o datos: hay que repintar todo
    datos_cambiados = pyqtSignal()   # se ha escrito algo en la carpeta de datos

    def __init__(self, cat: Catalogo | None = None, datos: CarpetaDatos | None = None):
        super().__init__()
        self.cat = cat or Catalogo(carpeta_catalogo())
        self.datos = datos or CarpetaDatos(carpeta_datos())
        self.sigla = ""
        self.curso = ""
        self.estado: estado.Estado | None = None
        self.error = ""
        a = ajustes()
        sigla = a.value("ultimo_ciclo", "", str)
        if sigla not in self.cat.siglas():
            sigla = "SEA" if "SEA" in self.cat.siglas() else self.cat.siglas()[0]
        self.elegir(sigla, a.value("ultimo_curso", "", str) or None, avisar=False)

    # -- ciclos -------------------------------------------------------------------------------------------------------
    def ciclos(self) -> list[dict]:
        """Los ciclos del catálogo con lo que enseña el selector, por familia y grado."""
        orden = {"GB": 0, "GM": 1, "GS": 2}
        out = []
        for s in self.cat.siglas():
            c = self.cat.ciclo(s)
            out.append({"sigla": s, "grado": c["grado"], "familia": texto(c["familia"]), "nombre": texto(c["nombre"])})
        return sorted(out, key=lambda c: (c["familia"], orden.get(c["grado"], 9), c["sigla"]))

    def ciclo(self) -> dict:
        return next(c for c in self.ciclos() if c["sigla"] == self.sigla)

    @property
    def grado(self) -> str:
        return self.cat.ciclo(self.sigla)["grado"]

    @property
    def tiene_apartados(self) -> bool:
        try:
            apartados.apartados(self.grado)
            return True
        except KeyError:
            return False

    def cursos(self) -> list[str]:
        """Los cursos que se pueden elegir: los de la carpeta de datos y el de hoy."""
        return sorted(set(self.datos.cursos()) | {curso_de_hoy()}, reverse=True)

    # -- elegir y recalcular ------------------------------------------------------------------------------------------
    def elegir(self, sigla: str, curso: str | None = None, avisar: bool = True) -> None:
        self.sigla = sigla
        if not curso:
            con_datos = self.datos.cursos(sigla)
            curso = con_datos[0] if con_datos else curso_de_hoy()
        self.curso = curso
        a = ajustes()
        a.setValue("ultimo_ciclo", sigla)
        a.setValue("ultimo_curso", curso)
        self.recalcular(avisar)

    def recalcular(self, avisar: bool = True) -> None:
        self.error = ""
        self.estado = None
        if self.tiene_apartados:
            try:
                informe = vigia.revisar(self.cat, self.datos, self.sigla, self.curso)
            except Exception as e:  # noqa: BLE001 - el vigía no impide trabajar: se dice en la barra
                logger.exception("Vigía")
                informe = None
                self.error = f"El vigía no ha podido revisar: {e}"
            try:
                self.estado = estado.calcular(self.cat, self.datos, self.sigla, self.curso, informe)
            except (DatosNoValidos, BloqueNoValido) as e:   # un archivo mal escrito: se dice cuál y qué le pasa
                self.error = f"Hay que corregir la carpeta de datos:\n{e}"
        if avisar:
            self.cambiado.emit()

    def escrito(self) -> None:
        """Algo de la carpeta de datos ha cambiado desde la interfaz."""
        self.recalcular(avisar=False)
        self.datos_cambiados.emit()

    @property
    def informe(self) -> vigia.Informe | None:
        return self.estado.informe if self.estado else None

    def hoy(self) -> str:
        return dt.date.today().isoformat()
