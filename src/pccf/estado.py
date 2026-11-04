"""En qué estado está cada apartado del PCCF de un ciclo y un curso (la lista de la interfaz, el progreso y los avisos).

Las reglas son las del documento (`documento.py`): lo calculado del MVP (1, 2, 4 y 20) sale hecho; el resto lleva sus
bloques o sale «pendiente». Un apartado está:
- **pendiente**: no tiene contenido (ni calculado ni bloques), o le falta un dato (el equipo docente del apartado 1);
- **heredado**: algo suyo viene de «Nuevo curso» y nadie lo ha confirmado;
- **borrador**: tiene algo en borrador;
- **confirmado**: todo lo suyo está confirmado o se calcula;
- **revisar**: el vigía ha visto cambiar una norma en la que se apoya (manda sobre los demás: hay que mirarlo).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pccf import apartados, derivados, vigia
from pccf.bloques import Bloque
from pccf.catalogo import Catalogo
from pccf.datos import CarpetaDatos

CALCULADOS = (1, 2, 4, 20)
#: De peor a mejor: el estado de un apartado es el peor de lo que tiene.
ORDEN = ("revisar", "pendiente", "heredado", "borrador", "confirmado")
NOMBRES = {"revisar": "Revisar", "pendiente": "Pendiente", "heredado": "Heredado", "borrador": "En borrador",
           "confirmado": "Confirmado"}


def heredado(origen: str) -> bool:
    return origen.startswith("heredado del curso ")


def de_bloque(b: Bloque) -> str:
    if b.confirmado:
        return "confirmado"
    return "heredado" if heredado(b.origen) else "borrador"


def peor(estados: list[str]) -> str:
    return min(estados, key=ORDEN.index) if estados else "pendiente"


@dataclass
class EstadoApartado:
    apartado: apartados.Apartado
    estado: str
    motivo: str                                   # una frase: por qué está así
    bloques: list[Bloque] = field(default_factory=list)
    normas: list[str] = field(default_factory=list)   # normas cambiadas que lo afectan (citas)

    @property
    def n(self) -> int:
        return self.apartado.n


@dataclass
class Estado:
    apartados: list[EstadoApartado]
    informe: vigia.Informe | None

    @property
    def confirmados(self) -> int:
        return sum(1 for a in self.apartados if a.estado == "confirmado")

    def de(self, n: int) -> EstadoApartado:
        return next(a for a in self.apartados if a.n == n)

    def con(self, estado: str) -> list[EstadoApartado]:
        return [a for a in self.apartados if a.estado == estado]


def afectados(inf: vigia.Informe | None) -> dict[int, list[str]]:
    """Apartado → normas cambiadas (o que ya no están vigentes) en las que se apoya."""
    out: dict[int, list[str]] = {}
    for c in (inf.cambios + inf.no_vigentes) if inf else []:
        for u in c.usos:
            if u.apartado is not None and c.cita not in out.setdefault(u.apartado, []):
                out[u.apartado].append(c.cita)
    return out


def calcular(cat: Catalogo, datos: CarpetaDatos, sigla: str, curso: str,
             informe: vigia.Informe | None = None) -> Estado:
    grado = cat.ciclo(sigla)["grado"]
    ident = derivados.identificacion(cat, datos, sigla, curso)
    todos = datos.bloques(sigla, curso)
    cambiados = afectados(informe)
    out = []
    for a in apartados.apartados(grado):
        propios = sorted((b for b in todos if b.apartado == a.n),
                         key=lambda b: (b.orden if b.orden is not None else 999, b.ruta.name))
        estados = [de_bloque(b) for b in propios]
        if a.n == 1:
            if not any(m.docentes for m in ident.modulos):
                estados.append("pendiente")
                motivo = f"Falta el equipo docente de {curso}"
            elif not ident.equipo_confirmado:
                estados.append("heredado" if heredado(ident.equipo_origen) else "borrador")
                motivo = f"Equipo docente {ident.equipo_origen or 'en borrador'}: sin confirmar"
            elif ident.departamento is None or ident.tutorias is None:
                estados.append("pendiente")
                motivo = "Falta el departamento o las tutorías"
            else:
                estados.append("confirmado")
                motivo = "Se calcula del catálogo y del equipo docente"
        elif a.n in CALCULADOS:
            estados.append("confirmado")
            motivo = "Se calcula del catálogo"
        elif propios:
            motivo = f"{len(propios)} bloque{'s' if len(propios) > 1 else ''}"
        else:
            motivo = "Sin texto: sale «pendiente» con lo que pide la guía"
        e = peor(estados)
        if propios and a.n not in CALCULADOS and e != "confirmado":
            motivo += f" · {NOMBRES[e].lower()}"
        normas = cambiados.get(a.n, [])
        if normas:
            e = "revisar"
            motivo = f"El vigía ha visto cambiar: {', '.join(normas)}"
        out.append(EstadoApartado(apartado=a, estado=e, motivo=motivo, bloques=propios, normas=normas))
    return Estado(apartados=out, informe=informe)
