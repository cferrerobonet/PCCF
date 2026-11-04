"""Catálogo publicado y firmado por Programaciones (ARCHITECTURE.md §1 y §6): bajarlo, verificarlo y guardarlo (sin
Qt). Copia de `catalogo_remoto.py` de Programaciones, sin la parte de publicar.

- **Publicado** en la rama `catalogo-publicado` del repositorio de Programaciones, servida por
  `raw.githubusercontent.com` (sin gastar la API de GitHub): `indice.json`, firmado con Ed25519 (`firma.py`), y un
  `catalogo-<versión>.json.gz` por versión.
- **Al compilar** (`scripts/catalogo.py bajar`), la última versión verificada va dentro de la app.
- **En la app instalada,** al arrancar y como mucho una vez al día, se baja `indice.json`; sin firma, con firma mala, con
  otra clave o con una versión que no es mayor que la que se tiene, no se acepta nada. Si es nuevo, se baja el paquete,
  se comprueba su sha256 y su contenido y se guarda en `<carpeta de la app>/catalogo/versiones/<versión>/`.
- **Sin red,** todo sigue con el catálogo más nuevo que haya en el equipo (el de la app, como mínimo).
"""

from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import io
import json
import logging
import os
import re
import shutil
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import yaml

from pccf import __version__, firma
from pccf.actualizaciones import contexto_ssl
from pccf.catalogo import Catalogo

logger = logging.getLogger(__name__)

REPO = "cferrerobonet/programaciones_fp"   # el catálogo es de Programaciones (ADR-001)
RAMA = "catalogo-publicado"
DOMINIO = "raw.githubusercontent.com"
URL_BASE = f"https://{DOMINIO}/{REPO}/{RAMA}/"
URL_INDICE = URL_BASE + "indice.json"
FORMATO_INDICE = "catalogo-indice/1"
FORMATO_PAQUETE = "catalogo-paquete/1"
#: Formatos del catálogo que entiende esta versión de la app (un cambio incompatible sube `catalogo/N`).
FORMATOS_CATALOGO = ("catalogo/4",)
TIMEOUT = 10
MAX_INDICE = 2 * 1024 * 1024
MAX_PAQUETE = 30 * 1024 * 1024
MAX_DESCOMPRIMIDO = 80 * 1024 * 1024
RE_VERSION = re.compile(r"^\d{4}\.\d{2}\.\d{2}(?:\.\d{1,3})?$")
RE_ARCHIVO_PAQUETE = re.compile(r"^catalogo-\d{4}\.\d{2}\.\d{2}(?:\.\d{1,3})?\.json\.gz$")
RE_RUTA = re.compile(r"^(?:(?:normativa|fuentes|version)\.yaml|(?:ciclos|modulos|cursos)/[A-Za-z0-9_-]+\.yaml)$")
#: Fuera del paquete: el estado del vigía no es catálogo.
FUERA = {"vigia.yaml"}
#: Fuera de la huella del contenido: `version.yaml` la contiene.
SIN_HUELLA = {"version.yaml"}


class CatalogoNoValido(Exception):
    """Lo descargado no tiene firma, la firma no vale o el contenido no es un catálogo: no se acepta."""


def _leer(p: Path):
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------------------------------------------------
# Versiones y contenido
# ---------------------------------------------------------------------------------------------------------------------
def clave_version(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return ()


def es_mayor(a: str, b: str) -> bool:
    return clave_version(a) > clave_version(b)


def archivos(carpeta: Path) -> dict[str, str]:
    """Los archivos del catálogo (ruta relativa con «/» → texto), en orden: lo que va en el paquete."""
    carpeta = Path(carpeta)
    out = {}
    for p in sorted(carpeta.rglob("*.yaml")):
        rel = p.relative_to(carpeta).as_posix()
        if rel in FUERA or not RE_RUTA.match(rel):
            continue
        out[rel] = p.read_text(encoding="utf-8")
    return out


def huella_contenido(textos: dict[str, str]) -> str:
    """sha256 de todos los archivos del catálogo salvo `version.yaml`: cambia si cambia cualquier dato."""
    h = hashlib.sha256()
    for rel in sorted(textos):
        if rel in SIN_HUELLA:
            continue
        h.update(rel.encode("utf-8") + b"\0" + textos[rel].encode("utf-8") + b"\0")
    return "sha256:" + h.hexdigest()


def empaquetar(carpeta: Path) -> bytes:
    """El paquete que se publica: JSON con todos los archivos, comprimido con gzip (sin fecha: igual cada vez)."""
    cat = Catalogo(carpeta)
    datos = {"formato": FORMATO_PAQUETE, "version": cat.version, "fecha": cat.fecha, "archivos": archivos(carpeta)}
    crudo = json.dumps(datos, ensure_ascii=False, sort_keys=True).encode("utf-8")
    salida = io.BytesIO()
    with gzip.GzipFile(fileobj=salida, mode="wb", mtime=0, compresslevel=9) as g:
        g.write(crudo)
    return salida.getvalue()


def sha256(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def leer_indice(contenido: bytes, publica: bytes | None = None) -> dict:
    """Los `datos` de `indice.json`, solo si la firma es buena y el formato es el esperado."""
    try:
        doc = json.loads(contenido.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise CatalogoNoValido(f"indice.json no es JSON ({e})") from e
    if not isinstance(doc, dict) or not isinstance(doc.get("datos"), dict):
        raise CatalogoNoValido("indice.json sin datos")
    if not doc.get("firma"):
        raise CatalogoNoValido("El catálogo publicado no está firmado")
    publica = publica or firma.clave_publica()
    if doc.get("clave") != firma.id_clave(publica):
        raise CatalogoNoValido(f"Firmado con otra clave ({doc.get('clave')})")
    if not firma.verificar(doc["datos"], doc["firma"], publica):
        raise CatalogoNoValido("La firma del catálogo publicado no es válida")
    d = doc["datos"]
    if d.get("formato") != FORMATO_INDICE:
        raise CatalogoNoValido(f"Formato de índice desconocido: {d.get('formato')}")
    if d.get("formato_catalogo") not in FORMATOS_CATALOGO:
        raise CatalogoNoValido(f"Catálogo de formato {d.get('formato_catalogo')}: hace falta una versión nueva de la app")
    if not RE_VERSION.match(str(d.get("version", ""))):
        raise CatalogoNoValido(f"Versión no válida: {d.get('version')}")
    for v, e in {d["version"]: d, **(d.get("versiones") or {})}.items():
        if not RE_VERSION.match(str(v)) or not RE_ARCHIVO_PAQUETE.match(str(e.get("archivo", ""))) \
                or not re.fullmatch(r"[0-9a-f]{64}", str(e.get("sha256", ""))):
            raise CatalogoNoValido(f"Entrada de la versión {v} no válida")
    return d


def desempaquetar(paquete: bytes, sha_esperado: str, version: str, destino: Path) -> Path:
    """Comprueba el paquete (sha256 publicado y firmado, rutas, versión, huella del contenido y que se lee como
    catálogo) y lo deja en `destino/<versión>`. Nada se escribe en su sitio hasta que todo cuadra."""
    if sha256(paquete) != sha_esperado:
        raise CatalogoNoValido("El paquete descargado no coincide con el publicado (sha256)")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(paquete)) as g:
            crudo = g.read(MAX_DESCOMPRIMIDO + 1)
        if len(crudo) > MAX_DESCOMPRIMIDO:
            raise CatalogoNoValido("Paquete demasiado grande")
        datos = json.loads(crudo.decode("utf-8"))
    except (OSError, EOFError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise CatalogoNoValido(f"Paquete dañado ({e})") from e
    if datos.get("formato") != FORMATO_PAQUETE or datos.get("version") != version:
        raise CatalogoNoValido("El paquete no es el de esta versión")
    textos = datos.get("archivos")
    if not isinstance(textos, dict) or not all(isinstance(k, str) and RE_RUTA.match(k) and isinstance(v, str)
                                               for k, v in textos.items()):
        raise CatalogoNoValido("El paquete tiene rutas o archivos no permitidos")
    destino = Path(destino)
    final = destino / version
    tmp = destino / f".tmp-{version}-{os.getpid()}"
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        for rel, texto in textos.items():
            p = tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(texto, encoding="utf-8", newline="\n")
        comprobar_carpeta(tmp, version)
        if final.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            os.replace(tmp, final)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return final


def comprobar_carpeta(carpeta: Path, version: str | None = None) -> Catalogo:
    """Que una carpeta es un catálogo completo y coherente: versión, huella del contenido, formato, ciclos y normas."""
    try:
        cat = Catalogo(carpeta)
        meta = _leer(Path(carpeta) / "version.yaml") or {}
        if version and cat.version != version:
            raise CatalogoNoValido(f"El catálogo dice ser la {cat.version}, no la {version}")
        if meta.get("formato") not in FORMATOS_CATALOGO:
            raise CatalogoNoValido(f"Formato de catálogo desconocido: {meta.get('formato')}")
        if meta.get("huella") != huella_contenido(archivos(carpeta)):
            raise CatalogoNoValido("El contenido no casa con la huella de version.yaml")
        if not cat.siglas():
            raise CatalogoNoValido("El catálogo no tiene ciclos")
        for s in cat.siglas():
            cat.ciclo(s)
        _ = cat.normas
    except CatalogoNoValido:
        raise
    except Exception as e:  # noqa: BLE001 - YAML roto, falta un archivo…: no es un catálogo
        raise CatalogoNoValido(f"No se puede leer el catálogo ({e})") from e
    return cat


# ---------------------------------------------------------------------------------------------------------------------
# En este equipo
# ---------------------------------------------------------------------------------------------------------------------
def carpeta_versiones(datos: Path) -> Path:
    return Path(datos) / "catalogo" / "versiones"


def ruta_estado(datos: Path) -> Path:
    return Path(datos) / "catalogo" / "estado.json"


def leer_estado(datos: Path) -> dict:
    try:
        return json.loads(ruta_estado(datos).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def guardar_estado(datos: Path, **cambios) -> dict:
    estado = {**leer_estado(datos), **cambios}
    p = ruta_estado(datos)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)
    return estado


def locales(datos: Path) -> dict[str, Path]:
    """Versiones guardadas en este equipo (descargadas o copia de la que llevaba la app) que se pueden leer."""
    out = {}
    base = carpeta_versiones(datos)
    for p in sorted(base.iterdir()) if base.is_dir() else []:
        if p.is_dir() and RE_VERSION.match(p.name) and (p / "normativa.yaml").is_file():
            out[p.name] = p
    return out


def guardar_copia(cat: Catalogo, datos: Path) -> None:
    """Copia el catálogo que lleva la app en la carpeta de la app, si no estaba (como Programaciones)."""
    if not RE_VERSION.match(cat.version) or not (cat.carpeta / "version.yaml").is_file():
        return
    final = carpeta_versiones(datos) / cat.version
    if final.exists():
        return
    tmp = carpeta_versiones(datos) / f".tmp-{cat.version}-{os.getpid()}"
    try:
        for rel, texto in archivos(cat.carpeta).items():
            p = tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(texto, encoding="utf-8", newline="\n")
        os.replace(tmp, final)
    except OSError as e:
        shutil.rmtree(tmp, ignore_errors=True)
        logger.warning("No se ha podido guardar una copia del catálogo %s: %s", cat.version, e)


def disponibles(datos: Path, empaquetado: Catalogo) -> dict[str, Catalogo]:
    """Todas las versiones que hay en el equipo, por versión: la de la app y las guardadas."""
    out = {}
    for v, p in locales(datos).items():
        try:
            out[v] = Catalogo(p)
        except (OSError, ValueError) as e:
            logger.warning("Catálogo %s del equipo ilegible: %s", v, e)
    out[empaquetado.version] = empaquetado
    return out


def mas_nuevo(catalogos: dict[str, Catalogo]) -> Catalogo:
    return catalogos[max(catalogos, key=clave_version)]


# ---------------------------------------------------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------------------------------------------------
def url_permitida(url: str) -> bool:
    p = urlparse(url or "")
    return p.scheme == "https" and p.hostname == DOMINIO and p.path.startswith(f"/{REPO}/{RAMA}/")


def _abrir(url: str, timeout: float = TIMEOUT):
    if not url_permitida(url):
        raise ValueError(f"URL no permitida: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": f"pccf/{__version__}",
                                               "Cache-Control": "no-cache"})
    return urllib.request.urlopen(req, timeout=timeout, context=contexto_ssl())  # nosec B310


def bajar(url: str, maximo: int, abrir=None) -> bytes:
    with (abrir or _abrir)(url) as r:
        datos = r.read(maximo + 1)
    if len(datos) > maximo:
        raise CatalogoNoValido(f"{url.rsplit('/', 1)[-1]}: demasiado grande")
    return datos


@dataclass
class Resultado:
    """`estado`: «nuevo» (hay versiones nuevas en `nuevas`), «al_dia», «hoy_ya» (ya se comprobó hoy) o «error»."""
    estado: str
    mensaje: str = ""
    version_remota: str = ""
    nuevas: list[str] = field(default_factory=list)
    novedades: str = ""


def toca(estado: dict, ahora: dt.datetime | None = None) -> bool:
    """Como mucho una vez al día (el arranque no espera a la red, y todo el centro sale por la misma IP)."""
    ultima = str(estado.get("ultima_comprobacion") or "")
    hoy = (ahora or dt.datetime.now()).date().isoformat()
    return not ultima.startswith(hoy)


def comprobar(datos: Path, actual: str, faltan=(), forzar: bool = False, abrir=None,
              ahora: dt.datetime | None = None) -> Resultado:
    """Mira el catálogo publicado y, si hay una versión mayor que `actual` (o alguna de `faltan`), la descarga y la
    guarda. Nunca lanza: devuelve el resultado."""
    ahora = ahora or dt.datetime.now()
    estado = leer_estado(datos)
    if not forzar and not toca(estado, ahora):
        return Resultado("hoy_ya", "Ya se ha comprobado hoy", str(estado.get("version_remota", "")))
    marca = ahora.isoformat(timespec="minutes")
    try:
        indice = leer_indice(bajar(URL_INDICE, MAX_INDICE, abrir))
        remota = indice["version"]
        ya = locales(datos)
        nuevas = []
        entradas = {remota: indice, **(indice.get("versiones") or {})}
        quiero = ([remota] if es_mayor(remota, actual) else []) + [v for v in faltan if v in entradas]
        for v in dict.fromkeys(quiero):
            if v in ya:
                continue
            e = entradas[v]
            paquete = bajar(URL_BASE + e["archivo"], MAX_PAQUETE, abrir)
            desempaquetar(paquete, e["sha256"], v, carpeta_versiones(datos))
            nuevas.append(v)
            logger.info("Catálogo %s descargado y verificado", v)
        if es_mayor(remota, actual) or nuevas:
            r = Resultado("nuevo" if nuevas else "al_dia", f"Catálogo {remota} verificado", remota, nuevas,
                          str(indice.get("novedades") or ""))
        else:
            r = Resultado("al_dia", f"Al día: el publicado es el {remota}", remota)
            if es_mayor(actual, remota):
                logger.info("El catálogo de este equipo (%s) es más nuevo que el publicado (%s)", actual, remota)
    except CatalogoNoValido as e:
        logger.warning("Catálogo publicado rechazado: %s", e)
        r = Resultado("error", f"No se acepta el catálogo publicado: {e}")
    except Exception as e:  # noqa: BLE001 - sin red, sin respuesta…: la app sigue con el que tiene
        logger.info("No se ha podido comprobar el catálogo publicado: %s", e)
        # Sin conexión no cuenta como comprobado: se vuelve a intentar en el próximo arranque.
        guardar_estado(datos, ultimo_intento=marca, resultado="sin_red",
                       mensaje="No se ha podido comprobar (sin conexión o sin respuesta)")
        return Resultado("error", f"No se ha podido comprobar (sin conexión o sin respuesta): {e}")
    guardar_estado(datos, ultima_comprobacion=marca, ultimo_intento=marca, resultado=r.estado, mensaje=r.mensaje,
                   **({"version_remota": r.version_remota} if r.version_remota else {}))
    return r
