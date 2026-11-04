"""Lo que se calcula al generar y nunca se guarda: identificación (apartado 1), marco normativo (2) y contribución de
cada módulo a las competencias profesionales (4). Sale del catálogo y de la carpeta de datos; lo que falte va como
None para que el documento lo marque «pendiente»."""
from __future__ import annotations

from dataclasses import dataclass, field

from pccf.catalogo import Catalogo, Norma, texto
from pccf.datos import CarpetaDatos

GRADOS = {"GB": "Grado Básico", "GM": "Grado Medio", "GS": "Grado Superior"}


@dataclass
class FilaModulo:
    curso: int
    clave: str          # la del catálogo y del equipo: «0524», «0526p», «OPT-EE-IA»
    codigo: str         # el que se ve: «0526», «CVOPS031»
    nombre: str
    horas: int
    h_sem: int
    tipo: str
    docentes: list[str] | None   # None: el equipo no está o no tiene el módulo (pendiente)


@dataclass
class Identificacion:
    sigla: str
    nombre: str
    titulo: str
    grado: str
    familia: str
    rd: Norma | None
    curso: str
    departamento: dict | None
    tutorias: list[tuple[str, str]] | None   # (grupo, nombre)
    modulos: list[FilaModulo] = field(default_factory=list)
    horas_total: int = 0
    equipo_confirmado: bool = True   # sin equipo, lo pendiente ya se ve en cada módulo
    equipo_origen: str = ""          # «heredado del curso AAAA-AAAA»

    @property
    def grado_largo(self) -> str:
        return GRADOS.get(self.grado, self.grado)


def filas_modulos(cat: Catalogo, sigla: str) -> list[dict]:
    """Las filas del horario del ciclo por curso, con cada optativo ofertado en lugar de su casilla."""
    out = []
    for m in cat.ciclo(sigla)["modulos"]:
        if m["tipo"] == "optativo":
            out += cat.optativos(sigla, m["curso"])
        else:
            out.append({**m, "clave": m["codigo"]})
    return sorted(out, key=lambda m: m["curso"])


def identificacion(cat: Catalogo, datos: CarpetaDatos, sigla: str, curso: str) -> Identificacion:
    c = cat.ciclo(sigla)
    equipo = datos.equipo(curso, sigla)
    rd = cat.normas.get(c["rd"]["id"]) if c.get("rd") else None
    filas = []
    for m in filas_modulos(cat, sigla):
        fila_eq = equipo.del_modulo(m["clave"]) if equipo else None
        filas.append(FilaModulo(curso=m["curso"], clave=m["clave"], codigo=m["codigo"].rstrip("p"),
                                nombre=texto(m["nombre"]), horas=m["h_anuales"], h_sem=m["h_sem"], tipo=m["tipo"],
                                docentes=equipo.nombres(fila_eq["docentes"]) if fila_eq else None))
    tutorias = ([(t["grupo"], equipo.docentes[t["docente"]]) for t in sorted(equipo.tutorias, key=lambda t: t["curso"])]
                if equipo and equipo.tutorias else None)
    return Identificacion(sigla=sigla, nombre=texto(c["nombre"]), titulo=texto(c["titulo"]), grado=c["grado"],
                          familia=texto(c["familia"]), rd=rd, curso=curso, departamento=datos.departamento_de(sigla),
                          tutorias=tutorias, modulos=filas,
                          equipo_confirmado=equipo.confirmado if equipo else True,
                          equipo_origen=equipo.origen if equipo else "",
                          # las optativas son alternativas: cuenta su casilla, no cada una
                          horas_total=sum(m["h_anuales"] for m in c["modulos"]))


def marco_normativo(cat: Catalogo, sigla: str, curso: str) -> dict[str, list[Norma]]:
    """Normas estatales y autonómicas que se aplican al ciclo en el curso, por fecha (las del catálogo; las propias
    del centro llegarán con `normativa.yaml` de la carpeta de datos)."""
    return {"estatal": cat.normativa(sigla, "estatal", curso), "autonomico": cat.normativa(sigla, "autonomico", curso)}


@dataclass
class Contribucion:
    competencias: list[tuple[str, str]]          # (letra, texto)
    filas: list[tuple[FilaModulo, list[str]]]    # módulo y sus letras; lista vacía: el RD no le asigna ninguna
    fuente: str                                  # norma de las letras (el RD del título)


def contribucion(cat: Catalogo, sigla: str) -> Contribucion:
    """Tabla módulo × competencia profesional según el RD del título («La formación del módulo contribuye a alcanzar
    las competencias…»: `competencias_modulo` del catálogo). Los ajustes del equipo (`ajustes.yaml`) llegan después."""
    c = cat.ciclo(sigla)
    comp = [(x["letra"], texto(x.get("corregido") or x["texto"])) for x in c["competencias"]]
    filas = []
    for m in filas_modulos(cat, sigla):
        try:
            letras = list(cat.modulo(m["modulo"]).get("competencias_modulo", {}).get(sigla, [])) if m.get("modulo") else []
        except KeyError:   # optativo sin RA en el catálogo
            letras = []
        filas.append((FilaModulo(curso=m["curso"], clave=m["clave"], codigo=m["codigo"].rstrip("p"),
                                 nombre=texto(m["nombre"]), horas=m["h_anuales"], h_sem=m["h_sem"], tipo=m["tipo"],
                                 docentes=None), letras))
    return Contribucion(competencias=comp, filas=filas, fuente=c.get("fuentes", {}).get("competencias", ""))
