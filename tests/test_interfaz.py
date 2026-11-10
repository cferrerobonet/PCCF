"""La interfaz sin pantalla (pytest-qt), con el catálogo y la carpeta de datos ficticios: ventana, los 20 apartados,
bloques (guardar y confirmar), vigía, «Nuevo curso» y QtPdf. Los ajustes de Qt van a un archivo temporal."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PyQt6.QtCore import QSettings, Qt  # noqa: E402
from PyQt6.QtWidgets import QLabel, QMessageBox  # noqa: E402

from pccf import bloques, cursos  # noqa: E402

from .conftest import CURSO  # noqa: E402


@pytest.fixture
def ventana(qtbot, cat, datos, tmp_path, monkeypatch):
    from pccf.ui import contexto, estilo, ventana

    ini = str(tmp_path / "ajustes.ini")
    monkeypatch.setattr(contexto, "ajustes", lambda: QSettings(ini, QSettings.Format.IniFormat))
    monkeypatch.setattr(ventana, "ajustes", lambda: QSettings(ini, QSettings.Format.IniFormat))
    from PyQt6.QtWidgets import QApplication

    estilo.cargar_fuentes()
    estilo.aplicar(QApplication.instance())
    ctx = contexto.Contexto(cat, datos)
    v = ventana.VentanaPrincipal(ctx)
    v.resize(1240, 760)
    qtbot.addWidget(v)
    v.show()
    return v


def _textos(w) -> str:
    return " ".join(x.text() for x in w.findChildren(QLabel) if x.isVisible())


def test_abre_con_el_ciclo_y_sus_20_apartados(ventana):
    assert ventana.ctx.sigla == "PRU" and ventana.ctx.curso == CURSO
    assert ventana.izquierda.lista.count() == 20
    assert ventana.boton_curso.text() == f"PRU · {CURSO}"
    assert ventana.derecha.progreso.value() == 5 and ventana.derecha.progreso.maximum() == 20   # 4 confirmados y 1 listo


def test_todos_los_apartados_se_ven_y_caben(ventana, qtbot):
    for n in range(1, 21):
        ventana.izquierda.ir(n)
        qtbot.wait(5)
        assert ventana.centro.n == n
        assert "No se puede enseñar" not in _textos(ventana.centro)
        zona = ventana.centro.zona
        assert zona.widget().minimumSizeHint().width() <= zona.viewport().width(), f"el apartado {n} no cabe"


def test_editar_y_confirmar_un_bloque(ventana, qtbot, datos):
    ventana.izquierda.ir(16)
    qtbot.wait(5)
    [tarjeta] = ventana.centro.tarjetas
    tarjeta.editor.setPlainText("Texto cambiado desde la interfaz.")
    tarjeta.guardar()
    b = datos.bloques("PRU", CURSO, 16)[0]
    assert b.cuerpo == "Texto cambiado desde la interfaz." and b.estado == "borrador"
    tarjeta.boton_confirmar.click()
    qtbot.wait(5)
    assert datos.bloques("PRU", CURSO, 16)[0].confirmado
    assert ventana.ctx.estado.de(16).estado == "confirmado"
    assert ventana.centro.n == 16 and not hasattr(ventana.centro.tarjetas[0], "boton_confirmar")


def test_cambiar_de_apartado_guarda_lo_escrito(ventana, qtbot, datos):
    ventana.izquierda.ir(16)
    qtbot.wait(5)
    ventana.centro.tarjetas[0].editor.setPlainText("Escrito y sin esperar.")
    ventana.izquierda.ir(2)
    qtbot.wait(5)
    assert datos.bloques("PRU", CURSO, 16)[0].cuerpo == "Escrito y sin esperar."


def test_anadir_un_bloque(ventana, qtbot, datos, monkeypatch):
    from pccf.ui import dialogos

    def aceptar(self):
        self.nombre.setText("metodologia")
        self.autor.setText("Equipo ficticio")
        self.crear()
        return 1

    monkeypatch.setattr(dialogos.DialogoNuevoBloque, "exec", aceptar)
    ventana.izquierda.ir(6)
    ventana.nuevo_bloque(6)
    qtbot.wait(5)
    assert [b.ruta.name for b in datos.bloques("PRU", CURSO, 6)] == ["metodologia.md"]
    assert ventana.ctx.estado.de(6).estado == "borrador"
    assert len(ventana.centro.tarjetas) == 1


def test_vigia_y_marcar_como_revisado(ventana, qtbot, datos, monkeypatch):
    from pccf.ui.dialogos import DialogoVigia

    d = DialogoVigia(ventana.ctx, ventana)
    qtbot.addWidget(d)
    assert "primera revisión" in _textos(d) or "Sin revisión" in _textos(d) or d.isHidden()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    d.marcar()
    assert d.revisado
    assert (datos.carpeta / "cursos" / CURSO / "PRU" / "vigia.yaml").is_file()
    ventana.ctx.recalcular()
    assert ventana.ctx.informe.anterior is not None
    assert ventana.boton_vigia.text() == "§ Vigía · al día"


def test_nuevo_curso_desde_la_ventana(ventana, qtbot, datos, monkeypatch):
    from pccf.ui.dialogos import DialogoNuevoCurso

    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    d = DialogoNuevoCurso(ventana.ctx, ventana)
    qtbot.addWidget(d)
    nuevo = cursos.siguiente(CURSO)
    assert d.destino.text() == nuevo and d.crear.text() == f"Crear {nuevo}"
    d.crear_curso()
    assert d.creado == nuevo
    ventana.ctx.elegir("PRU", nuevo)
    assert ventana.boton_curso.text() == f"PRU · {nuevo}"
    assert ventana.ctx.estado.de(1).estado == "heredado"
    # y ahora se pueden comparar los dos cursos
    d = DialogoNuevoCurso(ventana.ctx, ventana)
    qtbot.addWidget(d)
    d.comparar()
    assert d.tabla.rowCount() == 20


def test_selector_de_ciclo_busca(ventana, qtbot):
    ventana.izquierda.abrir_selector()
    s = ventana.izquierda._selector
    s.buscar.setText("pru")
    elegibles = [s.lista.item(i) for i in range(s.lista.count()) if s.lista.item(i).data(256)]
    assert len(elegibles) == 1
    s.buscar.setText("nada que case")
    assert not any(s.lista.item(i).data(256) for i in range(s.lista.count()))
    s.close()


def test_bloque_mal_escrito_no_tumba_la_ventana(cat, datos, carpeta, qtbot, tmp_path, monkeypatch):
    from pccf.ui import contexto

    monkeypatch.setattr(contexto, "ajustes",
                        lambda: QSettings(str(tmp_path / "a.ini"), QSettings.Format.IniFormat))
    (carpeta / "centro" / "roto.md").write_text("---\ntipo: nada\n---\n", encoding="utf-8")
    ctx = contexto.Contexto(cat, datos)
    assert ctx.estado is None and "roto.md" in ctx.error
    with pytest.raises(bloques.BloqueNoValido):
        datos.bloques("PRU", CURSO)


def test_qtpdf_disponible():
    from pccf.ui.vista_previa import comprobar_qtpdf

    assert "1 página" in comprobar_qtpdf()


def test_ajustes_con_menu_lateral_y_cambios_al_momento(ventana, qtbot, tmp_path, datos, monkeypatch):
    from pccf.ui import actualizar
    from pccf.ui.ajustes import APARTADOS, DialogoAjustes

    d = DialogoAjustes(ventana)
    qtbot.addWidget(d)
    assert [d.nav.item(i).text() for i in range(d.nav.count())] == APARTADOS
    # carpeta de datos: una que no existe no se guarda; una buena, sí, y la ventana la recargará al cerrar
    assert not d.elegir_datos(str(tmp_path / "no-existe")) and not d.carpetas_cambiadas
    assert d.estado_datos.property("rol") == "error-texto" and d.estado_datos.text().startswith("✕")
    assert d.elegir_datos(str(datos.carpeta)) and d.carpetas_cambiadas
    # catálogo: sin normativa.yaml no vale; «Volver al automático» quita el fijado
    assert not d.elegir_catalogo(str(tmp_path))
    assert d.elegir_catalogo(str(ventana.ctx.cat.carpeta)) and d.boton_automatico.isEnabled()
    d.catalogo_automatico()
    assert d.catalogo.text() == "" and not d.boton_automatico.isEnabled()
    # documento: el correo se valida y se guarda al momento; el programa del PDF, al elegirlo
    assert not d.poner_correo("no es un correo")
    assert d.poner_correo("departamento@example.com")
    d.motor.setCurrentIndex(d.motor.findData("libreoffice"))
    from pccf.ui.contexto import ajustes

    assert ajustes().value("correo_pie", "", str) == "departamento@example.com"
    assert ajustes().value("motor_pdf", "", str) == "libreoffice"
    # versión: «Buscar actualizaciones» avisa también si está al día
    llamadas = []
    monkeypatch.setattr(actualizar, "buscar_actualizaciones", lambda padre, avisar_si_al_dia, al_encontrar:
                        llamadas.append(avisar_si_al_dia))
    d.ir("Versión y catálogo")
    d.boton_buscar.click()
    assert llamadas == [True]
    assert not d.boton_comprobar.isEnabled()   # copia de desarrollo: el catálogo publicado no se comprueba


def test_barra_lateral_separa_lo_completo_de_lo_que_falta(ventana, qtbot):
    """ADR-024: cada fila dice su avance y los filtros dejan ver solo lo que falta o solo lo completo."""
    from pccf.ui.apartados import FilaApartado

    z = ventana.izquierda
    filas = {z.lista.item(i).data(Qt.ItemDataRole.UserRole): z.lista.itemWidget(z.lista.item(i))
             for i in range(z.lista.count())}
    assert isinstance(filas[16], FilaApartado) and filas[16].avance == "listo"
    assert filas[16].estado.text().startswith("◆ Listo")
    assert filas[3].avance == "vivo" and filas[3].estado.text() == "● Sin contenido"
    assert filas[20].estado.text() == "✓ Confirmado"
    z.filtrar("vivo")
    visibles = [z.lista.item(i).data(Qt.ItemDataRole.UserRole) for i in range(z.lista.count())
                if not z.lista.item(i).isHidden()]
    assert 16 not in visibles and 20 not in visibles and 3 in visibles
    z.filtrar("listo")
    visibles = [z.lista.item(i).data(Qt.ItemDataRole.UserRole) for i in range(z.lista.count())
                if not z.lista.item(i).isHidden()]
    assert sorted(visibles) == [1, 2, 4, 16, 20]
    z.ir(3)   # pedir uno que el filtro esconde: vuelven a verse todos
    assert z.filtro == "todos" and not any(z.lista.item(i).isHidden() for i in range(z.lista.count()))


def test_error_aviso_consejo_y_por_completar_se_distinguen():
    """ADR-025: cada significado con su color, separados al menos 25° de tono en claro y en oscuro; el oro, solo para la
    marca, no se usa en avisos ni en lo que falta."""
    import colorsys

    from pccf.ui import estilo

    def tono(h: str) -> float:
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
        return colorsys.rgb_to_hls(r, g, b)[0] * 360

    for paleta in (estilo.CLARO, estilo.OSCURO):
        claves = ["danger", "warn", "info", "pend", "accent"]
        for i, a in enumerate(claves):
            for b in claves[i + 1:]:
                d = abs(tono(paleta[a]) - tono(paleta[b]))
                assert min(d, 360 - d) >= 25, f"{a} y {b} se parecen demasiado"
    hoja = estilo.hoja(estilo.CLARO) if hasattr(estilo, "hoja") else ""
    if hoja:
        for regla in hoja.splitlines():
            if "aviso" in regla or 'avance="vivo"' in regla or "error" in regla:
                assert estilo.CLARO["gold"] not in regla, regla


def test_barras_laterales_mas_anchas_y_que_crecen(ventana, qtbot):
    """ADR-026: cada zona lateral, una cuarta parte de la ventana entre 330 y 400 px; el centro sigue cabiendo."""
    from pccf.ui.ventana import ancho_lateral

    assert ancho_lateral(1240) == 330 and ancho_lateral(1440) == 360 and ancho_lateral(2000) == 400
    ventana.resize(1240, 760)
    qtbot.wait(10)
    assert ventana.izquierda.width() == 330 and ventana.derecha.width() == 330
    ventana.resize(1800, 900)
    qtbot.wait(10)
    assert ventana.izquierda.width() == 400 and ventana.derecha.width() == 400
