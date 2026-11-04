"""Zona izquierda (280 px, maqueta v0): el ciclo (los 15 del centro, por familia y grado, con buscador), el curso y los
apartados de su grado con su número, título corto, chips de tipo e icono de estado."""
from __future__ import annotations

import unicodedata

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pccf import estado as estado_mod

from . import estilo
from .componentes import boton, chip_tipo, etiqueta

GRADOS = {"GB": "Grado básico", "GM": "Grado medio", "GS": "Grado superior"}


def _clave(t: str) -> str:
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


class SelectorCiclo(QFrame):
    """Ventana emergente con buscador y los ciclos agrupados por familia profesional."""

    elegido = pyqtSignal(str)

    def __init__(self, ciclos: list[dict], actual: str, padre=None):
        super().__init__(padre, Qt.WindowType.Popup)
        self.setObjectName("popup")
        self.setFixedWidth(400)
        self._ciclos = ciclos
        capa = QVBoxLayout(self)
        capa.setContentsMargins(10, 10, 10, 10)
        capa.setSpacing(8)
        self.buscar = QLineEdit()
        self.buscar.setObjectName("buscador")
        self.buscar.setPlaceholderText(f"{len(ciclos)} ciclos · buscar por sigla o nombre")
        self.buscar.setAccessibleName("Buscar ciclo")
        self.buscar.setClearButtonEnabled(True)
        self.buscar.textChanged.connect(self._filtrar)
        self.buscar.returnPressed.connect(self._primero)
        capa.addWidget(self.buscar)
        self.lista = QListWidget()
        self.lista.setObjectName("ciclos")
        self.lista.setMinimumHeight(460)
        self.lista.itemActivated.connect(self._elegir)
        self.lista.itemClicked.connect(self._elegir)
        capa.addWidget(self.lista)
        self._actual = actual
        self._filtrar("")

    def _filtrar(self, texto: str) -> None:
        k = _clave(texto.strip())
        self.lista.clear()
        familia = None
        for c in self._ciclos:
            if k and k not in _clave(f"{c['sigla']} {c['nombre']} {c['familia']}"):
                continue
            if c["familia"] != familia:
                familia = c["familia"]
                cab = QListWidgetItem(familia.upper())
                cab.setFlags(Qt.ItemFlag.NoItemFlags)
                cab.setFont(estilo.etiqueta_fuente(11))
                cab.setForeground(estilo.QColor(estilo.T["muted"]))
                self.lista.addItem(cab)
            it = QListWidgetItem(f"{c['grado']}   {c['sigla']} · {c['nombre']}")
            it.setData(Qt.ItemDataRole.UserRole, c["sigla"])
            it.setToolTip(f"{GRADOS.get(c['grado'], c['grado'])} · {c['familia']}")
            self.lista.addItem(it)
            if c["sigla"] == self._actual:
                self.lista.setCurrentItem(it)

    def _primero(self) -> None:
        for i in range(self.lista.count()):
            it = self.lista.item(i)
            if it.data(Qt.ItemDataRole.UserRole):
                self._elegir(it)
                return

    def _elegir(self, it: QListWidgetItem) -> None:
        sigla = it.data(Qt.ItemDataRole.UserRole)
        if sigla:
            self.close()
            self.elegido.emit(sigla)

    def showEvent(self, e):  # noqa: N802
        super().showEvent(e)
        self.buscar.setFocus()


class ListaApartados(QListWidget):
    """Lista cuyas filas miden siempre lo que mide su ventana (sin ello, Qt las ensancha y el icono queda fuera)."""

    def resizeEvent(self, e):  # noqa: N802
        super().resizeEvent(e)
        self.ajustar()

    def ajustar(self) -> None:
        ancho = self.viewport().width()
        for i in range(self.count()):
            it = self.item(i)
            w = self.itemWidget(it)
            if isinstance(w, FilaApartado):
                w.ajustar(ancho)
                it.setSizeHint(QSize(ancho, w.sizeHint().height()))


class FilaApartado(QWidget):
    """Número en su cuadro dorado, título (cortado al ancho, entero en la ayuda), chips de tipo y el icono del
    estado."""

    def __init__(self, ea: estado_mod.EstadoApartado, ancho_texto: int):
        super().__init__()
        self._texto = ea.apartado.titulo
        fila = QHBoxLayout(self)
        fila.setContentsMargins(6, 5, 8, 5)
        fila.setSpacing(9)
        num = QLabel(str(ea.n))
        num.setProperty("rol", "numero")
        num.setFixedSize(26, 26)
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setFont(estilo.fuente(16, QFont.Weight.ExtraBold, estilo.TITULAR))
        fila.addWidget(num, 0, Qt.AlignmentFlag.AlignTop)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        titulo = QLabel()
        titulo.setFont(estilo.fuente(14, QFont.Weight.DemiBold))
        titulo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.titulo = titulo
        self._poner_titulo(ancho_texto)
        titulo.setToolTip(f"{ea.n}. {ea.apartado.titulo}\n{ea.motivo}")
        textos.addWidget(titulo)
        chips = QHBoxLayout()
        chips.setSpacing(4)
        for t in ea.apartado.tipos:
            chips.addWidget(chip_tipo(t))
        chips.addStretch(1)
        textos.addLayout(chips)
        fila.addLayout(textos, 1)
        icono = QLabel()
        icono.setPixmap(estilo.icono_estado(ea.estado, 14))
        icono.setToolTip(estado_mod.NOMBRES[ea.estado])
        icono.setAccessibleName(estado_mod.NOMBRES[ea.estado])
        fila.addWidget(icono, 0, Qt.AlignmentFlag.AlignVCenter)

    def _poner_titulo(self, ancho: int) -> None:
        self.titulo.setText(QFontMetrics(self.titulo.font()).elidedText(self._texto, Qt.TextElideMode.ElideRight,
                                                                        max(60, ancho)))

    def ajustar(self, ancho: int) -> None:
        """Ancho de la fila: el del título es lo que queda tras el número, el icono y los márgenes."""
        self.setFixedWidth(ancho)
        self._poner_titulo(ancho - 6 - 26 - 9 - 9 - 14 - 8 - 2)


class ZonaApartados(QWidget):
    pedir_apartado = pyqtSignal(int)

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setFixedWidth(280)
        capa = QVBoxLayout(self)
        capa.setContentsMargins(12, 12, 8, 8)
        capa.setSpacing(8)
        self.boton_ciclo = boton("", ciclo=True)
        self.boton_ciclo.setAccessibleName("Ciclo formativo")
        self.boton_ciclo.setToolTip("Elegir el ciclo (los del catálogo, por familia profesional)")
        self.boton_ciclo.clicked.connect(self.abrir_selector)
        capa.addWidget(self.boton_ciclo)
        self.resumen = etiqueta("", "pequeno", envolver=True)
        capa.addWidget(self.resumen)
        self.lista = ListaApartados()
        self.lista.setObjectName("apartados")
        self.lista.setAccessibleName("Apartados del proyecto curricular")
        self.lista.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lista.currentItemChanged.connect(self._cambio)
        capa.addWidget(self.lista, 1)
        self._selector: SelectorCiclo | None = None

    def abrir_selector(self) -> None:
        self._selector = SelectorCiclo(self.ctx.ciclos(), self.ctx.sigla, self)
        self._selector.elegido.connect(lambda s: self.ctx.elegir(s))
        self._selector.move(self.boton_ciclo.mapToGlobal(self.boton_ciclo.rect().bottomLeft()))
        self._selector.show()

    def recargar(self, actual: int | None = None, emitir: bool = True) -> None:
        """Rehace la lista; con `emitir`, el centro enseña el apartado (sin él, solo se repintan los estados)."""
        c = self.ctx.ciclo()
        fm = QFontMetrics(estilo.fuente(14, QFont.Weight.Bold))
        nombre = fm.elidedText(f"{c['sigla']} · {c['nombre']}", Qt.TextElideMode.ElideRight, 220)
        self.boton_ciclo.setText(f"{c['familia']} · {c['grado']}\n{nombre}")
        self.boton_ciclo.setToolTip(f"{c['sigla']} · {c['nombre']} ({GRADOS.get(c['grado'], c['grado'])})\n"
                                    "Pulsa para elegir otro ciclo")
        n = len(self.ctx.ciclos())
        self.lista.blockSignals(True)
        self.lista.clear()
        e = self.ctx.estado
        if e is None:
            self.resumen.setText("No se puede leer la carpeta de datos: el error está a la derecha" if self.ctx.error
                                 else f"{n} ciclos en el catálogo · {GRADOS.get(c['grado'], c['grado'])}: la lista "
                                 "de apartados de este grado aún no está en la app")
            self.lista.blockSignals(False)
            return
        norma = sum(1 for a in e.apartados if a.apartado.origen == "norma")
        self.resumen.setText(f"{n} ciclos en el catálogo · {len(e.apartados)} apartados en {c['grado']} "
                             f"({norma} del art. 8.4 y {len(e.apartados) - norma} de la guía)")
        for ea in e.apartados:
            it = QListWidgetItem()
            it.setData(Qt.ItemDataRole.UserRole, ea.n)
            it.setData(Qt.ItemDataRole.AccessibleTextRole,
                       f"{ea.n}. {ea.apartado.titulo}. {estado_mod.NOMBRES[ea.estado]}")
            w = FilaApartado(ea, 170)
            it.setSizeHint(QSize(240, w.sizeHint().height()))
            self.lista.addItem(it)
            self.lista.setItemWidget(it, w)
        self.lista.ajustar()
        if emitir:
            self.lista.blockSignals(False)
            self.ir(actual or 1, emitir=True)
        else:
            self.ir(actual or 1)
            self.lista.blockSignals(False)

    def ir(self, n: int, emitir: bool = False) -> None:
        for i in range(self.lista.count()):
            if self.lista.item(i).data(Qt.ItemDataRole.UserRole) == n:
                if emitir and self.lista.currentRow() == i:
                    self.pedir_apartado.emit(n)
                self.lista.setCurrentRow(i)
                self.lista.scrollToItem(self.lista.item(i))
                return

    def actual(self) -> int | None:
        it = self.lista.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def _cambio(self, it, _anterior) -> None:
        if it is not None:
            self.pedir_apartado.emit(it.data(Qt.ItemDataRole.UserRole))
