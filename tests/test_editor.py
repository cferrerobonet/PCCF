"""El editor de los bloques como en Word (ADR-020), sin pantalla: lo guardado no cambia, la barra y los atajos, pegar
desde Word y copiar."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PyQt6.QtCore import QMimeData, Qt  # noqa: E402
from PyQt6.QtGui import QTextCursor  # noqa: E402

from pccf import texto  # noqa: E402
from pccf.texto import Parrafo  # noqa: E402

from .test_word import MD, PARRAFOS  # noqa: E402


@pytest.fixture
def editor(qtbot):
    from pccf.ui.editor import EditorTexto

    e = EditorTexto(MD)
    qtbot.addWidget(e)
    e.show()
    return e


def _ir(e, bloque: int, al_final: bool = True):
    c = QTextCursor(e.texto.document().findBlockByNumber(bloque))
    if al_final:
        c.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    e.texto.setTextCursor(c)
    e.texto.setFocus()


def test_lo_guardado_no_cambia(editor):
    assert editor.parrafos() == PARRAFOS
    assert texto.de_markdown(editor.markdown()) == PARRAFOS
    assert "**" not in editor.toPlainText() and "###" not in editor.toPlainText() and "](" not in editor.toPlainText()


def test_la_barra_cambia_la_clase_del_parrafo(editor):
    _ir(editor, 5)
    editor.b_subtitulo.click()
    assert editor.parrafos()[-1] == Parrafo("subtitulo", "Último párrafo.")
    editor.b_subtitulo.click()
    assert editor.parrafos()[-1] == Parrafo("parrafo", "Último párrafo.")    # sin la negrita del subtítulo
    editor.b_vinetas.click()
    assert editor.parrafos()[-1].clase == "vineta"
    editor.b_nota.click()
    assert editor.parrafos()[-1] == Parrafo("nota", "Último párrafo.")
    editor.b_nota.click()
    assert editor.parrafos()[-1] == Parrafo("parrafo", "Último párrafo.")


def test_negrita_y_enlace(editor, qtbot):
    _ir(editor, 5)
    c = editor.texto.textCursor()
    c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
    c.movePosition(QTextCursor.MoveOperation.NextWord, QTextCursor.MoveMode.KeepAnchor)
    editor.texto.setTextCursor(c)
    qtbot.keyClick(editor.texto, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
    assert editor.parrafos()[-1].texto == "**Último** párrafo."
    c = editor.texto.textCursor()
    c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
    c.movePosition(QTextCursor.MoveOperation.NextWord)
    c.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
    editor.texto.setTextCursor(c)
    editor.texto.poner_enlace("https://example.com/p")
    assert editor.parrafos()[-1].texto == "**Último** [párrafo.](https://example.com/p)"
    _ir(editor, 5)
    c = editor.texto.textCursor()
    c.movePosition(QTextCursor.MoveOperation.PreviousCharacter)
    editor.texto.setTextCursor(c)
    assert editor.texto.enlace_actual() == "https://example.com/p"
    editor.texto.poner_enlace("")   # dentro del enlace, sin selección: se quita entero
    assert editor.parrafos()[-1].texto == "**Último** párrafo."


def test_teclado_como_en_word(editor, qtbot):
    _ir(editor, 0)                                   # al final del subtítulo
    qtbot.keyClick(editor.texto, Qt.Key.Key_Return)
    qtbot.keyClicks(editor.texto, "- Nueva")         # «- » empieza una viñeta
    assert editor.parrafos()[1] == Parrafo("vineta", "Nueva")
    qtbot.keyClick(editor.texto, Qt.Key.Key_Return)
    qtbot.keyClick(editor.texto, Qt.Key.Key_Return)  # Intro en una viñeta vacía: fuera de la lista
    qtbot.keyClicks(editor.texto, "Normal")
    assert editor.parrafos()[1:3] == [Parrafo("vineta", "Nueva"), Parrafo("parrafo", "Normal")]


def test_pegar_desde_word(editor):
    html = ("<html><body><h2>Un título</h2>"
            "<p class=MsoListParagraph style='mso-list:l0 level1 lfo1'><![if !supportLists]>·<span> </span>"
            "<![endif]>Viñeta de <b>Word</b></p>"
            "<p><span style='font-family:Comic Sans MS;color:red'><i>Texto</i> con "
            "<a href='https://example.com/x'>enlace</a></span></p></body></html>")
    datos = QMimeData()
    datos.setHtml(html)
    _ir(editor, 5)
    editor.texto.insertFromMimeData(datos)
    assert editor.parrafos()[-3:] == [Parrafo("subtitulo", "Un título"), Parrafo("vineta", "Viñeta de **Word**"),
                                      Parrafo("parrafo", "Texto con [enlace](https://example.com/x)")]


def test_pegar_en_medio_de_un_parrafo_deja_el_resto_debajo(editor):
    from pccf.ui.editor import parrafos_de_texto

    _ir(editor, 5, al_final=False)
    c = editor.texto.textCursor()
    c.movePosition(QTextCursor.MoveOperation.NextWord)
    editor.texto.setTextCursor(c)
    editor.texto.insertar(parrafos_de_texto("- Uno\n- Dos"))
    assert editor.parrafos()[-4:] == [Parrafo("parrafo", "Último"), Parrafo("vineta", "Uno"),
                                      Parrafo("vineta", "Dos"), Parrafo("parrafo", "párrafo.")]


def test_copiar_da_html_limpio(editor):
    c = editor.texto.textCursor()
    c.select(QTextCursor.SelectionType.Document)
    editor.texto.setTextCursor(c)
    datos = editor.texto.createMimeDataFromSelection()
    assert "<h3>Organización del taller</h3>" in datos.html() and "<ul><li>" in datos.html()
    assert '<a href="https://example.com/norma">enlace</a>' in datos.html()
    assert "• Primera viñeta" in datos.text() and "**" not in datos.text()
