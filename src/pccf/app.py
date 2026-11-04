"""Arranque de la interfaz: `python -m pccf` sin argumentos (y, con el empaquetado, el ejecutable).

Una sola ventana; si falta la carpeta de datos o el catálogo, se dice cuál y se abren los ajustes para elegirla.
"""
from __future__ import annotations

import logging
import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from pccf import __version__

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = QApplication(list(sys.argv if argv is None else argv))
    app.setApplicationName("PCCF")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("EPLA")

    from pccf.ui import estilo

    estilo.cargar_fuentes()
    estilo.aplicar(app)

    from pccf.ui.contexto import Contexto
    from pccf.ui.dialogos import DialogoAjustes
    from pccf.ui.ventana import VentanaPrincipal

    ctx = None
    while ctx is None:
        try:
            ctx = Contexto()
        except Exception as e:  # noqa: BLE001 - se dice qué falta y se deja elegirlo
            logger.exception("No se pueden abrir los datos")
            r = QMessageBox.warning(None, "PCCF", f"No se pueden abrir los datos:\n{e}\n\n¿Eliges las carpetas en "
                                    "Ajustes?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Close)
            if r != QMessageBox.StandardButton.Yes or not DialogoAjustes().exec():
                return 1
    ventana = VentanaPrincipal(ctx)
    app.ventana = ventana
    ventana.mostrar_al_frente()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
