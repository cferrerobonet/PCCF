"""Aviso de versión nueva publicada en GitHub (ARCHITECTURE.md §6): copia de `actualizaciones.py` de la app hermana,
con el repositorio y los nombres de los instaladores del PCCF.

En macOS, la actualización **sustituye la app allí donde está instalada** (por ejemplo en `/Applications/EPLA/`): se monta el DMG, un script aparte espera a que la app se cierre, copia la nueva con `ditto` junto
a la vieja, las cambia y abre la actualizada. Si algo falla, la vieja se queda (o vuelve) en su sitio y se avisa. En
desarrollo, o si la carpeta no se puede escribir, se abre el DMG como antes, diciendo dónde hay que arrastrarla. En
Windows, el instalador, con su `AppId` fijo, ya instala en la carpeta de la versión anterior. En Linux, se descarga
el tar.gz y se abre con el gestor de archivos: se extrae encima de la carpeta de la app.
"""

from __future__ import annotations

import hashlib
import json
import logging
import platform
import re
import ssl
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Thread
from urllib.parse import quote, urlparse

logger = logging.getLogger(__name__)

REPO = "cferrerobonet/PCCF"
RELEASES_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
#: Plan B sin API: la API sin autenticar admite 60 consultas por hora y por IP, y
#: en el centro todos los equipos salen por la misma. Esta página redirige a
#: `.../tag/vX.Y.Z`.
RELEASES_WEB = f"https://github.com/{REPO}/releases/latest"
DESCARGAS_WEB = f"https://github.com/{REPO}/releases/download"
PAGINA_DE_RELEASES = RELEASES_WEB

INSTALADOR_POR_SISTEMA = {
    "Darwin": "PCCF-{v}-macOS-arm64.dmg",
    "Windows": "PCCF-{v}-Windows-Setup.exe",
    "Linux": "PCCF-{v}-Linux-x86_64.tar.gz",
}
_EXTENSION_POR_SISTEMA = {"Darwin": ".dmg", "Windows": ".exe", "Linux": ".tar.gz"}
HOSTS_PERMITIDOS = ("api.github.com", "github.com", "objects.githubusercontent.com")
#: Segundos de espera de cada petición; en la descarga, sin recibir datos.
TIMEOUT_CONSULTA = 5
TIMEOUT_DESCARGA = 30


class DescargaNoVerificada(Exception):
    """El instalador no se pudo comprobar o no coincide con el publicado: no se abre."""


def url_de_confianza(url: str) -> bool:
    partes = urlparse(url or "")
    return partes.scheme == "https" and partes.hostname in HOSTS_PERMITIDOS


def contexto_ssl() -> ssl.SSLContext:
    """TLS con los certificados de `certifi`: el OpenSSL empaquetado no ve los del sistema."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _abrir(url: str, timeout: float = TIMEOUT_CONSULTA):
    if not url_de_confianza(url):
        raise ValueError(f"URL no permitida: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "pccf"})
    return urllib.request.urlopen(req, timeout=timeout, context=contexto_ssl())  # nosec B310


def _buscar_instalador(assets: list) -> str:
    extension = _EXTENSION_POR_SISTEMA.get(platform.system())
    if not extension:
        return ""
    for asset in assets:
        if asset.get("name", "").lower().endswith(extension):
            url = asset.get("browser_download_url", "")
            return url if url_de_confianza(url) else ""
    return ""


def ultima_version() -> tuple[str, str, str]:
    """`(versión, url del instalador, notas)`: la API y, si falla, la web."""
    try:
        with _abrir(RELEASES_URL) as r:
            data = json.loads(r.read())
        return (
            data["tag_name"].lstrip("v"),
            _buscar_instalador(data.get("assets", [])),
            (data.get("body") or "").strip(),
        )
    except Exception as e:  # noqa: BLE001 - límite de la API o red
        logger.info("La API de GitHub no respondió (%s); se pregunta a la web", e)
    with _abrir(RELEASES_WEB) as r:
        destino = r.geturl()
    if "/tag/" not in destino:
        raise ValueError(f"La web no redirigió a una versión: {destino}")
    version = destino.rsplit("/tag/", 1)[1].lstrip("v")
    plantilla = INSTALADOR_POR_SISTEMA.get(platform.system())
    url = f"{DESCARGAS_WEB}/v{version}/{plantilla.format(v=version)}" if plantilla else ""
    return version, url, ""


def digest_del_asset(url: str) -> str:
    """sha256 (hex) que publica la API de releases para el instalador de `url`; vacío si no se sabe."""
    prefijo = DESCARGAS_WEB + "/"
    if not url.startswith(prefijo):
        return ""
    etiqueta, _, nombre = url[len(prefijo) :].partition("/")
    if not etiqueta or not nombre or "/" in nombre:
        return ""
    with _abrir(f"https://api.github.com/repos/{REPO}/releases/tags/{quote(etiqueta)}") as r:
        data = json.loads(r.read())
    for asset in data.get("assets", []):
        if asset.get("name") == nombre or asset.get("browser_download_url") == url:
            digest = str(asset.get("digest") or "")
            if digest.startswith("sha256:") and re.fullmatch(r"[0-9a-f]{64}", digest[7:]):
                return digest[7:]
    return ""


def descargar_verificado(url: str, destino: Path, avance: Callable[[int], None] | None = None) -> Path:
    """Descarga el instalador y lo devuelve solo si su sha256 es el que publica GitHub.

    Sin digest publicado (o si la API no responde) no se descarga; si no coincide, se borra.
    """
    destino = Path(destino)
    if not url_de_confianza(url):
        raise ValueError(f"URL no permitida: {url}")
    try:
        esperado = digest_del_asset(url)
    except Exception as e:  # noqa: BLE001 - límite de la API o red
        raise DescargaNoVerificada(f"No se pudo comprobar la suma del instalador en GitHub ({e}).") from e
    if not esperado:
        raise DescargaNoVerificada("No se pudo comprobar la suma del instalador: GitHub no la publica.")
    suma = hashlib.sha256()
    try:
        with _abrir(url, timeout=TIMEOUT_DESCARGA) as r, open(destino, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            hecho = 0
            while trozo := r.read(64 * 1024):
                f.write(trozo)
                suma.update(trozo)
                hecho += len(trozo)
                if avance and total:
                    avance(min(100, hecho * 100 // total))
    except BaseException:
        destino.unlink(missing_ok=True)
        raise
    if suma.hexdigest() != esperado:
        destino.unlink(missing_ok=True)
        logger.warning("Instalador descartado: sha256 %s, GitHub publica %s", suma.hexdigest(), esperado)
        raise DescargaNoVerificada("El instalador descargado no coincide con el publicado en GitHub; no se abre.")
    logger.info("Instalador verificado (sha256 %s)", esperado)
    return destino


def es_mas_nueva(nueva: str, actual: str) -> bool:
    try:
        return tuple(int(x) for x in nueva.split(".")) > tuple(int(x) for x in actual.split("."))
    except ValueError:
        return False


def comprobar(actual: str, avisar: Callable[[str, str, str], None], siempre: bool = False) -> None:
    """En segundo plano. `siempre` avisa también si ya está al día (versión vacía)."""

    def _hilo():
        try:
            version, url, notas = ultima_version()
        except Exception as e:  # noqa: BLE001 - nunca debe tumbar la interfaz
            logger.warning("No se pudo comprobar si hay versión nueva: %s", e)
            if siempre:
                avisar("", "", str(e))
            return
        logger.info("Versión instalada %s, última publicada %s", actual, version)
        if es_mas_nueva(version, actual):
            avisar(version, url, notas)
        elif siempre:
            avisar("", "", "")

    Thread(target=_hilo, daemon=True).start()


# ---------------------------------------------------------------------------------------------------------------------
# macOS: sustituir la app en su sitio
# ---------------------------------------------------------------------------------------------------------------------
HDIUTIL = "/usr/bin/hdiutil"
#: Lo hace todo después de que la app se cierre. Argumentos: app nueva (en el DMG montado), app instalada, PID de la app,
#: punto de montaje y registro. Las órdenes se pueden cambiar por variables (las pruebas las simulan).
SCRIPT_SUSTITUCION = r"""#!/bin/bash
# Actualización del PCCF en macOS: sustituye la app instalada por la nueva, en su misma carpeta.
# Nunca deja dos copias ni borra la vieja si la nueva no está entera en su sitio: si algo falla, la vieja vuelve.
set -u
ORIGEN="$1"; DESTINO="$2"; PID="$3"; MONTAJE="$4"; LOG="$5"
HDIUTIL="${HDIUTIL:-/usr/bin/hdiutil}"; DITTO="${DITTO:-/usr/bin/ditto}"; ABRIR="${ABRIR:-/usr/bin/open}"
XATTR="${XATTR:-/usr/bin/xattr}"; OSASCRIPT="${OSASCRIPT:-/usr/bin/osascript}"; ESPERA="${ESPERA:-120}"
mkdir -p "$(dirname "$LOG")" && exec >>"$LOG" 2>&1
echo "$(date '+%F %T') Actualización: $ORIGEN -> $DESTINO (espera al proceso $PID)"
PADRE="$(dirname "$DESTINO")"; NOMBRE="$(basename "$DESTINO")"
NUEVA="$PADRE/.$NOMBRE.nueva-$$"; VIEJA="$PADRE/.$NOMBRE.vieja-$$"
desmontar() { "$HDIUTIL" detach "$MONTAJE" -quiet || "$HDIUTIL" detach "$MONTAJE" -force -quiet || true; }
mal() {
    echo "$(date '+%F %T') ERROR: $1"
    rm -rf "$NUEVA"
    desmontar
    "$OSASCRIPT" -e "display alert "El PCCF no se ha podido actualizar" message "$1 Sigue la versión que tenías. Registro: $LOG" as critical" >/dev/null 2>&1 || true
    [ -d "$DESTINO" ] && "$ABRIR" "$DESTINO"
    exit 1
}
k=0
while kill -0 "$PID" 2>/dev/null; do
    k=$((k + 1)); [ "$k" -gt $((ESPERA * 2)) ] && mal "La app no se ha cerrado."
    sleep 0.5
done
rm -rf "$NUEVA"
"$DITTO" "$ORIGEN" "$NUEVA" || mal "No se ha podido copiar la versión nueva."
[ -d "$NUEVA/Contents/MacOS" ] || mal "La copia de la versión nueva está incompleta."
mv "$DESTINO" "$VIEJA" || mal "No se ha podido apartar la versión instalada."
if ! mv "$NUEVA" "$DESTINO"; then
    mv "$VIEJA" "$DESTINO" || echo "ERROR: la versión anterior está en $VIEJA"
    mal "No se ha podido poner la versión nueva en su sitio."
fi
rm -rf "$VIEJA" || rm -rf "$VIEJA" || echo "AVISO: no se ha podido borrar $VIEJA"
"$XATTR" -dr com.apple.quarantine "$DESTINO" || true
desmontar
echo "$(date '+%F %T') Actualizada: $DESTINO"
"$ABRIR" "$DESTINO"
"""


def app_en_ejecucion() -> Path | None:
    """El `.app` de la app congelada en macOS (`sys.executable` es `…/X.app/Contents/MacOS/x`); None en desarrollo."""
    import sys

    if platform.system() != "Darwin" or not getattr(sys, "frozen", False):
        return None
    exe = Path(sys.executable).resolve()
    if exe.parent.name != "MacOS" or exe.parents[1].name != "Contents" or exe.parents[2].suffix != ".app":
        return None
    return exe.parents[2]


def _orden(orden: list[str]) -> str:
    import subprocess

    return subprocess.run(orden, check=True, capture_output=True, text=True, timeout=120).stdout  # nosec B603


def _lanzar(orden: list[str]) -> None:
    """El script, separado de la app: sigue vivo cuando ella se cierra."""
    import subprocess

    subprocess.Popen(orden, start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,  # nosec B603
                     stderr=subprocess.DEVNULL, close_fds=True)


def montar_dmg(dmg: Path, ejecutar=_orden) -> tuple[str, Path]:
    """(punto de montaje, app que hay dentro). Montado sin abrir Finder, solo lectura y en una carpeta al azar."""
    import plistlib
    import tempfile

    base = tempfile.mkdtemp(prefix="pccf-dmg-")
    salida = ejecutar([HDIUTIL, "attach", "-nobrowse", "-readonly", "-mountrandom", base, "-plist", str(dmg)])
    puntos = [e["mount-point"] for e in plistlib.loads(salida.encode("utf-8")).get("system-entities", [])
              if e.get("mount-point")]
    if not puntos:
        raise OSError("hdiutil no ha montado el DMG")
    apps = sorted(Path(puntos[0]).glob("*.app"))
    if not apps:
        desmontar(puntos[0], ejecutar)
        raise OSError("El DMG no tiene ninguna app dentro")
    return puntos[0], apps[0]


def desmontar(punto: str, ejecutar=_orden) -> None:
    try:
        ejecutar([HDIUTIL, "detach", punto, "-quiet"])
    except Exception as e:  # noqa: BLE001 - un DMG que se queda montado no es grave
        logger.warning("No se ha podido desmontar %s: %s", punto, e)


def se_puede_sustituir(app: Path) -> bool:
    import os

    return os.access(app.parent, os.W_OK) and os.access(app, os.W_OK)


@dataclass
class Instalacion:
    """`modo`: «sustitucion» (el script la cambia al cerrar la app) o «reserva» (se abre el DMG, como antes)."""
    modo: str
    mensaje: str = ""
    script: Path | None = None


def instalar_macos(dmg: str | Path, app: Path | None = None, pid: int | None = None, logs: Path | None = None,
                   ejecutar=_orden, lanzar=_lanzar, abrir=None) -> Instalacion:
    """Prepara la sustitución de la app en su sitio y lanza el script; si no se puede, abre el DMG (reserva).
    `app` es el `.app` instalado (por defecto, el que se está ejecutando)."""
    import os
    import tempfile

    abrir = abrir or abrir_instalador
    app = app or app_en_ejecucion()

    def reserva(motivo: str, donde: Path | None) -> Instalacion:
        logger.info("Actualización con el DMG (%s)", motivo)
        abrir(str(dmg))
        carpeta = str(donde.parent) if donde else "/Applications"
        return Instalacion("reserva", f"{motivo} Se abre el DMG: arrastra «PCCF» a la carpeta en la que la "
                                      f"tienes instalada ({carpeta}) y sustituye la que hay.")

    if app is None:
        return reserva("No es una app instalada (modo de desarrollo).", None)
    if not se_puede_sustituir(app):
        return reserva(f"No hay permiso para escribir en {app.parent}.", app)
    try:
        punto, nueva = montar_dmg(Path(dmg), ejecutar)
    except Exception as e:  # noqa: BLE001
        return reserva(f"No se ha podido montar el DMG ({e}).", app)
    if logs is None:
        from pccf.rutas import carpeta_app

        logs = carpeta_app() / "logs"
    import datetime as dt

    registro = Path(logs) / f"actualizacion_{dt.datetime.now():%Y%m%d-%H%M%S}.log"
    script = Path(tempfile.mkdtemp(prefix="pccf-actualizar-")) / "actualizar.sh"
    script.write_text(SCRIPT_SUSTITUCION, encoding="utf-8")
    script.chmod(0o700)
    try:
        lanzar(["/bin/bash", str(script), str(nueva), str(app), str(pid or os.getpid()), punto, str(registro)])
    except Exception as e:  # noqa: BLE001
        desmontar(punto, ejecutar)
        return reserva(f"No se ha podido lanzar la actualización ({e}).", app)
    logger.info("Actualización en su sitio: %s → %s (registro %s)", nueva, app, registro)
    return Instalacion("sustitucion", f"Se cierra la app, se sustituye en {app.parent} y se vuelve a abrir.", script)


def abrir_instalador(ruta: str) -> None:
    import os
    import shutil
    import subprocess

    sistema = platform.system()
    if sistema == "Windows":
        os.startfile(ruta)  # noqa: S606  # nosec B606
    elif sistema == "Darwin":
        subprocess.run(["/usr/bin/open", ruta], check=False)  # nosec B603
    else:
        # Linux: el gestor de archivos abre el tar.gz para descomprimirlo.
        xdg = shutil.which("xdg-open")
        if xdg:
            subprocess.run([xdg, ruta], check=False)  # nosec B603
