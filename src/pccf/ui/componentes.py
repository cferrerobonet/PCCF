"""Piezas reutilizables de la interfaz: copia de `ui/componentes.py` de Programaciones (que viene de Partes de salida),
con `EstadoVacio`, el estado vacío de la familia, y el chip de tipo de contenido del PCCF."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPen, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from . import estilo


def etiqueta(texto: str = "", rol: str | None = None, envolver: bool = False) -> QLabel:
    e = QLabel(texto)
    if rol:
        e.setProperty("rol", rol)
    if rol == "etiqueta":
        e.setFont(estilo.etiqueta_fuente(12))
    e.setWordWrap(envolver)
    if envolver:   # sin esto, Qt le da un ancho mínimo grande y empuja la zona que la contiene
        e.setMinimumWidth(40)
    return e


def atajo(tecla: str) -> str:
    """Cómo se escribe un atajo en los botones: «⌘E» en macOS y «Ctrl+E» en Windows."""
    return f"⌘{tecla}" if sys.platform == "darwin" else f"Ctrl+{tecla}"


def boton(texto: str, **propiedades) -> QPushButton:
    b = QPushButton(texto)
    for k, v in propiedades.items():
        b.setProperty(k, v)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def separador_vertical() -> QFrame:
    f = QFrame()
    f.setObjectName("separador")
    f.setFixedWidth(1)
    return f


def refrescar_estilo(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)


class FlujoLayout(QLayout):
    """Coloca chips (grado, ciclo, curso) en filas que se parten solas."""

    def __init__(self, parent=None, espacio: int = 6):
        super().__init__(parent)
        self._items = []
        self._espacio = espacio
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):  # noqa: N802
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):  # noqa: N802
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):  # noqa: N802
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self):  # noqa: N802
        return True

    def heightForWidth(self, ancho):  # noqa: N802
        return self._colocar(QRect(0, 0, ancho, 0), True)

    def setGeometry(self, rect):  # noqa: N802
        super().setGeometry(rect)
        self._colocar(rect, False)

    def sizeHint(self):  # noqa: N802
        return self.minimumSize()

    def minimumSize(self):  # noqa: N802
        tam = QSize()
        for item in self._items:
            tam = tam.expandedTo(item.minimumSize())
        return tam

    def _colocar(self, rect: QRect, solo_medir: bool) -> int:
        x, y, alto_fila = rect.x(), rect.y(), 0
        for item in self._items:
            if item.isEmpty():  # un chip oculto (ciclos de otro grado) no ocupa sitio
                continue
            ancho = item.sizeHint().width()
            if x + ancho > rect.right() + 1 and alto_fila > 0:
                x, y = rect.x(), y + alto_fila + self._espacio
                alto_fila = 0
            if not solo_medir:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x += ancho + self._espacio
            alto_fila = max(alto_fila, item.sizeHint().height())
        return y + alto_fila - rect.y()


class AvisoFlotante(QLabel):
    """Mensaje breve sobre la ventana («Exportada en…»), que se va solo."""

    def __init__(self, padre: QWidget):
        super().__init__(padre)
        self.setObjectName("aviso_flotante")
        self.setWordWrap(True)
        self.hide()
        self._temporizador = QTimer(self, singleShot=True, timeout=self.hide)

    def mostrar(self, texto: str, ms: int = 3500) -> None:
        self.setText(texto)
        padre = self.parentWidget()
        self.setMaximumWidth(min(560, padre.width() - 40))
        self.adjustSize()
        self.move((padre.width() - self.width()) // 2, padre.height() - self.height() - 24)
        self.raise_()
        self.show()
        self._temporizador.start(ms)


class ZonaSoltar(QFrame):
    """Fila con icono, explicación y botón; también admite arrastrar archivos encima."""

    archivos = pyqtSignal(list)

    def __init__(self, titulo: str, explicacion: str, texto_boton: str, extensiones: tuple[str, ...], icono: str):
        super().__init__()
        self.setProperty("rol", "soltar")
        self.setAcceptDrops(True)
        self._extensiones = extensiones
        fila = QHBoxLayout(self)
        fila.setContentsMargins(14, 14, 14, 14)
        fila.setSpacing(14)
        simbolo = QLabel(icono)
        simbolo.setFixedSize(38, 38)
        simbolo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        simbolo.setStyleSheet(
            f"background:{estilo.T['accent_soft']};color:{estilo.T['accent']};border-radius:9px;font-size:18px;"
        )
        fila.addWidget(simbolo, 0, Qt.AlignmentFlag.AlignTop)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        t = etiqueta(titulo)
        t.setStyleSheet("font-weight:700;")
        textos.addWidget(t)
        self.explicacion = etiqueta(explicacion, "muted", envolver=True)
        textos.addWidget(self.explicacion)
        fila.addLayout(textos, 1)
        # Ayuda opcional junto al botón: «?» redondo que abre de dónde sale el archivo.
        self.ayuda = boton("?", pequeno=True)
        self.ayuda.setFixedSize(28, 28)
        self.ayuda.setToolTip("Cómo conseguir y preparar este archivo")
        self.ayuda.setStyleSheet(
            f"QPushButton {{ border-radius: 14px; padding: 0; font-weight: 700; color: {estilo.T['accent']}; }}"
        )
        self.ayuda.hide()
        fila.addWidget(self.ayuda, 0, Qt.AlignmentFlag.AlignVCenter)
        self.boton = boton(texto_boton, pequeno=True)
        fila.addWidget(self.boton, 0, Qt.AlignmentFlag.AlignVCenter)

    def con_ayuda(self, abrir: Callable[[], None]) -> ZonaSoltar:
        self.ayuda.clicked.connect(abrir)
        self.ayuda.show()
        return self

    def _validos(self, evento) -> list[str]:
        urls = evento.mimeData().urls() if evento.mimeData().hasUrls() else []
        return [u.toLocalFile() for u in urls if Path(u.toLocalFile()).suffix.lower() in self._extensiones]

    def dragEnterEvent(self, e):  # noqa: N802
        if self._validos(e):
            self.setProperty("encima", True)
            refrescar_estilo(self)
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):  # noqa: N802
        self.setProperty("encima", False)
        refrescar_estilo(self)

    def dropEvent(self, e):  # noqa: N802
        self.setProperty("encima", False)
        refrescar_estilo(self)
        validos = self._validos(e)
        if validos:
            self.archivos.emit(validos)


class Tarea(QThread):
    """Ejecuta un trabajo largo (documento, PDF, descarga) fuera de la interfaz, con progreso (RNF-03)."""

    progreso = pyqtSignal(int, int, str)
    terminado = pyqtSignal(object)
    fallo = pyqtSignal(str)

    def __init__(self, trabajo: Callable, *args):
        super().__init__()
        self._trabajo = trabajo
        self._args = args

    def run(self):
        try:
            self.terminado.emit(self._trabajo(*self._args, self.progreso.emit))
        except Exception as e:  # noqa: BLE001 - nada puede escapar de run()
            self.fallo.emit(str(e))


class EstadoVacio(QWidget):
    """Icono, título condensado de 26 px, explicación en gris y, si hace falta, botones; todo centrado."""

    def __init__(self, titulo: str, texto: str = "", icono: QPixmap | None = None):
        super().__init__()
        capa = QVBoxLayout(self)
        capa.setContentsMargins(24, 24, 24, 24)
        capa.setSpacing(8)
        capa.addStretch(1)
        self.icono = QLabel()
        self.icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icono is not None:
            self.icono.setPixmap(icono)
        else:
            self.icono.hide()
        capa.addWidget(self.icono)
        self.titulo = QLabel(titulo)
        self.titulo.setFont(estilo.fuente(26, QFont.Weight.Bold, estilo.TITULAR))
        self.titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.titulo.setWordWrap(True)
        capa.addWidget(self.titulo)
        self.texto = etiqueta(texto, "muted", envolver=True)
        self.texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.texto.setVisible(bool(texto))
        capa.addWidget(self.texto)
        self._botones = QHBoxLayout()
        self._botones.setSpacing(10)
        self._botones.addStretch(1)
        self._botones.addStretch(1)
        capa.addSpacing(8)
        capa.addLayout(self._botones)
        capa.addStretch(2)

    def poner(self, titulo: str, texto: str = "") -> None:
        self.titulo.setText(titulo)
        self.texto.setText(texto)
        self.texto.setVisible(bool(texto))

    def con_boton(self, texto: str, accion: Callable[[], None], **propiedades) -> QPushButton:
        b = boton(texto, **propiedades)
        b.clicked.connect(accion)
        self._botones.insertWidget(self._botones.count() - 1, b)
        return b


def politica(w: QWidget, h: QSizePolicy.Policy, v: QSizePolicy.Policy) -> QWidget:
    w.setSizePolicy(h, v)
    return w


def desplazable(contenido: QWidget, horizontal: bool = False) -> QScrollArea:
    """Zona con barra de desplazamiento, sin marco y con el fondo de lo que tiene detrás (como la columna)."""
    zona = QScrollArea()
    zona.setWidgetResizable(True)
    zona.setFrameShape(QFrame.Shape.NoFrame)
    if not horizontal:
        zona.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    zona.setWidget(contenido)
    zona.viewport().setAutoFillBackground(False)
    contenido.setAutoFillBackground(False)  # setWidget lo activa
    return zona


class DelegadoFila(QStyledItemDelegate):
    """Celda de tabla con una línea fina debajo (filas separadas sin rejilla) que respeta el fondo de cada celda: la
    fila nueva resaltada o una hora ajustada a mano. Con `QTableWidget::item` en la hoja de estilos, Qt no lo haría."""

    def paint(self, pintor, opcion, indice):
        super().paint(pintor, opcion, indice)
        pintor.save()
        pintor.setPen(QPen(QColor(estilo.T["line"]), 1))
        r = opcion.rect
        pintor.drawLine(r.bottomLeft(), r.bottomRight())
        pintor.restore()


def chip_tipo(tipo: str, texto: str | None = None) -> QLabel:
    """El chip de un tipo de contenido (`centro`, `ciclo`, `anual`, `normativo`, `derivado`) con su color fijo."""
    e = QLabel(texto or tipo)
    e.setProperty("tipo", tipo)
    e.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    return e


def limpiar(capa: QLayout) -> None:
    """Quita y destruye todo lo que hay en una capa (para rehacer una zona)."""
    while capa.count():
        item = capa.takeAt(0)
        w = item.widget()
        if w is not None:
            w.hide()
            w.deleteLater()
        elif item.layout() is not None:
            limpiar(item.layout())
