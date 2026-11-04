"""«Nuevo curso» y «Comparar» (PRD.md RF-4 y RF-5; ARCHITECTURE.md §4).

**Nuevo curso** copia `cursos/<origen>/<SIGLA>/` en `cursos/<destino>/<SIGLA>/` de la carpeta de datos:
- lo de centro y de ciclo no se copia: es común a todos los cursos;
- lo anual (el equipo docente y los bloques del curso) pasa como **heredado**: `estado: borrador` y
  `origen: heredado del curso <origen>`, hasta que el equipo lo revisa y lo confirma;
- lo que el vigía dio por revisado se copia: así su primer informe del curso nuevo dice qué ha cambiado;
- lo calculado no se guarda: se rehace con el catálogo al generar.
Nunca sobrescribe: si el ciclo ya tiene carpeta en el curso nuevo, se para sin tocar nada.

**Comparar** dos PCCF del mismo ciclo, apartado por apartado (líneas añadidas y quitadas). Cada lado es un curso
(«2026-2027»: la carpeta de datos tal como está) o un curso en una versión aprobada («2026-2027@SEA-2026-2027-v1»:
la carpeta de datos en esa etiqueta de git). Lo calculado se compara con el catálogo de hoy en los dos lados: el
catálogo no se guarda con los datos.
"""
from __future__ import annotations

import difflib
import io
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pccf import apartados, derivados, vigia
from pccf.bloques import poner as poner_clave
from pccf.catalogo import Catalogo
from pccf.datos import CarpetaDatos, DatosNoValidos

RE_CURSO = re.compile(r"^(\d{4})-(\d{4})$")
RE_CABECERA = re.compile(r"\A(---\n)(.*?\n)(---\n?)", re.S)


class CursoNoValido(ValueError):
    pass


def _anyos(curso: str) -> tuple[int, int]:
    m = RE_CURSO.match(curso or "")
    if not m or int(m.group(2)) != int(m.group(1)) + 1:
        raise CursoNoValido(f"«{curso}» no es un curso escolar (AAAA-AAAA, años seguidos)")
    return int(m.group(1)), int(m.group(2))


def siguiente(curso: str) -> str:
    a, b = _anyos(curso)
    return f"{a + 1}-{b + 1}"


# ---------------------------------------------------------------------------------------------------------------------
# Nuevo curso
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class NuevoCurso:
    carpeta: Path
    heredados: list[str] = field(default_factory=list)   # rutas dentro de la carpeta de datos
    copiados: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def heredar_equipo(texto: str, origen: str, destino: str) -> str:
    texto = poner_clave(texto, "curso", destino, "ciclo")
    texto = poner_clave(texto, "estado", "borrador", "fecha")
    texto = poner_clave(texto, "origen", f"heredado del curso {origen}", "estado")
    return f"# Heredado de {origen} con «Nuevo curso»: revisar y, al confirmarlo, «estado: confirmado».\n" + texto


def heredar_bloque(texto: str, origen: str) -> str:
    m = RE_CABECERA.match(texto)
    if not m:
        raise DatosNoValidos("bloque sin cabecera YAML entre «---»")
    cab = poner_clave(m.group(2), "origen", f"heredado del curso {origen}", "apartado")
    cab = poner_clave(cab, "estado", "borrador", "origen")
    return m.group(1) + cab + m.group(3) + texto[m.end():]


def nuevo_curso(cat: Catalogo, datos: CarpetaDatos, sigla: str, origen: str, destino: str | None = None) -> NuevoCurso:
    """Crea el curso `destino` (por defecto, el siguiente) del ciclo a partir de `origen`."""
    destino = destino or siguiente(origen)
    if _anyos(destino) <= _anyos(origen):
        raise CursoNoValido(f"El curso nuevo ({destino}) tiene que ir después de {origen}")
    src = datos.carpeta / "cursos" / origen / sigla
    dst = datos.carpeta / "cursos" / destino / sigla
    if not src.is_dir():
        raise FileNotFoundError(f"No hay datos de {sigla} en {origen}: {src}")
    if dst.exists():
        raise FileExistsError(f"{sigla} ya tiene carpeta en {destino}: {dst}. No se sobrescribe nada.")
    errores = datos.comprobar(sigla, origen)
    if errores:
        raise DatosNoValidos("El curso de partida tiene errores:\n" + "\n".join(errores))

    res = NuevoCurso(carpeta=dst)
    tmp = dst.parent / f".{sigla}.nuevo-curso"
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        for p in sorted(src.rglob("*")):
            rel = p.relative_to(src)
            if not p.is_file() or any(x.startswith(".") for x in rel.parts):
                continue
            q = tmp / rel
            q.parent.mkdir(parents=True, exist_ok=True)
            texto_rel = (dst / rel).relative_to(datos.carpeta).as_posix()
            if rel == Path("equipo.yaml"):
                q.write_text(heredar_equipo(p.read_text(encoding="utf-8"), origen, destino), encoding="utf-8")
                res.heredados.append(texto_rel)
            elif rel.parts[0] == "bloques" and p.suffix == ".md":
                q.write_text(heredar_bloque(p.read_text(encoding="utf-8").replace("\r\n", "\n"), origen),
                             encoding="utf-8")
                res.heredados.append(texto_rel)
            elif rel == Path("vigia.yaml"):
                vigia.escribir_estado(q, sigla, destino, yaml.safe_load(p.read_text(encoding="utf-8")) or {})
            else:
                shutil.copy2(p, q)
                res.copiados.append(texto_rel)
        tmp.mkdir(parents=True, exist_ok=True)
        tmp.rename(dst)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    errores = datos.comprobar(sigla, destino)
    if errores:
        shutil.rmtree(dst)
        raise DatosNoValidos("El curso nuevo no ha quedado bien y se ha deshecho:\n" + "\n".join(errores))
    if res.copiados:
        res.avisos.append(f"Copiado sin cambios (revísalo): {', '.join(res.copiados)}")
    if not any(n.curso_escolar == destino for n in cat.normas.values()):
        res.avisos.append(f"El catálogo aún no tiene la resolución de instrucciones de {destino}: el apartado 2 sale "
                          "sin ella hasta que entre.")
    return res


# ---------------------------------------------------------------------------------------------------------------------
# Comparar
# ---------------------------------------------------------------------------------------------------------------------
def lado(texto: str) -> tuple[str, str | None]:
    """«2026-2027» → (curso, None); «2026-2027@SEA-2026-2027-v1» → (curso, etiqueta)."""
    curso, _, etiqueta = texto.partition("@")
    _anyos(curso)
    return curso, etiqueta or None


def nombre_lado(curso: str, etiqueta: str | None) -> str:
    return f"{curso} ({etiqueta})" if etiqueta else curso


@contextmanager
def carpeta_en(datos: CarpetaDatos, etiqueta: str | None) -> Iterator[CarpetaDatos]:
    """La carpeta de datos tal como está o, con etiqueta, tal como quedó en esa versión aprobada (git, sin red)."""
    if not etiqueta:
        yield datos
        return
    r = subprocess.run(["git", "-C", str(datos.carpeta), "archive", "--format=tar", f"{etiqueta}^{{commit}}"],
                       capture_output=True)
    if r.returncode:
        raise CursoNoValido(f"La carpeta de datos no tiene la versión «{etiqueta}»: "
                            f"{r.stderr.decode('utf-8', 'ignore').strip()}")
    tmp = Path(tempfile.mkdtemp(prefix="pccf-version-"))
    try:
        with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tar:
            tar.extractall(tmp, filter="data")
        yield CarpetaDatos(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _parrafos(texto: str) -> list[str]:
    return [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]


def contenido(cat: Catalogo, datos: CarpetaDatos, sigla: str, curso: str) -> dict[int, list[str]]:
    """Lo que dice cada apartado del PCCF, en líneas comparables (lo calculado y los bloques)."""
    ident = derivados.identificacion(cat, datos, sigla, curso)
    out: dict[int, list[str]] = {}

    def poner(n: int, lineas: list[str]) -> None:
        out.setdefault(n, []).extend(lineas)

    dep = ident.departamento
    poner(1, [f"Departamento: {dep['nombre']} · jefatura: {dep['jefatura']}" if dep else "Departamento: pendiente"])
    poner(1, [f"Tutoría {g}: {n}" for g, n in ident.tutorias] if ident.tutorias else ["Tutorías: pendientes"])
    if not ident.equipo_confirmado:
        poner(1, [f"Equipo docente sin confirmar{f' ({ident.equipo_origen})' if ident.equipo_origen else ''}"])
    poner(1, [f"{m.codigo} {m.nombre}: {' / '.join(m.docentes) if m.docentes else 'profesorado pendiente'}"
              for m in ident.modulos])
    marco = derivados.marco_normativo(cat, sigla, curso)
    poner(2, [n.cita for n in marco["estatal"] + marco["autonomico"]])
    k = derivados.contribucion(cat, sigla)
    poner(3, [f"{letra}) {texto}" for letra, texto in k.competencias])
    vistos = set()
    for fila, letras in k.filas:
        if (fila.codigo, fila.nombre) not in vistos:
            vistos.add((fila.codigo, fila.nombre))
            poner(4, [f"{fila.codigo} {fila.nombre}: {', '.join(letras) or 'sin orientación'}"])
    poner(7, [f"{m.codigo} {m.nombre}: {m.horas} h · {m.h_sem} h/sem." for m in ident.modulos])
    for b in sorted(datos.bloques(sigla, curso), key=lambda b: (b.orden if b.orden is not None else 999, b.ruta.name)):
        poner(b.apartado, [f"Bloque {b.ruta.name} ({b.tipo}, {b.estado}"
                           f"{', ' + b.origen if b.origen.startswith('heredado') else ''})", *_parrafos(b.cuerpo)])
    return out


@dataclass
class DifApartado:
    n: int
    titulo: str
    anadidas: list[str] = field(default_factory=list)
    quitadas: list[str] = field(default_factory=list)

    @property
    def cambia(self) -> bool:
        return bool(self.anadidas or self.quitadas)


@dataclass
class Comparacion:
    sigla: str
    a: str
    b: str
    apartados: list[DifApartado]
    avisos: list[str] = field(default_factory=list)


def diferencia(antes: list[str], despues: list[str]) -> tuple[list[str], list[str]]:
    """(añadidas, quitadas) entre dos listas de líneas, en el orden en que aparecen."""
    anadidas, quitadas = [], []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, antes, despues, autojunk=False).get_opcodes():
        if op in ("replace", "delete"):
            quitadas += antes[i1:i2]
        if op in ("replace", "insert"):
            anadidas += despues[j1:j2]
    return anadidas, quitadas


def comparar(cat: Catalogo, datos: CarpetaDatos, sigla: str, a: str, b: str) -> Comparacion:
    """Compara dos lados («curso» o «curso@etiqueta») del PCCF de un ciclo."""
    (ca, ea), (cb, eb) = lado(a), lado(b)
    avisos = []
    lados = []
    for curso, etiqueta in ((ca, ea), (cb, eb)):
        with carpeta_en(datos, etiqueta) as d:
            if not (d.carpeta / "cursos" / curso / sigla).is_dir():
                avisos.append(f"{sigla} no tiene datos en {nombre_lado(curso, etiqueta)}: lo del curso sale pendiente")
            lados.append(contenido(cat, d, sigla, curso))
    difs = []
    for ap in apartados.apartados(cat.ciclo(sigla)["grado"]):
        anadidas, quitadas = diferencia(lados[0].get(ap.n, []), lados[1].get(ap.n, []))
        difs.append(DifApartado(n=ap.n, titulo=ap.titulo, anadidas=anadidas, quitadas=quitadas))
    return Comparacion(sigla=sigla, a=nombre_lado(ca, ea), b=nombre_lado(cb, eb), apartados=difs, avisos=avisos)


def markdown(c: Comparacion) -> str:
    md = [f"# Comparar PCCF {c.sigla} · {c.a} → {c.b}", "",
          "Lo calculado (apartados 1 a 4 y 7) se rehace con el catálogo de hoy en los dos lados; los bloques y el "
          "equipo docente, tal como están en cada uno.", "",
          ]
    cambian = [d for d in c.apartados if d.cambia]
    if cambian:
        md += ["| Apartado | Añadido | Quitado |", "| --- | --- | --- |"]
        md += [f"| {d.n} · {d.titulo} | {f'+{len(d.anadidas)}' if d.anadidas else ''} | "
               f"{f'−{len(d.quitadas)}' if d.quitadas else ''} |" for d in cambian]
        md.append("")
    iguales = [str(d.n) for d in c.apartados if not d.cambia]
    md += [f"Sin cambios: {'ninguno' if not iguales else 'todos' if not cambian else ', '.join(iguales)}.", ""]
    for d in c.apartados:
        if d.cambia:
            md += [f"## {d.n} · {d.titulo}", "", "```diff", *[f"- {x}" for x in d.quitadas],
                   *[f"+ {x}" for x in d.anadidas], "```", ""]
    if c.avisos:
        md += ["## Avisos", "", *[f"- {x}" for x in c.avisos], ""]
    return "\n".join(md)


def nombre_archivo(sigla: str, a: str, b: str) -> str:
    return f"Comparar PCCF {sigla} {a.replace('@', ' ')} - {b.replace('@', ' ')}.md"
