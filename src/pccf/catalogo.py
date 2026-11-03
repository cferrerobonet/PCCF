"""Lector del catálogo curricular de Programaciones (solo lectura): ciclos, módulos y normativa.

Copia del lector de Programaciones (`src/programaciones/catalogo.py`, sin la comparación de versiones), que es la
fuente única de ciclos, módulos, RA, horas, competencias y normas (ADR-001). La carpeta:
- `PCCF_CATALOGO`, si está definida;
- en la app empaquetada, la copia que lleva dentro;
- en desarrollo, el catálogo del repositorio de Programaciones, junto a este (`../../PROGRAMACIONES/…/catalogo`).
La descarga del catálogo publicado y firmado llega con el empaquetado (ARCHITECTURE.md §6).
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]


def carpeta_por_defecto() -> Path:
    if os.environ.get("PCCF_CATALOGO"):
        return Path(os.environ["PCCF_CATALOGO"])
    if getattr(sys, "frozen", False):  # app de PyInstaller: el catálogo va en sus datos
        return Path(sys._MEIPASS) / "catalogo"  # type: ignore[attr-defined]
    return RAIZ.parents[1] / "PROGRAMACIONES" / "PROGRAMACIONES - CÓDIGO FUENTE" / "catalogo"


def _leer(p: Path):
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _normal(t: str) -> str:
    """Para comparar nombres de módulo: sin tildes, en minúsculas y con los espacios normalizados."""
    import unicodedata
    t = unicodedata.normalize("NFKD", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().lower()


def texto(obj: dict | None, idioma: str = "es") -> str:
    """Texto de un objeto por idioma ({es: …}); el de «es» si no hay traducción."""
    if not obj:
        return ""
    return obj.get(idioma) or obj.get("es", "")


def texto_documento(elem: dict, idioma: str = "es") -> str:
    """El texto que va al documento: el corregido si la fuente tiene una errata, si no el literal."""
    return texto(elem.get("corregido") or elem["texto"], idioma)


RE_CITA = re.compile(r"^((?:Real Decreto|Ley Orgánica|Decreto|DECRETO|Orden|ORDEN)\s+\d+/\d{4}),\s+de\s+(\d{1,2}\s+de\s+"
                     r"[a-záéíóú]+)\b")


#: Erratas de los descriptores del perfil de salida que el documento corrige (CarlosFB, 2026-10-19). El catálogo guarda
#: el literal de la norma: su esquema no admite un campo «corregido» en las CE y añadirlo haría que las apps ya
#: instaladas rechazaran el catálogo publicado. Descriptor impreso → (corregido, motivo).
ERRATAS_DESCRIPTORES = {
    "CL3": ("CCL3", "Errata del RD 217/2022: la CE4 de Comunicación y Ciencias Sociales dice «CL3» por «CCL3» "
                    "(competencia en comunicación lingüística; no existe el descriptor «CL»)"),
}


@dataclass
class Norma:
    id: str
    titulo: str
    fecha: str
    enlace: str
    diario: str
    ambito: str
    aplica: object
    curso_escolar: str | None = None

    @property
    def cita(self) -> str:
        """«Real Decreto 1127/2010, de 10 de septiembre» (o el título entero si no tiene esa forma)."""
        m = RE_CITA.match(self.titulo)
        return f"{m.group(1)}, de {m.group(2)}" if m else self.titulo.rstrip(".")

    @property
    def cita_corta(self) -> str:
        """«Real Decreto 1127/2010»."""
        m = RE_CITA.match(self.titulo)
        return m.group(1) if m else self.cita

    @property
    def resto_titulo(self) -> str:
        """El título sin la cita ni el punto final: «, por el que se establece el título de … mínimas»."""
        t = self.titulo.rstrip(".")
        return t[len(self.cita):] if t.startswith(self.cita) else ""

    def aplica_a(self, sigla: str, grado: str) -> bool:
        """«todos», un grado («GM») o una lista de siglas y grados (["SEA"], ["GM", "GS"], ["GB"]). «citada»: a nadie;
        la norma está en el catálogo solo para enlazarla cuando otra la cita en su título (RD 1850/2009)."""
        if self.aplica == "todos":
            return True
        if self.aplica == "citada":
            return False
        if self.aplica in ("GM", "GS", "GB"):
            return self.aplica == grado
        return sigla in (self.aplica or []) or grado in (self.aplica or [])


@dataclass
class Ficha:
    """Lo que el documento necesita de un módulo en un ciclo, ya resuelto (textos en el idioma pedido)."""
    sigla: str
    grado: str
    familia: str
    ciclo_nombre: str
    titulo: str
    curso: int
    codigo: str            # el que se ve (portada, archivo): el del horario sin la «p» del Proyecto de 1.º, «0517»;
                           # en un optativo, el de la casilla de su ciclo, «CVOPS031» (ADR-043)
    codigo_horario: str    # tal cual: «0526p»
    nombre: str            # el del Decreto 95/2026 (CarlosFB, 2026-10-17)
    horas: int
    h_sem: int
    tipo: str
    modulo_id: str | None
    ra: list[dict] = field(default_factory=list)          # [{n, texto, criterios: [{letra, texto}]}]
    competencias_modulo: list[str] = field(default_factory=list)
    fuente_ra: str | None = None                          # norma de la que salen los RA
    pendientes: list[str] = field(default_factory=list)
    contenidos: list[dict] = field(default_factory=list)  # [{titulo, puntos: [texto]}]: contenidos básicos por bloques
    #: Propuesta de IA (no oficial) de las competencias de cada RA en este ciclo: {n: [letras]} (CarlosFB, 2026-10-17)
    propuesta_competencias: dict[int, list[str]] = field(default_factory=dict)
    #: Ámbitos de GB (ADR-032): `ra` lleva sus competencias específicas (criterios «1.1» en `letra`), `descriptores` sus
    #: descriptores del perfil de salida ({n: [CCL1, …]}) y `partes` las materias oficiales con sus horas (Comunicación
    #: y Ciencias Sociales); en Ciencias Aplicadas no hay oficiales: las propone `propuesta.partes` (ADR-039)
    descriptores: dict[int, list[str]] = field(default_factory=dict)
    partes: list[dict] = field(default_factory=list)
    #: La clave del módulo en su ciclo y curso: la que guarda la programación («modulo»). Es el código, salvo en los
    #: optativos ofertados, que comparten el de la casilla y se distinguen por su identificador («OPT-EE-IA», ADR-043)
    clave: str = ""

    @property
    def es_ambito(self) -> bool:
        return self.tipo == "ambito"

    @property
    def sigla_ra(self) -> str:
        """«RA» o, en un ámbito, «CE»."""
        return "CE" if self.es_ambito else "RA"

    @property
    def numeros_ra(self) -> list[int]:
        return [r["n"] for r in self.ra]


class Catalogo:
    """El catálogo de una carpeta. Carga perezosa: cada archivo se lee la primera vez que se pide."""

    def __init__(self, carpeta: Path | None = None):
        self.carpeta = Path(carpeta) if carpeta else carpeta_por_defecto()
        if not (self.carpeta / "normativa.yaml").is_file():
            raise FileNotFoundError(f"No hay catálogo en {self.carpeta}")
        self._ciclos: dict[str, dict] = {}
        self._modulos: dict[str, dict] = {}

    # -- archivos ----------------------------------------------------------------------------------------------------
    def ciclo(self, sigla: str) -> dict:
        if sigla not in self._ciclos:
            p = self.carpeta / "ciclos" / f"{sigla}.yaml"
            if not p.is_file():
                raise KeyError(f"Ciclo desconocido: {sigla}")
            self._ciclos[sigla] = _leer(p)
        return self._ciclos[sigla]

    def siglas(self) -> list[str]:
        return sorted(p.stem for p in (self.carpeta / "ciclos").glob("*.yaml"))

    def modulo(self, ident: str) -> dict:
        if ident not in self._modulos:
            p = self.carpeta / "modulos" / f"{ident}.yaml"
            if not p.is_file():
                raise KeyError(f"Módulo desconocido: {ident}")
            self._modulos[ident] = _leer(p)
        return self._modulos[ident]

    @cached_property
    def normas(self) -> dict[str, Norma]:
        d = _leer(self.carpeta / "normativa.yaml")
        return {n["id"]: Norma(id=n["id"], titulo=texto(n["titulo"]), fecha=n["fecha"], enlace=n["enlace"],
                               diario=n["diario"], ambito=n["ambito"], aplica=n["aplica"],
                               curso_escolar=n.get("curso_escolar")) for n in d["normas"]}

    def norma(self, ident: str) -> Norma:
        return self.normas[ident]

    @cached_property
    def _version(self) -> dict:
        """`version.yaml` (ADR-027): versión AAAA.MM.DD[.n], fecha y huella del contenido. Sin él (una copia de las
        pruebas o un catálogo de antes de F5), la versión es la comprobación más reciente de los ciclos y la normativa."""
        p = self.carpeta / "version.yaml"
        if p.is_file():
            return _leer(p) or {}
        fechas = [str(self.ciclo(s).get("comprobado", "")) for s in self.siglas()]
        fechas.append(str(_leer(self.carpeta / "normativa.yaml").get("comprobado", "")))
        f = max(fechas)
        return {"version": f.replace("-", "."), "fecha": f}

    @cached_property
    def version(self) -> str:
        """La versión del catálogo («2026.10.17», «2026.10.20.1»): la que guarda cada programación (`catalogo`)."""
        return str(self._version["version"])

    @cached_property
    def fecha(self) -> str:
        """AAAA-MM-DD de la versión."""
        return str(self._version.get("fecha") or self.version[:10].replace(".", "-"))

    def curso_escolar(self, curso: str) -> dict | None:
        """Fechas y periodos de un curso escolar (`cursos/AAAA-AAAA.yaml`) o None si aún no está dado de alta."""
        p = self.carpeta / "cursos" / f"{curso}.yaml"
        return _leer(p) if p.is_file() else None

    # -- consultas ---------------------------------------------------------------------------------------------------
    # -- módulos de un ciclo: códigos equivalentes y optativos (ADR-043) --------------------------------------------
    def optativos(self, sigla: str, curso: int | None = None) -> list[dict]:
        """Los optativos que oferta el centro en el ciclo, como filas del horario: los datos de la casilla «Módulo
        optativo» de su curso (horas) con el nombre, el código que se ve y el módulo de cada uno. Su clave es el
        identificador del módulo («OPT-EE-IA»): varios pueden compartir el código de la casilla."""
        ciclo = self.ciclo(sigla)
        casillas = {m["curso"]: m for m in ciclo["modulos"] if m["tipo"] == "optativo"}
        out = []
        for o in ciclo.get("optativos_ofertados", []):
            casilla = casillas.get(o["curso"])
            if casilla is None or (curso is not None and o["curso"] != curso):
                continue
            out.append({**{k: v for k, v in casilla.items() if k != "pendiente"}, "codigo": o["codigo"],
                        "modulo": o["modulo"], "nombre": o["nombre"], "clave": o["modulo"]})
        return out

    def resolver(self, sigla: str, codigo: str, curso: int | None = None, nombre: str = "") -> str | None:
        """La clave del módulo en el ciclo a partir de cualquiera de sus códigos: el del horario («1665031»), el general
        del módulo («1665»), el del Proyecto de 1.º sin la «p», el identificador de un optativo («OPT-EE-IA») o el
        código de su casilla («CVOPS031»; si lo comparten varios, decide `nombre`). None si no es del ciclo o si hay
        varios y el nombre no decide."""
        try:
            filas = self.ciclo(sigla)["modulos"]
        except KeyError:
            return None
        cod = str(codigo).strip()

        def en_curso(cands):   # estricto: con curso, solo los de ese curso
            return [m for m in cands if curso is None or m["curso"] == curso]

        opt = self.optativos(sigla)
        por_id = [o for o in opt if o["clave"] == cod]
        if por_id:
            return por_id[0]["clave"]
        exactas = [m for m in filas if m["codigo"] == cod or m["codigo"].rstrip("p") == cod]
        if en_curso(exactas) and not (en_curso(exactas)[0]["tipo"] == "optativo" and en_curso(
                [o for o in opt if o["codigo"] == cod])):
            return en_curso(exactas)[0]["codigo"].rstrip("p")
        por_casilla = en_curso([o for o in opt if o["codigo"] == cod])
        if len(por_casilla) > 1 and nombre:
            n = _normal(nombre)
            por_casilla = [o for o in por_casilla if _normal(texto(o["nombre"])) in n or n in _normal(texto(o["nombre"]))]
        if len(por_casilla) == 1:
            return por_casilla[0]["clave"]
        if por_casilla:
            return None
        if exactas:   # el Proyecto de 1.º («0526» con curso 1 es el «0526p») y llamadas sin el curso exacto
            return exactas[0]["codigo"].rstrip("p")
        generales = en_curso([m for m in filas if m.get("modulo") == cod]) or [m for m in filas if m.get("modulo") == cod]
        if len(generales) == 1:
            return generales[0]["codigo"].rstrip("p")
        return None

    def entrada(self, sigla: str, codigo: str, curso: int | None = None) -> dict:
        """La fila del módulo en el horario del ciclo. «0526» con curso 1 es el «0526p» (Proyecto de 1.º); «1665» es el
        «1665031» de SEA; «OPT-EE-IA», el optativo ofertado con ese módulo (`resolver`, ADR-043)."""
        filas = self.ciclo(sigla)["modulos"]
        clave = self.resolver(sigla, codigo, curso) or codigo
        opt = [o for o in self.optativos(sigla, curso) if o["clave"] == clave] or \
            [o for o in self.optativos(sigla) if o["clave"] == clave]
        if opt:
            return opt[0]
        candidatas = [m for m in filas if m["codigo"] == clave or m["codigo"].rstrip("p") == clave]
        if curso is not None:
            candidatas = [m for m in candidatas if m["curso"] == curso] or candidatas
        if not candidatas:
            raise KeyError(f"{codigo} no es un módulo de {sigla}")
        return candidatas[0]

    def identidad(self, sigla: str, codigo: str, curso: int | None = None) -> str:
        """Qué módulo es, más allá del ciclo: el general («0179», «1665», «OPT-EE-IA») o su código si es propio.
        Dos programaciones de ciclos distintos con la misma identidad son del mismo módulo (copiar a otro ciclo)."""
        e = self.entrada(sigla, codigo, curso)
        return e.get("clave") or e.get("modulo") or e["codigo"].rstrip("p")

    def mismo_modulo(self, a: tuple[str, int, str], b: tuple[str, int, str]) -> bool:
        """(ciclo, curso, código) de dos programaciones: ¿son del mismo módulo (con los mismos RA)?"""
        try:
            return self.identidad(a[0], a[2], a[1]) == self.identidad(b[0], b[2], b[1])
        except KeyError:
            return False

    def nombre_modulo(self, sigla: str, codigo: str) -> str:
        """Nombre del módulo en el ciclo: el del Decreto 95/2026 (portada, archivo y tabla del apartado 2)."""
        return texto(self.entrada(sigla, codigo)["nombre"])

    def ficha(self, sigla: str, codigo: str, curso: int | None = None, idioma: str = "es") -> Ficha:
        c = self.ciclo(sigla)
        e = self.entrada(sigla, codigo, curso)
        pendientes = []
        if e.get("pendiente"):
            pendientes.append(e["pendiente"])
        ra, comp, fuente, contenidos, propuesta, descriptores = [], [], None, [], {}, {}
        if e.get("modulo"):
            m = self.modulo(e["modulo"])
            propuesta = {int(n): list(v) for n, v in (m.get("propuesta_ra_competencias") or {}).get(sigla, {}).items()}
            contenidos = [{"titulo": texto(b["titulo"], idioma), "puntos": [texto(x, idioma) for x in b["puntos"]]}
                          for b in m.get("contenidos", [])]
            ra = [{"n": r["n"], "texto": texto_documento(r, idioma),
                   "criterios": [{"letra": x["letra"], "texto": texto_documento(x, idioma)} for x in r["criterios"]]}
                  for r in m["ra"]]
            if m.get("ce"):   # ámbito: las competencias específicas hacen de RA
                ra = [{"n": c["n"], "texto": texto(c["texto"], idioma),
                       "criterios": [{"letra": x["n"], "texto": texto(x["texto"], idioma)} for x in c["criterios"]]}
                      for c in m["ce"]]
                descriptores = {c["n"]: [ERRATAS_DESCRIPTORES.get(d, (d,))[0] for d in c["descriptores"]]
                                for c in m["ce"]}
            comp = list(m.get("competencias_modulo", {}).get(sigla, []))
            fuente = m["fuente"]["norma"]
        elif not e.get("pendiente"):
            pendientes.append(f"{e['codigo']}: el catálogo no tiene sus RA")
        if c.get("pendiente_competencias"):
            pendientes.append(c["pendiente_competencias"])
        return Ficha(sigla=sigla, grado=c["grado"], familia=texto(c["familia"], idioma),
                     ciclo_nombre=texto(c["nombre"], idioma), titulo=texto(c["titulo"], idioma), curso=e["curso"],
                     codigo=e["codigo"].rstrip("p"), codigo_horario=e["codigo"], nombre=texto(e["nombre"], idioma),
                     clave=e.get("clave") or e["codigo"].rstrip("p"),
                     horas=e["h_anuales"], h_sem=e["h_sem"], tipo=e["tipo"], modulo_id=e.get("modulo"), ra=ra,
                     competencias_modulo=comp, fuente_ra=fuente, pendientes=pendientes, contenidos=contenidos,
                     propuesta_competencias=propuesta, descriptores=descriptores,
                     partes=[{"nombre": texto(x["nombre"], idioma), "horas": x["h_anuales"]} for x in e.get("partes", [])])

    def normativa(self, sigla: str, ambito: str, curso_escolar: str | None = None) -> list[Norma]:
        """Normas de un ámbito que se aplican al ciclo, por fecha creciente. Las resoluciones de un curso escolar solo
        entran en el suyo."""
        grado = self.ciclo(sigla)["grado"]
        out = [n for n in self.normas.values() if n.ambito == ambito and n.aplica_a(sigla, grado)
               and (n.curso_escolar is None or n.curso_escolar == curso_escolar)]
        return sorted(out, key=lambda n: (n.fecha, n.id))

    def diferencias(self, otro: Catalogo, sigla: str, codigo: str, curso: int | None = None) -> list[str]:
        """Cambios de RA, criterios y horas de un módulo entre este catálogo (el de la programación) y `otro` (el nuevo):
        la base de la ventana «Cambios en el currículo» (ADR-015). Cada línea empieza por «RAn de …» o por «Horas»."""
        try:
            a = self.ficha(sigla, codigo, curso)
        except KeyError:
            a = None
        try:
            b = otro.ficha(sigla, codigo, curso)
        except KeyError:
            return [f"Módulo {codigo}: ya no está en {sigla}"] if a else []
        if a is None:
            return [f"Módulo {codigo}: nuevo en {sigla}"]
        out = []
        if a.horas != b.horas:
            out.append(f"Horas de {codigo}: {a.horas} h → {b.horas} h al año")
        if a.h_sem != b.h_sem:
            out.append(f"Horas de {codigo}: {a.h_sem} → {b.h_sem} h a la semana")
        ra_a, ra_b = {r["n"]: r for r in a.ra}, {r["n"]: r for r in b.ra}
        for n in sorted(set(ra_a) | set(ra_b)):
            if n not in ra_b:
                out.append(f"RA{n} de {codigo}: ya no está")
            elif n not in ra_a:
                out.append(f"RA{n} de {codigo}: nuevo")
            else:
                if ra_a[n]["texto"] != ra_b[n]["texto"]:
                    out.append(f"RA{n} de {codigo}: enunciado nuevo")
                ca = {x["letra"]: x["texto"] for x in ra_a[n]["criterios"]}
                cb = {x["letra"]: x["texto"] for x in ra_b[n]["criterios"]}
                for letra in sorted(set(ca) | set(cb)):
                    if ca.get(letra) != cb.get(letra):
                        estado = "nuevo" if letra not in ca else "ya no está" if letra not in cb else "cambia"
                        out.append(f"RA{n} de {codigo}: criterio {letra}) {estado}")
        return out
