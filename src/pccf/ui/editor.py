"""Editor de los bloques como en Word (ADR-020): el equipo no ve Markdown. Ofrece solo lo que el documento del PCCF
sabe escribir: párrafos, subtítulos, viñetas, negrita, enlaces y notas internas (que no salen en el PCCF). Lo guardado
no cambia: el Markdown del bloque (`pccf.texto`).

Parte del editor de Programaciones (su ADR-045):
- Barra pequeña: Subtítulo, Negrita, Viñetas, Enlace y Nota interna; atajos de Word: ⌘B (Ctrl+B) negrita, ⌘K (Ctrl+K)
  enlace, Intro en una viñeta vacía para salir de la lista, Retroceso al principio para quitar la viñeta y «- » al
  principio de un párrafo para empezar una. Intro al final de un subtítulo o de una nota sigue con un párrafo normal.
- Al pegar desde Word (o desde cualquier sitio) se quedan los títulos, las viñetas, la negrita y los enlaces; el resto
  (letra, tamaño, color, cursiva…) se descarta. Al copiar, sale HTML limpio.
"""
from __future__ import annotations

import html
import re

from PyQt6.QtCore import QMimeData, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextListFormat,
)
from PyQt6.QtWidgets import QHBoxLayout, QInputDialog, QLineEdit, QSizePolicy, QTextEdit, QVBoxLayout, QWidget

from pccf import texto as tx
from pccf.texto import Parrafo, Trozo

from . import estilo
from .componentes import atajo, boton

#: Propiedad del bloque de Qt con su clase cuando no se deduce del formato (la nota interna)
CLASE = QTextFormat.Property.UserProperty + 1
#: Marca invisible con el nivel de una viñeta de Word («mso-list: l0 level1»), que el HTML de Qt no conserva
MARCA = "⁣"
RE_MSO_PARRAFO = re.compile(r"(<p\b[^>]*mso-list:\s*l\d+\s+level(\d)[^>]*>)", re.I)
RE_MSO_VINETA = re.compile(r"<!(?:--)?\[if !supportLists\](?:--)?>.*?<!(?:--)?\[endif\](?:--)?>", re.I | re.S)
RE_VINETA_ESCRITA = re.compile(r"^[•·▪◦‣]\s+")
RE_ENLACE_SUELTO = re.compile(r"^(https?://\S+|www\.\S+)$")


# ---------------------------------------------------------------------------------------------------------------------
# Párrafos ↔ documento de Qt
# ---------------------------------------------------------------------------------------------------------------------
def _negrita(fmt: QTextCharFormat) -> bool:
    return fmt.fontWeight() >= QFont.Weight.DemiBold


def clase_de_bloque(bloque) -> str:
    if bloque.blockFormat().property(CLASE) == "nota":
        return "nota"
    if bloque.blockFormat().headingLevel() > 0:
        return "subtitulo"
    if bloque.textList() is not None:
        return "vineta"
    return "parrafo"


def _texto_de_bloque(bloque, negrita: bool = True) -> str:
    ts: list[Trozo] = []
    it = bloque.begin()
    while not it.atEnd():
        f = it.fragment()
        if f.isValid():
            fmt = f.charFormat()
            url = fmt.anchorHref() if fmt.isAnchor() and re.match(r"https?://", fmt.anchorHref() or "") else None
            ts.append(Trozo(f.text().replace("￼", ""), _negrita(fmt), url))
        it += 1
    return tx.de_trozos(ts, negrita=negrita)


def parrafos_de_documento(doc: QTextDocument, pegado: bool = False) -> list[Parrafo]:
    """Los párrafos del documento. `pegado`: también las viñetas de Word (su marca) y las que llegan escritas
    («• texto»)."""
    out = []
    bloque = doc.begin()
    while bloque.isValid():
        clase = clase_de_bloque(bloque)
        t = _texto_de_bloque(bloque, negrita=clase != "subtitulo")
        if pegado:
            m = re.match(rf"^(?:\*\*)?{MARCA}\d{MARCA}(?:\*\*)?\s*", t)
            if m:
                clase, t = "vineta", t[m.end():]
            elif clase == "parrafo" and RE_VINETA_ESCRITA.match(t):
                clase, t = "vineta", RE_VINETA_ESCRITA.sub("", t)
        t = tx.limpio(t.replace(MARCA, ""))
        if tx.limpio(t.replace("*", "")):
            out.append(Parrafo(clase, t))
        bloque = bloque.next()
    return out


def html_de_word(h: str) -> str:
    """El HTML que pone Word en el portapapeles, con cada viñeta marcada y sin su «·» dibujado."""
    h = RE_MSO_PARRAFO.sub(lambda m: f"{m.group(1)}{MARCA}{m.group(2)}{MARCA}", h)
    return RE_MSO_VINETA.sub("", h)


def parrafos_de_html(h: str) -> list[Parrafo]:
    doc = QTextDocument()
    doc.setHtml(html_de_word(h))
    return parrafos_de_documento(doc, pegado=True)


def parrafos_de_texto(t: str) -> list[Parrafo]:
    """Texto sin formato: una línea, un párrafo; «- » o «• » al principio, viñeta."""
    out = []
    for linea in t.replace("\r\n", "\n").split("\n"):
        s = linea.strip()
        if not s:
            continue
        m = re.match(r"^[-•·*]\s+(.*)$", s)
        out.append(Parrafo("vineta", tx.limpio(m.group(1))) if m else Parrafo("parrafo", tx.limpio(s)))
    return [p for p in out if p.texto]


def _formato_lista() -> QTextListFormat:
    f = QTextListFormat()
    f.setStyle(QTextListFormat.Style.ListDisc)
    f.setIndent(1)
    return f


def formato_caracter(negrita: bool = False, url: str | None = None, subtitulo: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setFontWeight(QFont.Weight.Bold if negrita or subtitulo else QFont.Weight.Normal)
    f.setProperty(QTextFormat.Property.FontSizeAdjustment, 1 if subtitulo else 0)
    f.setFontItalic(False)
    f.setAnchor(bool(url))
    f.setAnchorHref(url or "")
    f.setFontUnderline(bool(url))
    if url:
        f.setForeground(QColor(estilo.T["accent"]))
    else:
        f.clearForeground()
    return f


def formato_bloque(clase: str) -> QTextBlockFormat:
    f = QTextBlockFormat()
    f.setHeadingLevel(3 if clase == "subtitulo" else 0)
    f.setTopMargin(8 if clase == "subtitulo" else 0)
    f.setBottomMargin(4)
    if clase == "nota":
        f.setProperty(CLASE, "nota")
        f.setBackground(QColor(estilo.T["warn_soft"]))
        f.setLeftMargin(6)
        f.setRightMargin(6)
    return f


def _escribir(cursor: QTextCursor, texto: str, subtitulo: bool = False, nota: bool = False) -> None:
    for t in tx.trozos(texto):
        f = formato_caracter(t.negrita, t.url, subtitulo)
        if nota:
            f.setFontItalic(True)
        cursor.insertText(t.texto, f)


def insertar_parrafos(cursor: QTextCursor, parrafos: list[Parrafo], primero_nuevo: bool) -> None:
    """Escribe los párrafos donde está el cursor, cada uno con su formato. Con `primero_nuevo`, el primero empieza un
    bloque; si no, ocupa el bloque del cursor (que debe estar vacío)."""
    lista = None
    for i, p in enumerate(parrafos):
        if i or primero_nuevo:
            cursor.insertBlock(formato_bloque(p.clase), formato_caracter())
        else:
            if cursor.block().textList() is not None:
                cursor.block().textList().remove(cursor.block())
            cursor.setBlockFormat(formato_bloque(p.clase))
        if p.clase == "vineta":
            if lista is None:
                lista = cursor.createList(_formato_lista())
            else:
                lista.add(cursor.block())
        else:
            lista = None
        _escribir(cursor, p.texto, subtitulo=p.clase == "subtitulo", nota=p.clase == "nota")


def poner_parrafos(doc: QTextDocument, parrafos: list[Parrafo]) -> None:
    """El documento con estos párrafos, cada uno con su formato."""
    doc.clear()
    insertar_parrafos(QTextCursor(doc), list(parrafos or []), primero_nuevo=False)


def html_de_parrafos(parrafos: list[Parrafo]) -> str:
    """HTML limpio para el portapapeles (Word lo pega con sus títulos, viñetas, negrita y enlaces)."""
    out, en_lista = [], False
    for p in parrafos:
        if (p.clase == "vineta") != en_lista:
            out.append("<ul>" if not en_lista else "</ul>")
            en_lista = not en_lista
        partes = "".join(f'<a href="{html.escape(t.url)}">{html.escape(t.texto)}</a>' if t.url else
                         f"<b>{html.escape(t.texto)}</b>" if t.negrita else html.escape(t.texto)
                         for t in tx.trozos(p.texto))
        etiqueta = {"vineta": "li", "subtitulo": "h3"}.get(p.clase, "p")
        out.append(f"<{etiqueta}>{'<i>' + partes + '</i>' if p.clase == 'nota' else partes}</{etiqueta}>")
    if en_lista:
        out.append("</ul>")
    return "<html><body>" + "".join(out) + "</body></html>"


def texto_de_parrafos(parrafos: list[Parrafo]) -> str:
    return "\n".join(("• " if p.clase == "vineta" else "") + tx.sin_marcas(p.texto) for p in parrafos)


# ---------------------------------------------------------------------------------------------------------------------
# El cuadro de texto
# ---------------------------------------------------------------------------------------------------------------------
class _Texto(QTextEdit):
    """Lo que se pega se queda en títulos, viñetas, negrita y enlaces; crece con su contenido (la zona central es la
    que se desplaza)."""

    foco = pyqtSignal()
    pedir_enlace = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("editor")
        self.setAcceptRichText(True)
        self.setTabChangesFocus(True)
        self.document().setDocumentMargin(4)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.document().documentLayout().documentSizeChanged.connect(self._alto)
        self._alto()

    def _alto(self, *_) -> None:
        self.setFixedHeight(max(120, int(self.document().size().height()) + 26))

    def resizeEvent(self, e) -> None:  # noqa: N802
        super().resizeEvent(e)
        self._alto()

    def focusInEvent(self, e) -> None:  # noqa: N802
        super().focusInEvent(e)
        self.foco.emit()

    def focusOutEvent(self, e) -> None:  # noqa: N802
        super().focusOutEvent(e)
        self.foco.emit()

    # -- pegar y copiar ------------------------------------------------------------------------------------------------
    def insertFromMimeData(self, origen: QMimeData) -> None:  # noqa: N802
        if origen.hasHtml():
            ps = parrafos_de_html(origen.html())
        elif origen.hasText():
            ps = parrafos_de_texto(origen.text())
        else:
            return
        self.insertar(ps)

    def insertar(self, parrafos: list[Parrafo]) -> None:
        """Lo pegado: un trozo de texto va dentro del párrafo; varios párrafos, cada uno en el suyo con su formato
        (el texto que hubiera tras el cursor queda en su propio párrafo, debajo)."""
        if not parrafos:
            return
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        if len(parrafos) == 1 and parrafos[0].clase == "parrafo":
            _escribir(cursor, parrafos[0].texto, subtitulo=clase_de_bloque(cursor.block()) == "subtitulo")
        else:
            if cursor.block().text() and not cursor.atBlockEnd():
                en_inicio = cursor.atBlockStart()
                cursor.insertBlock(cursor.blockFormat(), cursor.charFormat())
                cursor.movePosition(QTextCursor.MoveOperation.PreviousBlock)
                if not en_inicio:
                    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            insertar_parrafos(cursor, parrafos, primero_nuevo=bool(cursor.block().text()))
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def createMimeDataFromSelection(self) -> QMimeData:  # noqa: N802
        temp = QTextDocument()
        QTextCursor(temp).insertFragment(self.textCursor().selection())
        ps = parrafos_de_documento(temp)
        datos = QMimeData()
        datos.setHtml(html_de_parrafos(ps))
        datos.setText(texto_de_parrafos(ps))
        return datos

    # -- teclado como en Word ------------------------------------------------------------------------------------------
    def keyPressEvent(self, e) -> None:  # noqa: N802
        cursor = self.textCursor()
        lista = cursor.currentList()
        if e.matches(QKeySequence.StandardKey.Bold):
            self.negrita()
            return
        if e.key() == Qt.Key.Key_K and e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.pedir_enlace.emit()
            return
        intro = e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        if intro and lista is not None and not cursor.block().text():
            self.poner_clase("parrafo")   # Intro en una viñeta vacía: fuera de la lista
            return
        if e.key() == Qt.Key.Key_Backspace and lista is not None and cursor.atBlockStart() and not cursor.hasSelection():
            self.poner_clase("parrafo")
            return
        if intro and clase_de_bloque(cursor.block()) in ("subtitulo", "nota") and cursor.atBlockEnd():
            cursor.insertBlock(formato_bloque("parrafo"), formato_caracter())   # tras un subtítulo, texto normal
            self.setTextCursor(cursor)
            self.setCurrentCharFormat(formato_caracter())
            return
        super().keyPressEvent(e)
        if e.text() == " " and lista is None and clase_de_bloque(self.textCursor().block()) == "parrafo":
            antes = self.textCursor().block().text()[:self.textCursor().positionInBlock()]
            if antes in ("- ", "* ", "• "):   # «- » al principio: empieza una viñeta, como en Word
                c = self.textCursor()
                c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                c.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, 2)
                c.removeSelectedText()
                self.poner_clase("vineta")

    # -- órdenes de la barra -------------------------------------------------------------------------------------------
    def negrita(self) -> None:
        if clase_de_bloque(self.textCursor().block()) == "subtitulo":
            return   # el subtítulo ya va en negrita
        f = QTextCharFormat()
        f.setFontWeight(QFont.Weight.Normal if _negrita(self.currentCharFormat()) else QFont.Weight.Bold)
        self.mergeCurrentCharFormat(f)

    def poner_clase(self, clase: str) -> None:
        """Convierte los párrafos de la selección (o el del cursor) en párrafo, subtítulo, viñeta o nota."""
        cursor = self.textCursor()
        inicio, fin = sorted((cursor.anchor(), cursor.position()))
        c = QTextCursor(self.document())
        c.setPosition(inicio)
        c.beginEditBlock()
        bloques = []
        b = c.block()
        while b.isValid() and b.position() <= fin:
            bloques.append(b)
            b = b.next()
        for b in bloques:
            era_subtitulo = clase_de_bloque(b) == "subtitulo"
            c.setPosition(b.position())
            if b.textList() is not None:
                b.textList().remove(b)
            c.setBlockFormat(formato_bloque(clase))
            c.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            f = QTextCharFormat()
            f.setProperty(QTextFormat.Property.FontSizeAdjustment, 1 if clase == "subtitulo" else 0)
            f.setFontItalic(clase == "nota")
            if clase == "subtitulo":
                f.setFontWeight(QFont.Weight.Bold)
            elif era_subtitulo:   # deja de ser subtítulo: su negrita era la del subtítulo
                f.setFontWeight(QFont.Weight.Normal)
            c.mergeCharFormat(f)
        if clase == "vineta":
            c.setPosition(bloques[0].position())
            lista = c.createList(_formato_lista())
            for b in bloques[1:]:
                lista.add(b)
        c.endEditBlock()
        nuevo = QTextCharFormat()
        nuevo.setProperty(QTextFormat.Property.FontSizeAdjustment, 1 if clase == "subtitulo" else 0)
        nuevo.setFontItalic(clase == "nota")
        nuevo.setFontWeight(QFont.Weight.Bold if clase == "subtitulo" else QFont.Weight.Normal)
        self.mergeCurrentCharFormat(nuevo)

    def enlace_actual(self) -> str:
        f = self.textCursor().charFormat()
        return f.anchorHref() if f.isAnchor() else ""

    def poner_enlace(self, url: str) -> None:
        """Enlaza la selección (o la palabra del cursor) con `url`; con `url` vacía, quita el enlace."""
        cursor = self.textCursor()
        if not cursor.hasSelection():
            if self.enlace_actual():   # dentro de un enlace: todo el enlace
                href = self.enlace_actual()
                inicio = fin = cursor.position()
                bloque = cursor.block()
                it = bloque.begin()
                while not it.atEnd():
                    fr = it.fragment()
                    if fr.charFormat().anchorHref() == href and fr.position() <= cursor.position() <= \
                            fr.position() + fr.length():
                        inicio, fin = fr.position(), fr.position() + fr.length()
                    it += 1
                cursor.setPosition(inicio)
                cursor.setPosition(fin, QTextCursor.MoveMode.KeepAnchor)
            else:
                cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        if not cursor.hasSelection():
            if url:   # sin texto: se escribe la dirección enlazada
                cursor.insertText(url, formato_caracter(url=url))
                self.setCurrentCharFormat(formato_caracter())
            return
        subtitulo = clase_de_bloque(cursor.block()) == "subtitulo"
        f = QTextCharFormat()
        f.setAnchor(bool(url))
        f.setAnchorHref(url)
        f.setFontUnderline(bool(url))
        if url:
            f.setForeground(QColor(estilo.T["accent"]))
        else:
            f.clearForeground()
            f.setFontWeight(QFont.Weight.Bold if subtitulo else QFont.Weight.Normal)
        cursor.mergeCharFormat(f)
        if not url:   # mergeCharFormat no quita el color: se limpia del todo
            fmt = formato_caracter(subtitulo=subtitulo)
            cursor.setCharFormat(fmt)
        fuera = QTextCursor(cursor)
        fuera.clearSelection()
        self.setTextCursor(fuera)
        self.setCurrentCharFormat(formato_caracter(subtitulo=subtitulo))


# ---------------------------------------------------------------------------------------------------------------------
# El editor con su barra
# ---------------------------------------------------------------------------------------------------------------------
class EditorTexto(QWidget):
    """El texto de un bloque como en Word, con su barra pequeña encima. `markdown()` da lo que se guarda."""

    cambiado = pyqtSignal()

    def __init__(self, md: str = "", marcador: str = "Escribe aquí, como en Word…"):
        super().__init__()
        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.setSpacing(6)
        barra = QHBoxLayout()
        barra.setSpacing(4)
        self.texto = _Texto()
        self.texto.setPlaceholderText(marcador)
        self.texto.setToolTip("Escribe como en Word. Lo que pegues de Word conserva los títulos, las viñetas, la "
                              "negrita y los enlaces.")
        self.b_subtitulo = boton("Subtítulo", chip=True)
        self.b_subtitulo.setToolTip("Subtítulo del apartado: en el PCCF sale numerado (n.1, n.2…)")
        self.b_negrita = boton("N", chip=True)
        self.b_negrita.setToolTip(f"Negrita ({atajo('B')})")
        f = self.b_negrita.font()
        f.setBold(True)
        self.b_negrita.setFont(f)
        self.b_vinetas = boton("• Viñetas", chip=True)
        self.b_vinetas.setToolTip("Viñetas (o escribe «- » al principio del párrafo)")
        self.b_enlace = boton("Enlace…", chip=True)
        self.b_enlace.setToolTip(f"Enlazar el texto elegido con una página web ({atajo('K')})")
        self.b_nota = boton("Nota interna", chip=True)
        self.b_nota.setToolTip("Nota para el equipo (sombreada): se guarda con el bloque pero no sale en el PCCF")
        for b in (self.b_subtitulo, self.b_negrita, self.b_vinetas, self.b_enlace, self.b_nota):
            b.setCheckable(b is not self.b_enlace)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # el cursor sigue en el texto
            barra.addWidget(b)
        barra.addStretch(1)
        capa.addLayout(barra)
        capa.addWidget(self.texto)
        self.b_subtitulo.clicked.connect(lambda si: self.texto.poner_clase("subtitulo" if si else "parrafo"))
        self.b_negrita.clicked.connect(lambda: self.texto.negrita())
        self.b_vinetas.clicked.connect(lambda si: self.texto.poner_clase("vineta" if si else "parrafo"))
        self.b_nota.clicked.connect(lambda si: self.texto.poner_clase("nota" if si else "parrafo"))
        self.b_enlace.clicked.connect(self.pedir_enlace)
        self.texto.pedir_enlace.connect(self.pedir_enlace)
        self.texto.cursorPositionChanged.connect(self._estado)
        self.texto.foco.connect(self._estado)
        self.texto.currentCharFormatChanged.connect(lambda _f: self._estado())
        self.texto.textChanged.connect(self.cambiado)
        self.texto.textChanged.connect(self._estado)
        self.poner(md)

    def _estado(self) -> None:
        activo = self.texto.hasFocus()
        clase = clase_de_bloque(self.texto.textCursor().block())
        self.b_subtitulo.setChecked(activo and clase == "subtitulo")
        self.b_vinetas.setChecked(activo and clase == "vineta")
        self.b_nota.setChecked(activo and clase == "nota")
        self.b_negrita.setChecked(activo and clase != "subtitulo" and _negrita(self.texto.currentCharFormat()))
        self.b_negrita.setEnabled(clase != "subtitulo")

    def pedir_enlace(self) -> None:
        actual = self.texto.enlace_actual()
        url, ok = QInputDialog.getText(self, "Enlace", "Dirección de la página (vacía para quitar el enlace):",
                                       QLineEdit.EchoMode.Normal, actual or "https://")
        if not ok:
            return
        url = url.strip()
        if url in ("https://", "http://"):
            url = ""
        if url and not re.match(r"https?://", url):
            url = "https://" + url
        self.texto.poner_enlace(url)
        self.texto.setFocus()

    # -- datos ---------------------------------------------------------------------------------------------------------
    def poner(self, md: str) -> None:
        self.texto.blockSignals(True)
        poner_parrafos(self.texto.document(), tx.de_markdown(md))
        self.texto.document().clearUndoRedoStacks()
        self.texto.blockSignals(False)
        self.texto._alto()
        self._estado()

    def parrafos(self) -> list[Parrafo]:
        return parrafos_de_documento(self.texto.document())

    def markdown(self) -> str:
        return tx.a_markdown(self.parrafos())

    def setPlainText(self, t: str) -> None:  # noqa: N802
        """Texto escrito como si lo tecleara alguien (una línea, un párrafo; «- », viñeta)."""
        poner_parrafos(self.texto.document(), parrafos_de_texto(t))

    def toPlainText(self) -> str:  # noqa: N802
        return self.texto.toPlainText()
