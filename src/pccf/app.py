"""Arranque de la interfaz: `python -m pccf` sin argumentos y el ejecutable compilado (`src/main.py`). Copia del de
Programaciones: una sola instancia (dos copias abiertas podrían pisarse los bloques), registro y prueba de arranque.

Si faltan la carpeta de datos o el catálogo, se dice cuál y se eligen en Ajustes.

Prueba de arranque de la compilación (`compilar.yml`): con `PCCF_PRUEBA_DE_ARRANQUE=ventana`, la app abre la ventana
con una carpeta de datos vacía y temporal, comprueba lo que lleva dentro (`diagnostico.py`) y QtPdf, escribe una marca
por cada cosa en el registro y sale. Si algo falla, sale con código 1 y sin la marca de la ventana.
"""
from __future__ import annotations

import getpass
import logging
import os
import sys
import tempfile

from PyQt6.QtCore import QEvent, QObject, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QMessageBox

from pccf import __version__
from pccf.rutas import recursos
from pccf.sistema import configurar_registro

logger = logging.getLogger(__name__)
NOMBRE_APP = "PCCF"
SERVIDOR = f"pccf-{getpass.getuser()}"
VARIABLE_PRUEBA = "PCCF_PRUEBA_DE_ARRANQUE"
MARCA_PRUEBA = "PRUEBA DE ARRANQUE: ventana principal a la vista"


def _ya_abierta() -> bool:
    """Si hay otra abierta, le pide que se muestre y devuelve True."""
    s = QLocalSocket()
    s.connectToServer(SERVIDOR)
    if s.waitForConnected(400):
        s.write(b"mostrar")
        s.flush()
        s.waitForBytesWritten(400)
        s.disconnectFromServer()
        return True
    return False


class _Reactivar(QObject):
    """En macOS, pulsar el icono del Dock con la ventana minimizada la vuelve a mostrar."""

    def __init__(self, ventana):
        super().__init__()
        self._ventana = ventana

    def eventFilter(self, objeto, evento):  # noqa: N802
        if evento.type() == QEvent.Type.ApplicationActivate and self._ventana.isMinimized():
            self._ventana.mostrar_al_frente()
        return False


def icono_app() -> QIcon:
    ruta = recursos() / "icono.png"
    return QIcon(str(ruta)) if ruta.exists() else QIcon()


def prueba_de_arranque(ventana) -> bool:
    """Lo que la CI comprueba en la app compilada, con una marca en el registro por cada pieza."""
    from pccf.diagnostico import MARCA_DATOS, comprobar_datos
    from pccf.ui.vista_previa import MARCA_QTPDF, comprobar_qtpdf

    if not ventana.isVisible():
        logger.error("PRUEBA DE ARRANQUE: fallo: la ventana principal no está a la vista")
        return False
    try:
        for linea in comprobar_datos(ventana.ctx.cat):
            logger.info("%s: %s", MARCA_DATOS, linea)
        logger.info("%s: %s", MARCA_QTPDF, comprobar_qtpdf())
    except Exception:  # noqa: BLE001 - la prueba informa y falla, no se cuelga
        logger.exception("PRUEBA DE ARRANQUE: fallo")
        return False
    logger.info(MARCA_PRUEBA)
    return True


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    prueba = os.environ.get(VARIABLE_PRUEBA)
    ruta_log = configurar_registro()
    logger.info("Arranca %s %s (%s)", NOMBRE_APP, __version__, sys.platform)
    app = QApplication(argv)
    app.setApplicationName(NOMBRE_APP)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("EPLA")
    app.setWindowIcon(icono_app())

    if not prueba and _ya_abierta():
        logger.info("Ya había una instancia abierta; se le pide que se muestre")
        return 0
    QLocalServer.removeServer(SERVIDOR)
    servidor = QLocalServer()
    servidor.listen(SERVIDOR)

    from pccf.ui import estilo

    estilo.cargar_fuentes()
    estilo.aplicar(app)

    from pccf.datos import CarpetaDatos
    from pccf.ui.ajustes import DialogoAjustes
    from pccf.ui.contexto import Contexto
    from pccf.ui.ventana import VentanaPrincipal

    ctx = None
    vacia = tempfile.TemporaryDirectory(prefix="pccf-prueba-") if prueba else None
    while ctx is None:
        try:
            ctx = Contexto(datos=CarpetaDatos(vacia.name)) if vacia else Contexto()
        except Exception as e:  # noqa: BLE001 - se dice qué falta y se deja elegirlo
            logger.exception("No se pueden abrir los datos")
            if prueba:
                return 1
            r = QMessageBox.warning(None, NOMBRE_APP, f"No se pueden abrir los datos:\n{e}\n\n¿Eliges las carpetas en "
                                    "Ajustes?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Close)
            if r != QMessageBox.StandardButton.Yes or not DialogoAjustes().exec():
                return 1
    logger.info("Catálogo %s en %s; datos en %s", ctx.cat.version, ctx.cat.carpeta, ctx.datos.carpeta)
    ventana = VentanaPrincipal(ctx)
    app.ventana = ventana

    def conexion():
        s = servidor.nextPendingConnection()
        if s is not None:
            s.readyRead.connect(ventana.mostrar_al_frente)

    servidor.newConnection.connect(conexion)
    reactivar = _Reactivar(ventana)
    app.installEventFilter(reactivar)
    ventana.mostrar_al_frente()

    if prueba:
        QTimer.singleShot(3000, lambda: app.exit(0 if prueba_de_arranque(ventana) else 1))
    else:
        QTimer.singleShot(4000, ventana.buscar_actualizaciones)
        QTimer.singleShot(6000, ventana.comprobar_catalogo)
    codigo = app.exec()
    logger.info("Cierre (%s) · registro en %s", codigo, ruta_log)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
