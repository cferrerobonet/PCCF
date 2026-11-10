"""Zona izquierda (280 px, maqueta v0): el ciclo (los 15 del centro, por familia y grado, con buscador), el resumen del
avance con su barra y sus filtros, y los apartados de su grado con su número y lo que les falta o si están listos (ADR-024)."""
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
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pccf import estado as estado_mod

from . import estilo
from .componentes import boton, etiqueta

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
    """Una fila de la lista (ADR-024): franja de color a la izquierda y número en su cuadro según el avance (ámbar con
    borde discontinuo si hay que seguir alimentándolo; verde claro si está listo para aprobar; verde lleno si está
    confirmado; rojo si lo pide el vigía), el título (cortado al ancho, entero en la ayuda) y, debajo, lo que le falta o
    que está listo."""

    def __init__(self, ea: estado_mod.EstadoApartado, ancho_texto: int):
        super().__init__()
        self._texto = ea.apartado.titulo
        self.avance = ea.avance
        self.setObjectName("fila")
        self.setProperty("avance", ea.avance)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(10, 6, 8, 6)
        fila.setSpacing(10)
        num = QLabel(str(ea.numero))
        num.setObjectName("numero-avance")
        num.setProperty("avance", ea.avance)
        num.setFixedSize(30, 30)
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setFont(estilo.fuente(17, QFont.Weight.ExtraBold, estilo.TITULAR))
        fila.addWidget(num, 0, Qt.AlignmentFlag.AlignTop)
        textos = QVBoxLayout()
        textos.setSpacing(1)
        titulo = QLabel()
        titulo.setFont(estilo.fuente(14, QFont.Weight.DemiBold))
        titulo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.titulo = titulo
        self._poner_titulo(ancho_texto)
        lista = "\n".join(f"· {x}" for x in ea.faltan[:8]) + ("\n· …" if len(ea.faltan) > 8 else "")
        titulo.setToolTip(f"{ea.numero}. {ea.apartado.titulo}\n{ea.motivo}" + (f"\n\nFalta:\n{lista}" if lista else ""))
        textos.addWidget(titulo)
        linea = QHBoxLayout()
        linea.setSpacing(6)
        self.estado = QLabel(texto_avance(ea))
        self.estado.setObjectName("avance")
        self.estado.setProperty("avance", ea.avance)
        linea.addWidget(self.estado)
        if ea.normas:
            vigia = QLabel("⚠ vigía")
            vigia.setObjectName("avance")
            vigia.setProperty("avance", "revisar")
            vigia.setToolTip(f"Ha cambiado una norma en la que se apoya: {', '.join(ea.normas)}. Revísalo.")
            linea.addWidget(vigia)
        linea.addStretch(1)
        textos.addLayout(linea)
        fila.addLayout(textos, 1)

    def _poner_titulo(self, ancho: int) -> None:
        self.titulo.setText(QFontMetrics(self.titulo.font()).elidedText(self._texto, Qt.TextElideMode.ElideRight,
                                                                        max(60, ancho)))

    def ajustar(self, ancho: int) -> None:
        """Ancho de la fila: el del título es lo que queda tras la franja, el número y los márgenes."""
        self.setFixedWidth(ancho)
        self._poner_titulo(ancho - 10 - 30 - 10 - 8 - 4)


def texto_avance(ea: estado_mod.EstadoApartado) -> str:
    if ea.avance == "vivo":
        if len(ea.faltan) == 1 and ea.faltan[0].startswith("Sin texto"):
            return "● Sin contenido"
        n = len(ea.faltan)
        return f"● Faltan {n} cosa{'s' if n != 1 else ''}" if n else "● Por completar"
    if ea.avance == "listo":
        return "◆ Listo · falta confirmarlo"
    return "✓ Confirmado"


class BarraAvance(QWidget):
    """Barra en tres colores (confirmado, listo, por completar) con su recuento, como un resumen de un vistazo."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(8)
        self.partes: dict[str, int] = {}

    def poner(self, partes: dict[str, int]) -> None:
        self.partes = partes
        self.update()

    def paintEvent(self, _e):  # noqa: N802
        from PyQt6.QtGui import QColor, QPainter

        total = sum(self.partes.values())
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        pintor.setPen(Qt.PenStyle.NoPen)
        pintor.setBrush(QColor(estilo.T["line"]))
        pintor.drawRoundedRect(self.rect(), 4, 4)
        if not total:
            return
        x = 0.0
        colores = {"confirmado": estilo.T["accent"], "listo": estilo.T["accent_soft_fuerte"], "vivo": estilo.T["pend"]}
        for clave in ("confirmado", "listo", "vivo"):
            ancho = self.width() * self.partes.get(clave, 0) / total
            if ancho:
                pintor.setBrush(QColor(colores[clave]))
                pintor.drawRect(int(x), 0, int(round(x + ancho)) - int(x), self.height())
            x += ancho
        pintor.end()


class ZonaApartados(QWidget):
    pedir_apartado = pyqtSignal(int)

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setMinimumWidth(330)   # el ancho lo pone la ventana (ADR-026)
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
        self.barra = BarraAvance()
        self.barra.setToolTip("Confirmado · listo para aprobar · por completar")
        capa.addWidget(self.barra)
        filtros = QHBoxLayout()
        filtros.setSpacing(4)
        self.filtros: dict[str, QPushButton] = {}
        for clave, texto_f, ayuda in (("todos", "Todos", "Todos los apartados"),
                                      ("vivo", "Completar", "Los que hay que seguir alimentando"),
                                      ("listo", "Aprobar", "Los completos: solo falta que el equipo los confirme (o ya "
                                                           "lo están)")):
            b_ = boton(texto_f, chip=True)
            b_.setCheckable(True)
            b_.setProperty("filtro", clave)
            b_.setToolTip(ayuda)
            b_.clicked.connect(lambda _c, k=clave: self.filtrar(k))
            filtros.addWidget(b_)
            self.filtros[clave] = b_
        filtros.addStretch(1)
        capa.addLayout(filtros)
        self.filtro = "todos"
        self.filtros["todos"].setChecked(True)
        self.lista = ListaApartados()
        self.lista.setObjectName("apartados")
        self.lista.setAccessibleName("Apartados del proyecto curricular")
        self.lista.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lista.currentItemChanged.connect(self._cambio)
        capa.addWidget(self.lista, 1)
        self._selector: SelectorCiclo | None = None

    def _pintar_boton_ciclo(self) -> None:
        c = getattr(self, "_ciclo", None)
        if not c:
            return
        fm = QFontMetrics(estilo.fuente(14, QFont.Weight.Bold))
        nombre = fm.elidedText(f"{c['sigla']} · {c['nombre']}", Qt.TextElideMode.ElideRight,
                               max(160, self.width() - 60))
        self.boton_ciclo.setText(f"{c['familia']} · {c['grado']}\n{nombre}")

    def resizeEvent(self, e) -> None:  # noqa: N802
        super().resizeEvent(e)
        self._pintar_boton_ciclo()

    def abrir_selector(self) -> None:
        self._selector = SelectorCiclo(self.ctx.ciclos(), self.ctx.sigla, self)
        self._selector.elegido.connect(lambda s: self.ctx.elegir(s))
        self._selector.move(self.boton_ciclo.mapToGlobal(self.boton_ciclo.rect().bottomLeft()))
        self._selector.show()

    def recargar(self, actual: int | None = None, emitir: bool = True) -> None:
        """Rehace la lista; con `emitir`, el centro enseña el apartado (sin él, solo se repintan los estados)."""
        c = self.ctx.ciclo()
        self._ciclo = c
        self._pintar_boton_ciclo()
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
        cuenta = {k: len(e.con_avance(k)) for k in estado_mod.AVANCES}
        listos = cuenta["listo"] + cuenta["confirmado"]
        revisar = len(e.con("revisar"))
        self.resumen.setText(f"{len(e.apartados)} apartados en {c['grado']} · <b style='color:{estilo.T['accent']}'>"
                             f"{listos} completos</b> · <b style='color:{estilo.T['pend']}'>{cuenta['vivo']} por "
                             "completar</b>" + (f" · <span style='color:{estilo.T['warn']}'>⚠ {revisar} con aviso "
                                                "del vigía</span>" if revisar else ""))
        self.resumen.setToolTip(f"{n} ciclos en el catálogo. Completos: {cuenta['confirmado']} confirmados y "
                                f"{cuenta['listo']} listos para aprobar.")
        self.barra.poner(cuenta)
        self.filtros["todos"].setText(f"Todos {len(e.apartados)}")
        self.filtros["vivo"].setText(f"Completar {cuenta['vivo']}")
        self.filtros["listo"].setText(f"Aprobar {listos}")
        for ea in e.apartados:
            it = QListWidgetItem()
            it.setData(Qt.ItemDataRole.UserRole, ea.n)
            it.setData(Qt.ItemDataRole.AccessibleTextRole,
                       f"{ea.numero}. {ea.apartado.titulo}. {texto_avance(ea)}")
            w = FilaApartado(ea, 170)
            it.setSizeHint(QSize(240, w.sizeHint().height()))
            self.lista.addItem(it)
            self.lista.setItemWidget(it, w)
        self.lista.ajustar()
        self._aplicar_filtro()
        if emitir:
            self.lista.blockSignals(False)
            self.ir(actual or 1, emitir=True)
        else:
            self.ir(actual or 1)
            self.lista.blockSignals(False)

    def filtrar(self, clave: str) -> None:
        """Enseña todos, solo los que hay que completar (y los que pide revisar el vigía) o solo los completos."""
        self.filtro = clave
        for k, b_ in self.filtros.items():
            b_.setChecked(k == clave)
        self._aplicar_filtro()

    def _aplicar_filtro(self) -> None:
        quiero = {"todos": None, "vivo": {"vivo"}, "listo": {"listo", "confirmado"}}[self.filtro]
        for i in range(self.lista.count()):
            w = self.lista.itemWidget(self.lista.item(i))
            self.lista.item(i).setHidden(quiero is not None and getattr(w, "avance", None) not in quiero)

    def ir(self, n: int, emitir: bool = False) -> None:
        for i in range(self.lista.count()):
            if self.lista.item(i).data(Qt.ItemDataRole.UserRole) == n:
                if self.lista.item(i).isHidden():   # el que se pide no está en el filtro: se enseñan todos
                    self.filtrar("todos")
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
