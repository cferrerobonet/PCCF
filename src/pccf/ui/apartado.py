"""Zona central (flexible, maqueta v0): el apartado elegido.

- Cabecera: número en su cuadro dorado («de 20»), título, chips de tipo y base (norma · punto de la guía).
- La guía a la vista (ADR-014): caja plegable de solo lectura con su punto de la guía y lo que pide.
- Aviso del vigía si una norma en la que se apoya ha cambiado (no se ha tocado ningún texto).
- Contenido según el apartado: lo oficial en gris y de solo lectura con su fuente; lo calculado, en tablas de solo
  lectura con «Se calcula de…»; los bloques del equipo, editables como en Word (ADR-020), con su chip de tipo, autoría y estado,
  «Confirmar bloque» y la banda: azul si está en borrador, ámbar si viene heredada del curso anterior (ADR-025).

Los bloques se guardan solos al dejar de escribir (un texto cambiado vuelve a borrador: hay que confirmarlo).
"""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QRectF, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QFont, QPainter
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pccf import bloques, citas, derivados, estado
from pccf.bloques import Bloque

from . import estilo
from .componentes import DelegadoFila, FlujoLayout, boton, chip_tipo, desplazable, etiqueta, limpiar
from .editor import EditorTexto

logger = logging.getLogger(__name__)
ROL_DATO = Qt.ItemDataRole.UserRole


# ---------------------------------------------------------------------------------------------------------------------
# Piezas
# ---------------------------------------------------------------------------------------------------------------------
def caja(rol: str = "caja", margen: tuple[int, int, int, int] = (14, 12, 14, 12)) -> tuple[QFrame, QVBoxLayout]:
    f = QFrame()
    f.setProperty("rol", rol)
    capa = QVBoxLayout(f)
    capa.setContentsMargins(*margen)
    capa.setSpacing(8)
    return f, capa


def titulo_caja(texto: str, fuente: str = "") -> QWidget:
    """«DEL CATÁLOGO   BOE · RD 1127/2010 · comprobado el …»: etiqueta en versalitas y su fuente en gris."""
    w = QWidget()
    fila = QHBoxLayout(w)
    fila.setContentsMargins(0, 0, 0, 0)
    fila.setSpacing(10)
    fila.addWidget(etiqueta(texto, "etiqueta"))
    if fuente:
        f = etiqueta(fuente, "pequeno", envolver=True)
        fila.addWidget(f, 1)
    else:
        fila.addStretch(1)
    return w


class TablaAjustable(QTableWidget):
    """Tabla que rehace la altura de sus filas al cambiar de ancho (texto que se parte en varias líneas)."""

    def resizeEvent(self, e):  # noqa: N802
        super().resizeEvent(e)
        self.resizeRowsToContents()
        _ajustar_alto(self)


def tabla(cabeceras: list[str], filas: list[list[str]], estirar: int = 1, mono: tuple[int, ...] = (),
          derecha: tuple[int, ...] = ()) -> QTableWidget:
    """Tabla de solo lectura sin rejilla, con una línea fina entre filas (DelegadoFila), a toda su altura."""
    t = TablaAjustable(len(filas), len(cabeceras))
    t.setHorizontalHeaderLabels(cabeceras)
    t.verticalHeader().hide()
    t.setShowGrid(False)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    t.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    t.setWordWrap(True)
    t.setItemDelegate(DelegadoFila(t))
    t.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    for i, fila in enumerate(filas):
        for j, valor in enumerate(fila):
            it = QTableWidgetItem(valor)
            if j in mono:
                it.setFont(estilo.fuente(13, familia=estilo.MONO))
                it.setForeground(QColor(estilo.T["accent"]))   # códigos en verde (ADR-025)
            if j in derecha:
                it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            t.setItem(i, j, it)
    cab = t.horizontalHeader()
    cab.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    for j in range(len(cabeceras)):
        cab.setSectionResizeMode(j, QHeaderView.ResizeMode.Stretch if j == estirar
                                 else QHeaderView.ResizeMode.ResizeToContents)
    t.resizeColumnsToContents()
    for j in range(len(cabeceras)):
        if j != estirar and t.columnWidth(j) > 200:   # el texto largo se parte; la tabla no empuja la zona
            cab.setSectionResizeMode(j, QHeaderView.ResizeMode.Interactive)
            t.setColumnWidth(j, 200)
    t.resizeRowsToContents()
    _ajustar_alto(t)
    t.setMinimumWidth(200)   # sin barra horizontal, Qt pediría el ancho de todas las columnas
    return t


def _ajustar_alto(t: QTableWidget) -> None:
    alto = t.horizontalHeader().height() + sum(t.rowHeight(i) for i in range(t.rowCount())) + 4
    t.setFixedHeight(alto)


def _humano(nombre: str) -> str:
    return nombre.removesuffix(".md")


# ---------------------------------------------------------------------------------------------------------------------
# Matriz módulo × competencia
# ---------------------------------------------------------------------------------------------------------------------
class DelegadoPunto(DelegadoFila):
    """Celda de la matriz: punto verde si el módulo contribuye a la competencia."""

    def paint(self, pintor, opcion, indice):
        if indice.data(ROL_DATO) is True:
            super().paint(pintor, opcion, indice)
            pintor.save()
            pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
            pintor.setPen(Qt.PenStyle.NoPen)
            pintor.setBrush(QColor(estilo.T["accent"]))
            r = opcion.rect
            d = min(r.width(), r.height(), 14)
            pintor.drawEllipse(QRectF(r.center().x() - d / 2 + 1, r.center().y() - d / 2 + 1, d, d))
            pintor.restore()
        else:
            super().paint(pintor, opcion, indice)


def matriz(k: derivados.Contribucion) -> QTableWidget:
    letras = [x[0] for x in k.competencias]
    vistos, filas = set(), []
    for fila, ls in k.filas:
        if (fila.codigo, fila.nombre) in vistos:
            continue
        vistos.add((fila.codigo, fila.nombre))
        filas.append((fila, ls))
    t = QTableWidget(len(filas), len(letras) + 2)
    t.setHorizontalHeaderLabels(["Módulo", *[f"{x})" for x in letras], "N.º"])
    t.verticalHeader().hide()
    t.setShowGrid(False)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    t.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    t.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    t.setItemDelegate(DelegadoPunto(t))
    for j, (letra, texto) in enumerate(k.competencias, start=1):
        t.horizontalHeaderItem(j).setToolTip(f"{letra}) {texto}")
    for i, (fila, ls) in enumerate(filas):
        it = QTableWidgetItem(f"{fila.codigo}  {fila.nombre}")
        it.setToolTip(f"{fila.codigo} {fila.nombre} ({fila.curso}.º curso)")
        t.setItem(i, 0, it)
        for j, letra in enumerate(letras, start=1):
            c = QTableWidgetItem("")
            c.setData(ROL_DATO, letra in ls)
            if letra in ls:
                c.setToolTip(f"{fila.codigo} contribuye a la competencia {letra})")
            t.setItem(i, j, c)
        n = QTableWidgetItem(str(len(ls)) if ls else "sin orient.")
        n.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if not ls:
            n.setForeground(QColor(estilo.T["pend"]))   # lo decide el equipo: por completar
            n.setToolTip("El real decreto no le asigna competencias (módulo nuevo de la LO 3/2022): lo decide el equipo")
        t.setItem(i, len(letras) + 1, n)
    t.setWordWrap(False)
    t.setTextElideMode(Qt.TextElideMode.ElideRight)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    cab = t.horizontalHeader()
    cab.setMinimumSectionSize(16)
    cab.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    for j in range(1, len(letras) + 1):
        cab.setSectionResizeMode(j, QHeaderView.ResizeMode.Fixed)
        t.setColumnWidth(j, 17)
    cab.setSectionResizeMode(len(letras) + 1, QHeaderView.ResizeMode.ResizeToContents)
    cab.setFont(estilo.fuente(12, familia=estilo.MONO))
    for i in range(t.rowCount()):
        t.setRowHeight(i, 26)
    _ajustar_alto(t)
    t.setFixedHeight(t.height() + 14)
    t.setMinimumWidth(240)
    return t


# ---------------------------------------------------------------------------------------------------------------------
# Bloque de texto
# ---------------------------------------------------------------------------------------------------------------------
class TarjetaBloque(QFrame):
    """Un bloque: banda de heredado, chip de tipo, archivo y autoría, editor, citas y acciones."""

    cambiado = pyqtSignal()        # el estado ha cambiado (repintar la lista y el estado)
    confirmado = pyqtSignal()      # repintar también el centro

    def __init__(self, ctx, b: Bloque):
        super().__init__()
        self.ctx = ctx
        self.b = b
        self.setProperty("rol", "bloque")
        hered = estado.de_bloque(b) == "heredado"
        self.setProperty("heredado", hered)
        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 12)
        capa.setSpacing(8)
        if not b.confirmado:
            banda = QFrame()
            banda.setProperty("rol", "banda")
            banda.setProperty("heredado", hered)   # ámbar (aviso) si viene del curso anterior; azul si es borrador
            fb = QHBoxLayout(banda)
            fb.setContentsMargins(14, 7, 10, 7)
            texto = (f"⚠ Heredado de {b.origen.rsplit(' ', 1)[-1]} · revisa y confirma" if hered
                     else "ⓘ En borrador · revisa y confirma")
            e = etiqueta(texto, "banda")
            e.setProperty("heredado", hered)
            e.setFont(estilo.fuente(14, QFont.Weight.DemiBold))
            fb.addWidget(e, 1)
            self.boton_confirmar = boton("Confirmar bloque", pequeno=True, primario=True)
            self.boton_confirmar.setToolTip("El equipo da el texto por bueno: deja de salir en borrador")
            self.boton_confirmar.clicked.connect(self.confirmar)
            fb.addWidget(self.boton_confirmar)
            capa.addWidget(banda)
        cuerpo = QVBoxLayout()
        cuerpo.setContentsMargins(14, 4 if not b.confirmado else 12, 14, 0)
        cuerpo.setSpacing(8)
        cab = QHBoxLayout()
        cab.setSpacing(8)
        cab.addWidget(chip_tipo(b.tipo))
        nombre = etiqueta(_humano(b.ruta.name))
        nombre.setFont(estilo.fuente(15, QFont.Weight.Bold))
        nombre.setToolTip(str(b.ruta))
        cab.addWidget(nombre)
        cab.addStretch(1)
        cuerpo.addLayout(cab)
        self.autoria = etiqueta("", "pequeno", envolver=True)
        cuerpo.addWidget(self.autoria)
        self.editor = EditorTexto(b.cuerpo)
        self.editor.texto.setAccessibleName(f"Texto del bloque {_humano(b.ruta.name)}")
        cuerpo.addWidget(self.editor)
        chips = QWidget()
        flujo = FlujoLayout(chips, 6)
        for c in b.citas:
            norma = citas.resolver(ctx.cat, c["norma"])
            art = f" · art. {c['articulo']}" if c.get("articulo") else ""
            texto = f"cita: {norma.cita_corta if norma else c['norma']}{art}"
            chip = chip_tipo("cita", texto if len(texto) <= 56 else texto[:55] + "…")
            chip.setToolTip(f"{norma.titulo} ({norma.id}){art}" if norma else
                            f"«{c['norma']}» no está en el catálogo de Programaciones: el vigía no la puede vigilar")
            if norma is None:
                chip.setStyleSheet(f"color: {estilo.T['warn']}; background: {estilo.T['warn_soft']};")
            flujo.addWidget(chip)
        cuerpo.addWidget(chips)
        pie = QHBoxLayout()
        pie.setSpacing(6)
        pie.addStretch(1)
        self.guardado = etiqueta("", "pequeno")
        pie.addWidget(self.guardado)
        exportar = boton("Exportar a Word…", pequeno=True)
        exportar.setToolTip("Guardar el bloque en Word para que alguien del equipo lo escriba o lo revise; "
                            "después se importa con «Importar Word…»")
        exportar.clicked.connect(self.exportar)
        pie.addWidget(exportar)
        if b.confirmado:
            hecho = etiqueta("Confirmado", "estado-confirmado")
            pie.addWidget(hecho)
        capa.addLayout(cuerpo)
        envoltura = QHBoxLayout()
        envoltura.setContentsMargins(14, 0, 14, 0)
        envoltura.addLayout(pie)
        capa.addLayout(envoltura)
        self._sucio = False
        self._temporizador = QTimer(self, singleShot=True, interval=900, timeout=self.guardar)
        self.editor.cambiado.connect(self._tecleado)
        self._pintar_autoria()

    def _pintar_autoria(self) -> None:
        self.autoria.setText(f"{estado.NOMBRES[estado.de_bloque(self.b)]} · {self.b.aportado_por} · {self.b.fecha}")

    def _tecleado(self) -> None:
        self._sucio = True
        self.guardado.setText("Sin guardar…")
        self._temporizador.start()

    def guardar(self) -> None:
        """Guarda si hay cambios (se llama también al cambiar de apartado y al cerrar)."""
        self._temporizador.stop()
        if not self._sucio:
            return
        self._sucio = False
        antes = self.b.estado
        try:
            self.b = bloques.guardar(self.b, self.editor.markdown(), self.ctx.hoy())
        except (OSError, bloques.BloqueNoValido) as e:
            self.guardado.setText("No se ha guardado")
            QMessageBox.warning(self, "Guardar el bloque", str(e))
            return
        self.guardado.setText("Guardado")
        self._pintar_autoria()
        if self.b.estado != antes:
            self.cambiado.emit()

    def confirmar(self) -> None:
        self.guardar()
        try:
            self.b = bloques.confirmar(self.b, self.ctx.hoy())
        except (OSError, bloques.BloqueNoValido) as e:
            QMessageBox.warning(self, "Confirmar el bloque", str(e))
            return
        self.confirmado.emit()

    def _numero(self) -> int:
        from pccf import apartados as aps

        try:
            return aps.numero(self.ctx.grado, self.b.apartado)
        except KeyError:
            return self.b.apartado

    def exportar(self) -> None:
        self.guardar()
        nombre = f"PCCF {self.ctx.sigla} {self.ctx.curso} - apartado {self._numero()} - {_humano(self.b.ruta.name)}.docx"
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar a Word", str(Path.home() / nombre), "Word (*.docx)")
        if not ruta:
            return
        titulo = f"PCCF {self.ctx.sigla} {self.ctx.curso} · apartado {self._numero()} · {_humano(self.b.ruta.name)}"
        try:
            Path(ruta).write_bytes(bloques.a_word(self.b, titulo))
        except OSError as e:
            QMessageBox.warning(self, "Exportar a Word", str(e))


# ---------------------------------------------------------------------------------------------------------------------
# Vista del apartado
# ---------------------------------------------------------------------------------------------------------------------
class VistaApartado(QWidget):
    pedir_vigia = pyqtSignal()
    repintar = pyqtSignal()          # algo ha cambiado: lista, estado y centro
    estados_cambiados = pyqtSignal()  # solo la lista y el estado (el texto sigue en edición)
    pedir_nuevo_bloque = pyqtSignal(int)
    pedir_importar = pyqtSignal()

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.n: int | None = None
        self.tarjetas: list[TarjetaBloque] = []
        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        contenido = QWidget()
        self.capa = QVBoxLayout(contenido)
        self.capa.setContentsMargins(22, 18, 22, 24)
        self.capa.setSpacing(12)
        self.zona = desplazable(contenido)
        capa.addWidget(self.zona)

    def guardar_pendiente(self) -> None:
        for t in self.tarjetas:
            t.guardar()

    def mostrar(self, n: int | None) -> None:
        self.guardar_pendiente()
        self.tarjetas = []
        limpiar(self.capa)
        self.n = n
        e = self.ctx.estado
        if e is None or n is None:
            self.capa.addWidget(self._vacio())
            return
        ea = e.de(n)
        self.capa.addWidget(self._cabecera(ea, len(e.apartados)))
        self.capa.addWidget(self._guia(ea))
        if ea.normas:
            self.capa.addWidget(self._aviso_vigia(ea))
        try:
            constructor = {1: self._apartado_1, 2: self._apartado_2, 3: self._apartado_3, 4: self._apartado_4,
                           7: self._apartado_7, 20: self._apartado_20}.get(n)
            if constructor:
                constructor(ea)
            elif not ea.bloques:
                self.capa.addWidget(self._pendiente(ea))
        except Exception as ex:  # noqa: BLE001 - un dato mal no tumba la ventana: se dice
            logger.exception("Apartado %s", n)
            self.capa.addWidget(etiqueta(f"✕ No se puede enseñar este apartado: {ex}", "error", envolver=True))
        for b in ea.bloques:
            t = TarjetaBloque(self.ctx, b)
            t.cambiado.connect(self.estados_cambiados)
            t.confirmado.connect(self.repintar)
            self.tarjetas.append(t)
            self.capa.addWidget(t)
        if set(ea.apartado.tipos) - {"derivado"}:
            self.capa.addWidget(self._nuevo(ea))
        self.capa.addStretch(1)
        self.zona.verticalScrollBar().setValue(0)

    # -- piezas comunes ---------------------------------------------------------------------------------------------
    def _vacio(self) -> QWidget:
        from .componentes import EstadoVacio

        c = self.ctx.ciclo()
        v = EstadoVacio(f"{c['sigla']} · {c['nombre']}",
                        self.ctx.error or "La lista de apartados de grado básico (Decreto 117/2025, 17 apartados) "
                        "llega con la fase de grado básico. Elige un ciclo de grado medio o superior.",
                        icono=estilo.icono_documento(estilo.T["muted"], 30))
        v.texto.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if self.ctx.error:
            v.con_boton("Releer la carpeta de datos", self.ctx.recalcular, primario=True)
        return v

    def _cabecera(self, ea: estado.EstadoApartado, total: int) -> QWidget:
        w = QWidget()
        fila = QHBoxLayout(w)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(16)
        num = QLabel(f"{ea.numero}")
        num.setProperty("rol", "numero")
        num.setFixedSize(64, 64)
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setFont(estilo.fuente(36, QFont.Weight.ExtraBold, estilo.TITULAR))
        num.setToolTip(f"Apartado {ea.numero} de {total}")
        caja_num = QVBoxLayout()
        caja_num.setSpacing(0)
        caja_num.addWidget(num)
        de = etiqueta(f"de {total}", "pequeno")
        de.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caja_num.addWidget(de)
        caja_num.addStretch(1)
        fila.addLayout(caja_num)
        textos = QVBoxLayout()
        textos.setSpacing(6)
        t = QLabel(ea.apartado.titulo.upper())
        t.setWordWrap(True)
        t.setMinimumWidth(40)
        t.setFont(estilo.fuente(26, QFont.Weight.Bold, estilo.TITULAR))
        t.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        textos.addWidget(t)
        fila_chips = QWidget()
        chips = FlujoLayout(fila_chips, 6)
        for tipo in ea.apartado.tipos:
            chips.addWidget(chip_tipo(tipo))
        base = (f"{ea.apartado.decreto}, art. 8.4" if ea.apartado.origen == "norma" else "Lo añade la guía de la DGFP")
        chips.addWidget(etiqueta(f"{base} · Guía {ea.apartado.guia}", "muted"))
        est = etiqueta(estado.NOMBRES[ea.estado], f"estado-{ea.estado}")
        est.setToolTip(ea.motivo)
        chips.addWidget(est)
        textos.addWidget(fila_chips)
        fila.addLayout(textos, 1)
        return w

    def _guia(self, ea: estado.EstadoApartado) -> QWidget:
        f, capa = caja("guia", (14, 8, 14, 8))
        cab = QHBoxLayout()
        b = boton(f"Guía de la DGFP · {ea.apartado.guia}   ▾", enlace=True)
        b.setToolTip("Qué pide la guía práctica del PCCF en este apartado")
        cab.addWidget(b)
        cab.addStretch(1)
        cab.addWidget(etiqueta("solo lectura", "pequeno"))
        capa.addLayout(cab)
        pide = etiqueta(ea.apartado.pide, envolver=True)
        pide.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        capa.addWidget(pide)

        def plegar():
            pide.setVisible(not pide.isVisible())
            b.setText(f"Guía de la DGFP · {ea.apartado.guia}   {'▾' if pide.isVisible() else '▸'}")

        b.clicked.connect(plegar)
        return f

    def _aviso_vigia(self, ea: estado.EstadoApartado) -> QWidget:
        f, capa = caja("aviso-vigia", (14, 10, 14, 10))
        fila = QHBoxLayout()
        e = etiqueta(f"§ El vigía ha visto cambiar {', '.join(ea.normas)}, en la que se apoya este apartado. "
                     "No se ha tocado ningún texto: revísalo y márcalo como revisado.", "aviso-vigia", envolver=True)
        fila.addWidget(e, 1)
        b = boton("Ver informe ›", enlace=True, verde=True)
        b.clicked.connect(self.pedir_vigia)
        fila.addWidget(b, 0, Qt.AlignmentFlag.AlignBottom)
        capa.addLayout(fila)
        return f

    def _pendiente(self, ea: estado.EstadoApartado) -> QWidget:
        f, capa = caja("nuevo")
        capa.addWidget(etiqueta("Pendiente", "estado-borrador"))
        capa.addWidget(etiqueta("Este apartado aún no tiene texto: el documento lo enseña con «Pendiente» y lo que "
                                "pide la guía. El equipo lo redacta en un bloque.", "muted", envolver=True))
        return f

    def _nuevo(self, ea: estado.EstadoApartado) -> QWidget:
        f, capa = caja("nuevo")
        fila = QHBoxLayout()
        tipos = [t for t in ea.apartado.tipos if t != "derivado"]
        fila.addWidget(etiqueta(f"Añadir un bloque de texto ({', '.join(tipos)}) o traer uno que haya preparado "
                                "alguien del equipo.", "muted", envolver=True), 1)
        capa.addLayout(fila)
        botones = QHBoxLayout()
        anadir = boton("Añadir bloque", pequeno=True)
        anadir.clicked.connect(lambda: self.pedir_nuevo_bloque.emit(ea.n))
        botones.addWidget(anadir)
        importar = boton("Importar Word…", pequeno=True)
        importar.setToolTip("Un Word exportado desde la app vuelve a su bloque; cualquier otro Word, a un bloque nuevo "
                            "de este apartado")
        importar.clicked.connect(self.pedir_importar)
        botones.addWidget(importar)
        botones.addStretch(1)
        capa.addLayout(botones)
        return f

    def _calculado(self, texto: str) -> QLabel:
        return etiqueta(texto, "pequeno", envolver=True)

    # -- apartados con contenido calculado ---------------------------------------------------------------------------
    def _apartado_1(self, ea: estado.EstadoApartado) -> None:
        cat, ctx = self.ctx.cat, self.ctx
        c = cat.ciclo(ctx.sigla)
        ident = derivados.identificacion(cat, ctx.datos, ctx.sigla, ctx.curso)
        f, capa = caja("curriculo")
        rd = ident.rd.cita_corta if ident.rd else "real decreto del título"
        capa.addWidget(titulo_caja("Del catálogo", f"{rd} · catálogo comprobado el {c.get('comprobado', cat.fecha)}"))
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(18)
        rejilla.setVerticalSpacing(6)
        from pccf.catalogo import texto

        filas = [("Título", ident.titulo), ("Familia", ident.familia),
                 ("Grado y duración", f"{ident.grado_largo} · {ident.horas_total} horas"),
                 ("Real decreto", ident.rd.cita if ident.rd else "Pendiente"),
                 ("Competencia general", texto(c.get("competencia_general_corregida") or c.get("competencia_general")))]
        for i, (k, v) in enumerate(filas):
            rejilla.addWidget(etiqueta(k, "muted"), i, 0, Qt.AlignmentFlag.AlignTop)
            valor = etiqueta(v, envolver=True)
            valor.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            rejilla.addWidget(valor, i, 1)
        rejilla.setColumnStretch(1, 1)
        capa.addLayout(rejilla)
        self.capa.addWidget(f)

        f, capa = caja()
        dep = ident.departamento
        capa.addWidget(titulo_caja("Del centro", "carpeta de datos · centro/departamentos.yaml"))
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(18)
        datos = [("Departamento", dep["nombre"] if dep else "Pendiente"),
                 ("Jefatura del departamento", dep["jefatura"] if dep else "Pendiente"),
                 ("Tutorías", " · ".join(f"{g}: {n}" for g, n in ident.tutorias) if ident.tutorias else "Pendiente")]
        for i, (k, v) in enumerate(datos):
            rejilla.addWidget(etiqueta(k, "muted"), i, 0, Qt.AlignmentFlag.AlignTop)
            valor = etiqueta(v, None if v != "Pendiente" else "estado-borrador", envolver=True)
            rejilla.addWidget(valor, i, 1)
        rejilla.setColumnStretch(1, 1)
        capa.addLayout(rejilla)
        self.capa.addWidget(f)
        self.capa.addWidget(self._equipo(ident))

    def _equipo(self, ident: derivados.Identificacion) -> QWidget:
        ctx = self.ctx
        ruta = ctx.datos.carpeta / "cursos" / ctx.curso / ctx.sigla / "equipo.yaml"
        tiene = any(m.docentes for m in ident.modulos)
        f = QFrame()
        f.setProperty("rol", "bloque")
        hered = estado.heredado(ident.equipo_origen)
        f.setProperty("heredado", tiene and not ident.equipo_confirmado and hered)
        capa = QVBoxLayout(f)
        capa.setContentsMargins(0, 0, 0, 12)
        capa.setSpacing(8)
        if tiene and not ident.equipo_confirmado:
            banda = QFrame()
            banda.setProperty("rol", "banda")
            banda.setProperty("heredado", hered)
            fb = QHBoxLayout(banda)
            fb.setContentsMargins(14, 7, 10, 7)
            texto = (f"⚠ Heredado de {ident.equipo_origen.rsplit(' ', 1)[-1]} · revisa y confirma" if hered
                     else "ⓘ En borrador · revisa y confirma")
            et = etiqueta(texto, "banda")
            et.setProperty("heredado", hered)
            fb.addWidget(et, 1)
            confirmar = boton("Confirmar equipo", pequeno=True, primario=True)
            confirmar.clicked.connect(self._confirmar_equipo)
            fb.addWidget(confirmar)
            capa.addWidget(banda)
        interior = QVBoxLayout()
        interior.setContentsMargins(14, 12 if ident.equipo_confirmado or not tiene else 4, 14, 0)
        interior.setSpacing(8)
        cab = QHBoxLayout()
        cab.addWidget(chip_tipo("anual"))
        t = etiqueta(f"1.1 Equipo docente {ctx.curso}")
        t.setFont(estilo.fuente(15, QFont.Weight.Bold))
        cab.addWidget(t)
        cab.addStretch(1)
        cab.addWidget(etiqueta("lo aporta la jefatura de departamento", "pequeno", envolver=True))
        interior.addLayout(cab)
        if not tiene:
            interior.addWidget(etiqueta(f"Falta el equipo docente de {ctx.sigla} en {ctx.curso} "
                                        f"(cursos/{ctx.curso}/{ctx.sigla}/equipo.yaml de la carpeta de datos). "
                                        "Sin él, el documento enseña «Pendiente» en cada módulo.",
                                        "muted", envolver=True))
        else:
            filas = [[m.codigo, m.nombre, " / ".join(m.docentes) if m.docentes else "Pendiente", f"{m.curso}.º"]
                     for m in ident.modulos]
            interior.addWidget(tabla(["Código", "Módulo", "Profesorado", "Curso"], filas, estirar=1,
                                               mono=(0,)))
        pie = QHBoxLayout()
        pie.addStretch(1)
        if ruta.is_file():
            abrir = boton("Abrir equipo.yaml", pequeno=True)
            abrir.setToolTip(f"{ruta}\nSe edita en el editor del equipo; al volver, la app lo relee")
            abrir.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta))))
            pie.addWidget(abrir)
        interior.addLayout(pie)
        capa.addLayout(interior)
        return f

    def _confirmar_equipo(self) -> None:
        try:
            self.ctx.datos.confirmar_equipo(self.ctx.curso, self.ctx.sigla)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Confirmar el equipo", str(e))
            return
        self.repintar.emit()

    def _apartado_2(self, ea: estado.EstadoApartado) -> None:
        cat, ctx = self.ctx.cat, self.ctx
        marco = derivados.marco_normativo(cat, ctx.sigla, ctx.curso)
        idx = citas.indice(cat, ctx.datos, ctx.sigla, ctx.curso)
        inf = ctx.informe
        cambiadas = {c.norma: c for c in inf.cambios} if inf else {}
        no_vigentes = {c.norma for c in inf.no_vigentes} if inf else set()
        f, capa = caja()
        capa.addWidget(titulo_caja("Se calcula del catálogo",
                                   f"normativa del catálogo de Programaciones · comprobada el {cat.fecha} · por fecha"))
        for ambito, titulo in (("estatal", "2.1 Normativa estatal"), ("autonomico", "2.2 Normativa autonómica")):
            capa.addWidget(etiqueta(titulo, "etiqueta"))
            filas = []
            for n in marco[ambito]:
                if n.id in cambiadas:
                    vig = "Cambia"
                elif n.id in no_vigentes:
                    vig = "No vigente"
                elif inf is None or inf.anterior is None:
                    vig = "Sin revisar"
                else:
                    vig = "Sin cambios"
                usos = idx.usos.get(n.id, [])
                filas.append([n.cita, n.id, vig, str(len(usos))])
            t = tabla(["Norma", "Id", "Vigía", "Usos"], filas, estirar=0, mono=(1,), derecha=(3,))
            for i, n in enumerate(marco[ambito]):
                usos = idx.usos.get(n.id, [])
                t.item(i, 3).setToolTip("\n".join(f"{u.numero or '—'} · {u.titulo} · {u.detalle}" for u in usos))
                t.item(i, 0).setToolTip(f"{n.titulo}\n{n.enlace}")
                if n.id in cambiadas:
                    t.item(i, 2).setToolTip("\n".join(cambiadas[n.id].que))
                elif inf is not None and inf.anterior:
                    t.item(i, 2).setToolTip(f"Sin cambios desde la revisión del {inf.anterior}")
                if n.id in cambiadas or n.id in no_vigentes:
                    t.item(i, 2).setForeground(QColor(estilo.T["warn"]))
            capa.addWidget(t)
        nota = etiqueta("Las normas propias del centro llegarán con normativa.yaml de la carpeta de datos. «Usos»: "
                        "apartados y bloques que se apoyan en cada norma (los vigila el vigía).", "pequeno",
                        envolver=True)
        capa.addWidget(nota)
        self.capa.addWidget(f)
        if idx.sin_vigilar:
            f, capa = caja("aviso-ambar")
            capa.addWidget(etiqueta("⚠ Citas sin vigilar", "aviso-texto"))
            capa.addWidget(etiqueta("Estas citas de los bloques no casan con una sola norma del catálogo: el vigía no "
                                    "puede vigilarlas. O entran en el catálogo o se quitan de las citas.", "muted",
                                    envolver=True))
            for cita_, usos in idx.sin_vigilar.items():
                capa.addWidget(etiqueta(f"• {cita_} — {', '.join(sorted({u.detalle for u in usos}))}",
                                        envolver=True))
            self.capa.addWidget(f)

    def _apartado_3(self, ea: estado.EstadoApartado) -> None:
        k = derivados.contribucion(self.ctx.cat, self.ctx.sigla)
        f, capa = caja("curriculo")
        capa.addWidget(titulo_caja("Del catálogo", f"competencias profesionales del título · {k.fuente}"))
        capa.addWidget(tabla(["Letra", "Competencia profesional", "Peso"],
                                       [[f"{x})", t, "—"] for x, t in k.competencias], estirar=1, mono=(0,),
                                       derecha=(2,)))
        capa.addWidget(etiqueta("La ponderación en % (suma 100) la decide el equipo docente tras el análisis del "
                                "contexto: está pendiente.", "estado-borrador", envolver=True))
        self.capa.addWidget(f)

    def _apartado_4(self, ea: estado.EstadoApartado) -> None:
        k = derivados.contribucion(self.ctx.cat, self.ctx.sigla)
        rd = self.ctx.cat.normas.get(k.fuente)
        f, capa = caja()
        capa.addWidget(titulo_caja("Módulo × competencia",
                                   f"orientaciones pedagógicas del {rd.cita_corta if rd else 'real decreto'} · se "
                                   "calcula, no se escribe"))
        capa.addWidget(matriz(k))
        sin = sorted({fila.codigo for fila, ls in k.filas if not ls})
        if sin:
            capa.addWidget(etiqueta(f"Sin orientación en el real decreto ({', '.join(sin)}): son módulos nuevos de la "
                                    "LO 3/2022 o comunes; su contribución la decide el equipo.", "pequeno",
                                    envolver=True))
        self.capa.addWidget(f)
        f, capa = caja()
        cab = QHBoxLayout()
        cab.addWidget(chip_tipo("ciclo"))
        t = etiqueta("Ajustes del equipo docente")
        t.setFont(estilo.fuente(15, QFont.Weight.Bold))
        cab.addWidget(t)
        cab.addStretch(1)
        cab.addWidget(etiqueta("ninguno · la tabla sale tal cual del real decreto", "pequeno", envolver=True))
        capa.addLayout(cab)
        capa.addWidget(etiqueta("Si el equipo decide que un módulo aporta más o menos a una competencia, se anotará "
                                "con su motivo en ajustes.yaml del ciclo (llega con el resto de apartados de SEA).",
                                "muted", envolver=True))
        self.capa.addWidget(f)

    def _apartado_7(self, ea: estado.EstadoApartado) -> None:
        if ea.bloques:
            return
        ident = derivados.identificacion(self.ctx.cat, self.ctx.datos, self.ctx.sigla, self.ctx.curso)
        f, capa = caja("curriculo")
        capa.addWidget(titulo_caja("Del catálogo", "horario del currículo"))
        capa.addWidget(tabla(["Curso", "Código", "Módulo del currículo", "Horas", "h/sem."],
                                       [[f"{m.curso}.º", m.codigo, m.nombre, str(m.horas), str(m.h_sem)]
                                        for m in ident.modulos], estirar=2, mono=(1,), derecha=(3, 4)))
        capa.addWidget(etiqueta("Falta la agrupación de los módulos que acuerde el equipo (anexo I, ap. 5, de la "
                                "guía): el apartado sale pendiente.", "estado-borrador", envolver=True))
        self.capa.addWidget(f)

    def _apartado_20(self, ea: estado.EstadoApartado) -> None:
        ident = derivados.identificacion(self.ctx.cat, self.ctx.datos, self.ctx.sigla, self.ctx.curso)
        f, capa = caja("curriculo")
        capa.addWidget(titulo_caja("Del catálogo", "las programaciones las genera la app Programaciones"))
        vistos, filas = set(), []
        for m in ident.modulos:
            if (m.codigo, m.nombre) not in vistos:
                vistos.add((m.codigo, m.nombre))
                filas.append([m.codigo, m.nombre, f"{m.curso}.º"])
        capa.addWidget(tabla(["Código", "Módulo profesional", "Curso"], filas, estirar=1, mono=(0,)))
        self.capa.addWidget(f)

    def sizeHint(self):  # noqa: N802
        return QSize(560, 600)

