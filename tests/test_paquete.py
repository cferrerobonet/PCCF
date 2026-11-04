"""La versión y lo que necesita la app compilada: diagnóstico de lo empaquetado, catálogo publicado y firmado (sin red:
un servidor falso y una clave de prueba creada aquí, nunca la de verdad), actualizaciones y coherencia de nombres entre
la app, los scripts de compilación y el CHANGELOG."""
from __future__ import annotations

import base64
import datetime as dt
import io
import json
import re
import shutil
import urllib.error
from pathlib import Path

import pytest
import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

import pccf
from pccf import actualizaciones, diagnostico, firma
from pccf import catalogo_remoto as cr
from pccf.catalogo import Catalogo

from .conftest import DATOS

RAIZ = Path(__file__).resolve().parents[1]


def test_diagnostico_de_lo_empaquetado(cat):
    lineas = diagnostico.comprobar_datos(cat)
    assert lineas[0].startswith("catálogo 2030.01.01: 1 ciclos")
    assert "PCCF de PRU generado" in lineas[2] and "borrador" in lineas[2]
    assert "Ed25519" in lineas[-1]


# ---------------------------------------------------------------------------------------------------------------------
# Catálogo publicado
# ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture
def clave(monkeypatch):
    """Clave de prueba: la app la toma como la suya mientras dura la prueba."""
    k = Ed25519PrivateKey.generate()
    monkeypatch.setattr(firma, "clave_publica", lambda: k.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))
    return k


def _version(carpeta: Path, v: str) -> None:
    (carpeta / "version.yaml").write_text(yaml.safe_dump({
        "formato": "catalogo/4", "version": v, "fecha": v[:10].replace(".", "-"),
        "huella": cr.huella_contenido(cr.archivos(carpeta))}), encoding="utf-8")


def _publicar(rama: Path, origen: Path, k, v: str, firmar=True) -> dict:
    """Lo que deja la publicación de Programaciones en la rama catalogo-publicado: paquete e índice firmado."""
    _version(origen, v)
    paquete = cr.empaquetar(origen)
    archivo = f"catalogo-{v}.json.gz"
    rama.mkdir(parents=True, exist_ok=True)
    (rama / archivo).write_bytes(paquete)
    datos = {"formato": cr.FORMATO_INDICE, "formato_catalogo": "catalogo/4", "version": v, "archivo": archivo,
             "sha256": cr.sha256(paquete), "novedades": "Cambio ficticio"}
    publica = k.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    firma_b64 = base64.b64encode(k.sign(firma.canonico(datos))).decode() if firmar else ""
    (rama / "indice.json").write_text(json.dumps({"datos": datos, "firma": firma_b64,
                                                  "clave": firma.id_clave(publica)}), encoding="utf-8")
    return datos


class Servidor:
    """raw.githubusercontent.com falso: sirve la carpeta de la rama catalogo-publicado."""

    def __init__(self, carpeta: Path):
        self.carpeta = carpeta
        self.pedidas: list[str] = []

    def __call__(self, url, timeout=None):
        assert cr.url_permitida(url), url
        self.pedidas.append(url)
        p = self.carpeta / url[len(cr.URL_BASE):]
        if not p.is_file():
            raise urllib.error.HTTPError(url, 404, "no está", {}, None)
        return io.BytesIO(p.read_bytes())


@pytest.fixture
def origen(tmp_path) -> Path:
    destino = tmp_path / "origen"
    shutil.copytree(DATOS / "catalogo", destino)
    return destino


def test_baja_un_catalogo_publicado_mas_nuevo(tmp_path, origen, clave):
    _publicar(tmp_path / "rama", origen, clave, "2030.02.01")
    servidor = Servidor(tmp_path / "rama")
    app = tmp_path / "app"
    r = cr.comprobar(app, "2030.01.01", abrir=servidor, ahora=dt.datetime(2030, 2, 2, 9))
    assert r.estado == "nuevo" and r.nuevas == ["2030.02.01"] and r.novedades == "Cambio ficticio"
    nuevo = cr.mas_nuevo(cr.disponibles(app, Catalogo(DATOS / "catalogo")))
    assert nuevo.version == "2030.02.01" and nuevo.siglas() == ["PRU"]
    # el mismo día no vuelve a preguntar; al día siguiente sí, y ya está al día
    assert cr.comprobar(app, "2030.02.01", abrir=servidor, ahora=dt.datetime(2030, 2, 2, 18)).estado == "hoy_ya"
    assert cr.comprobar(app, "2030.02.01", abrir=servidor, ahora=dt.datetime(2030, 2, 3, 9)).estado == "al_dia"


def test_sin_firma_o_con_otra_clave_no_se_acepta(tmp_path, origen, clave):
    _publicar(tmp_path / "rama", origen, clave, "2030.02.01", firmar=False)
    r = cr.comprobar(tmp_path / "app", "2030.01.01", abrir=Servidor(tmp_path / "rama"))
    assert r.estado == "error" and "no está firmado" in r.mensaje
    otra = Ed25519PrivateKey.generate()
    _publicar(tmp_path / "rama2", origen, otra, "2030.02.01")
    r = cr.comprobar(tmp_path / "app", "2030.01.01", abrir=Servidor(tmp_path / "rama2"), forzar=True)
    assert r.estado == "error" and "otra clave" in r.mensaje
    assert cr.locales(tmp_path / "app") == {}


def test_un_paquete_cambiado_no_se_acepta(tmp_path, origen, clave):
    d = _publicar(tmp_path / "rama", origen, clave, "2030.02.01")
    p = tmp_path / "rama" / d["archivo"]
    p.write_bytes(p.read_bytes() + b"x")
    r = cr.comprobar(tmp_path / "app", "2030.01.01", abrir=Servidor(tmp_path / "rama"))
    assert r.estado == "error" and "sha256" in r.mensaje
    assert cr.locales(tmp_path / "app") == {}


def test_bajar_para_compilar(tmp_path, origen, clave, monkeypatch):
    import catalogo as receta

    _publicar(tmp_path / "rama", origen, clave, "2030.02.01")
    monkeypatch.setattr(cr, "_abrir", Servidor(tmp_path / "rama"))
    destino = tmp_path / "catalogo"
    assert receta.bajar(destino) == "2030.02.01"
    assert Catalogo(destino).version == "2030.02.01" and (destino / "ciclos" / "PRU.yaml").is_file()


# ---------------------------------------------------------------------------------------------------------------------
# Actualizaciones y nombres de la compilación
# ---------------------------------------------------------------------------------------------------------------------
def test_actualizaciones():
    assert actualizaciones.REPO == "cferrerobonet/PCCF"
    assert actualizaciones.es_mas_nueva("0.2.0", "0.1.0") and not actualizaciones.es_mas_nueva("0.1.0", "0.1.0")
    assert not actualizaciones.es_mas_nueva("raro", "0.1.0")
    assert actualizaciones.url_de_confianza("https://github.com/cferrerobonet/PCCF/releases/latest")
    assert not actualizaciones.url_de_confianza("http://github.com/x")
    assert not actualizaciones.url_de_confianza("https://otro.example.com/x")


def test_nombres_de_los_instaladores_iguales_en_la_app_y_en_la_compilacion():
    v = pccf.__version__
    dmg = (RAIZ / "scripts" / "build" / "build_dmg.sh").read_text(encoding="utf-8")
    linux = (RAIZ / "scripts" / "build" / "build_linux.sh").read_text(encoding="utf-8")
    iss = (RAIZ / "installer_windows.iss").read_text(encoding="utf-8")
    nombres = {k: x.format(v=v) for k, x in actualizaciones.INSTALADOR_POR_SISTEMA.items()}
    assert 'DMG_NAME="PCCF-${VERSION}-macOS-arm64.dmg"' in dmg and nombres["Darwin"] == f"PCCF-{v}-macOS-arm64.dmg"
    assert 'SALIDA="PCCF-${VERSION}-Linux-${ARCH}.tar.gz"' in linux
    assert nombres["Linux"] == f"PCCF-{v}-Linux-x86_64.tar.gz"
    assert "OutputBaseFilename=PCCF-{#MyAppVersion}-Windows-Setup" in iss
    assert nombres["Windows"] == f"PCCF-{v}-Windows-Setup.exe"


def test_lo_que_usa_la_compilacion_existe_y_el_changelog_tiene_la_version():
    for p in ("imagenes/icono.png", "imagenes/icono.ico", "imagenes/icono.svg", "src/pccf/recursos/icono.png",
              "src/pccf/recursos/clave_catalogo.txt", "src/main.py", "PCCF.spec"):
        assert (RAIZ / p).is_file(), p
    assert firma.id_clave(firma.clave_publica()) == "B9CFC5AE", "la clave pública del catálogo de Programaciones"
    changelog = (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(rf"^## \[{re.escape(pccf.__version__)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", changelog, re.M), \
        "las novedades de la versión (notas de la release) salen de su entrada en CHANGELOG.md"
    assert (RAIZ / "scripts" / "build_windows.ps1").read_bytes().startswith(b"\xef\xbb\xbf"), "UTF-8 con BOM"
