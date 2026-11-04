"""Ventana «Vista previa» (900 × 700, copia de la de Programaciones): el mismo documento convertido a PDF, en
borrador, en un `QPdfView` (DESIGN.md: «La vista previa es el mismo documento»).

`comprobar_qtpdf` demuestra que el paquete de PyQt6 trae QtPdf y que funciona (crea un PDF de una página con
`QPdfWriter` y lo abre): lo llaman las pruebas y, con el empaquetado, la prueba de arranque de la app compilada.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtGui import QFont, QPageSize, QPainter, QPdfWriter
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QStackedLayout, QVBoxLayout, QWidget

from . import estilo
from .componentes import EstadoVacio, boton

MARCA_QTPDF = "PRUEBA DE ARRANQUE: QtPdf"


def comprobar_qtpdf() -> str:
    """Escribe un PDF de una página y lo abre con QtPdf. Devuelve una línea para el registro o lanza RuntimeError."""
    # En Windows, Qt tiene el archivo abierto mientras viven el escritor y el documento: se liberan antes de borrar la
    # carpeta, y un resto que no se pueda borrar no hace fallar la comprobación (está en la carpeta temporal).
    with tempfile.TemporaryDirectory(prefix="pccf-qtpdf-", ignore_cleanup_errors=True) as carpeta:
        ruta = Path(carpeta) / "prueba.pdf"
        escritor = QPdfWriter(str(ruta))
        escritor.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        p = QPainter(escritor)
        p.drawText(100, 100, "PCCF")
        p.end()
        del p, escritor
        documento = QPdfDocument(None)
        error = documento.load(str(ruta))
        paginas = documento.pageCount()
        documento.close()
        del documento
    if error != QPdfDocument.Error.None_ or paginas != 1:
        raise RuntimeError(f"QtPdf no abre un PDF de prueba (error {error}, {paginas} páginas)")
    return "QPdfDocument abre un PDF de 1 página y QPdfView está disponible"


class DialogoVistaPrevia(QDialog):
    def __init__(self, padre=None):
        super().__init__(padre)
        self.setWindowTitle("Vista previa")
        self.resize(900, 700)
        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.setSpacing(0)
        cabecera = QHBoxLayout()
        cabecera.setContentsMargins(22, 14, 22, 10)
        titulo = QLabel("Vista previa")
        titulo.setFont(estilo.fuente(22, QFont.Weight.Bold, estilo.TITULAR))
        cabecera.addWidget(titulo)
        cabecera.addSpacing(12)
        self.elegir = QComboBox()
        self.elegir.setAccessibleName("Documento que se ve")
        self.elegir.setMinimumWidth(420)
        self.elegir.currentIndexChanged.connect(lambda i: self.abrir(self.elegir.itemData(i)) if i >= 0 else None)
        self.elegir.hide()
        cabecera.addWidget(self.elegir)
        cabecera.addStretch(1)
        cerrar = boton("Cerrar", pequeno=True)
        cerrar.clicked.connect(self.accept)
        cabecera.addWidget(cerrar)
        capa.addLayout(cabecera)
        cuerpo = QWidget()
        self.pila = QStackedLayout(cuerpo)
        self.vacio = EstadoVacio("Sin vista previa", "No se ha podido abrir el PDF del proyecto curricular.",
                                 icono=estilo.icono_documento(estilo.T["muted"], 30))
        self.pila.addWidget(self.vacio)
        self.documento = QPdfDocument(self)
        self.visor = QPdfView(self)
        self.visor.setDocument(self.documento)
        self.visor.setPageMode(QPdfView.PageMode.MultiPage)
        self.visor.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.pila.addWidget(self.visor)
        capa.addWidget(cuerpo, 1)

    def abrir(self, pdf: str | Path) -> bool:
        """Enseña el PDF (el mismo `.docx` convertido, con la marca «BORRADOR»). False si no se puede abrir."""
        ok = self.documento.load(str(pdf)) == QPdfDocument.Error.None_
        self.pila.setCurrentWidget(self.visor if ok else self.vacio)
        return ok

    def abrir_varias(self, rutas: list[tuple[str, str | Path]]) -> bool:
        """[(nombre, pdf)…]: con más de una, el desplegable de la cabecera elige cuál se ve."""
        self.elegir.blockSignals(True)
        self.elegir.clear()
        for nombre, ruta in rutas:
            self.elegir.addItem(nombre, str(ruta))
        self.elegir.blockSignals(False)
        self.elegir.setVisible(len(rutas) > 1)
        return self.abrir(rutas[0][1]) if rutas else False
