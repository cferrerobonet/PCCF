"""Ventana principal (maqueta v0, aprobada el 2026-11-03): barra superior y tres zonas, apartados (280 px) · apartado
elegido (flexible) · estado, vista previa y exportar (290 px), en una ventana de 1100 × 700.

Barra: «PCCF · Formación Profesional», catálogo, vigía (dorado si ha visto cambios), ciclo y curso, «Nuevo curso…» y
«Ajustes». La vista previa y exportar trabajan en una `Tarea` (fuera de la interfaz) con la ventana de espera.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from PyQt6.QtCore import QSize, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QFont, QImage, QKeySequence, QPixmap
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMenu, QMessageBox, QVBoxLayout, QWidget

from pccf import __version__, documento, pdf

from . import estilo
from .apartado import VistaApartado
from .apartados import ZonaApartados
from .componentes import AvisoFlotante, Tarea, boton, etiqueta, refrescar_estilo, separador_vertical
from .contexto import ajustes
from .dialogos import DialogoAjustes, DialogoEspera, DialogoNuevoBloque, DialogoNuevoCurso, DialogoVigia
from .resumen import ZonaResumen
from .vista_previa import DialogoVistaPrevia

logger = logging.getLogger(__name__)
NOMBRE_APP = "PCCF"


class VentanaPrincipal(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._tarea: Tarea | None = None
        self._espera: DialogoEspera | None = None
        self.setWindowTitle(NOMBRE_APP)
        self.resize(1100, 700)
        self.setMinimumSize(1000, 620)
        raiz = QWidget()
        raiz.setObjectName("raiz")
        self.setCentralWidget(raiz)
        vertical = QVBoxLayout(raiz)
        vertical.setContentsMargins(0, 0, 0, 0)
        vertical.setSpacing(0)
        vertical.addWidget(self._barra())
        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(0)
        self.izquierda = ZonaApartados(ctx)
        self.centro = VistaApartado(ctx)
        self.derecha = ZonaResumen(ctx)
        cuerpo.addWidget(self.izquierda)
        cuerpo.addWidget(separador_vertical())
        cuerpo.addWidget(self.centro, 1)
        cuerpo.addWidget(separador_vertical())
        cuerpo.addWidget(self.derecha)
        vertical.addLayout(cuerpo, 1)
        self.aviso = AvisoFlotante(raiz)
        self._menu()

        self.izquierda.pedir_apartado.connect(self.centro.mostrar)
        self.derecha.pedir_apartado.connect(self.izquierda.ir)
        self.derecha.pedir_vigia.connect(self.abrir_vigia)
        self.derecha.pedir_vista_previa.connect(self.vista_previa)
        self.derecha.pedir_exportar.connect(self.exportar)
        self.centro.pedir_vigia.connect(self.abrir_vigia)
        self.centro.repintar.connect(self._repintar_todo)
        self.centro.estados_cambiados.connect(self._repintar_estados)
        self.centro.pedir_nuevo_bloque.connect(self.nuevo_bloque)
        self.centro.pedir_importar.connect(self.importar_bloque)
        ctx.cambiado.connect(self.recargar)
        self.recargar()

    # -- construcción ------------------------------------------------------------------------------------------------
    def _barra(self) -> QWidget:
        barra = QWidget()
        barra.setObjectName("barra")
        barra.setStyleSheet(f"#barra {{ background: {estilo.T['surface2']}; border-bottom: 1px solid {estilo.T['line']}; }}")
        fila = QHBoxLayout(barra)
        fila.setContentsMargins(16, 9, 12, 9)
        fila.setSpacing(8)
        titulo = QLabel(NOMBRE_APP)
        titulo.setFont(estilo.fuente(22, QFont.Weight.Bold, estilo.TITULAR))
        fila.addWidget(titulo)
        fila.addWidget(etiqueta("· Formación Profesional", "muted"))
        fila.addStretch(1)
        icono = QLabel()
        icono.setPixmap(estilo.icono_visto(estilo.T["accent"], 15, circulo=True))
        fila.addWidget(icono)
        self.catalogo = etiqueta("", "ok")
        self.catalogo.setToolTip("Catálogo curricular de Programaciones: ciclos, módulos, competencias y normas del BOE y "
                                 "del DOGV (solo lectura)")
        fila.addWidget(self.catalogo)
        fila.addSpacing(4)
        self.boton_vigia = boton("", pequeno=True)
        self.boton_vigia.clicked.connect(self.abrir_vigia)
        fila.addWidget(self.boton_vigia)
        self.boton_curso = boton("", pequeno=True)
        self.boton_curso.setToolTip("Curso académico del PCCF")
        self.boton_curso.clicked.connect(self._menu_cursos)
        fila.addWidget(self.boton_curso)
        nuevo = boton("Nuevo curso…", pequeno=True)
        nuevo.setToolTip("Crear el curso siguiente a partir de este, o comparar dos cursos o versiones aprobadas")
        nuevo.clicked.connect(self.nuevo_curso)
        fila.addWidget(nuevo)
        aj = boton("Ajustes", pequeno=True)
        aj.clicked.connect(self.abrir_ajustes)
        fila.addWidget(aj)
        return barra

    def _menu(self) -> None:
        barra = self.menuBar()

        def accion(menu, texto, disparo, atajo=None, rol=None) -> QAction:
            a = QAction(texto, self)
            if atajo is not None:
                a.setShortcut(QKeySequence(atajo))
            if rol is not None:
                a.setMenuRole(rol)
            a.triggered.connect(disparo)
            menu.addAction(a)
            return a

        archivo = barra.addMenu("Archivo")
        self.accion_vista = accion(archivo, "Vista previa", self.vista_previa, QKeySequence.StandardKey.Print)
        self.accion_exportar = accion(archivo, "Exportar", self.exportar, "Ctrl+E")
        archivo.addSeparator()
        accion(archivo, "Nuevo curso y comparar…", self.nuevo_curso, "Ctrl+Shift+N")
        accion(archivo, "Vigía normativo…", self.abrir_vigia)
        accion(archivo, "Releer la carpeta de datos", self.ctx.recalcular, "Ctrl+R")
        accion(archivo, "Abrir la carpeta de datos", lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(self.ctx.datos.carpeta))))
        accion(archivo, "Ajustes…", self.abrir_ajustes, "Ctrl+,", QAction.MenuRole.PreferencesRole)
        ayuda = barra.addMenu("Ayuda")
        accion(ayuda, f"Acerca de {NOMBRE_APP}", self.acerca_de, rol=QAction.MenuRole.AboutRole)

    # -- datos -------------------------------------------------------------------------------------------------------
    def recargar(self) -> None:
        """Otro ciclo, otro curso o la carpeta releída: se repinta todo y se vuelve al apartado en que estaba."""
        actual = self.izquierda.actual()
        self.centro.guardar_pendiente()
        self._repintar_barra()
        self.izquierda.recargar(actual)
        if self.ctx.estado is None:
            self.centro.mostrar(None)
        self.derecha.recargar()
        self.derecha.poner_miniatura(None)
        hay = self.ctx.estado is not None
        self.accion_vista.setEnabled(hay)
        self.accion_exportar.setEnabled(hay)

    def _repintar_barra(self) -> None:
        self.catalogo.setText(f"Catálogo · {self.ctx.cat.version}")
        self.boton_curso.setText(f"{self.ctx.sigla} · {self.ctx.curso}")
        inf = self.ctx.informe
        if self.ctx.estado is None:
            texto, aviso, ayuda = "§ Vigía", False, "Sin apartados para este grado"
        elif inf is None:
            texto, aviso, ayuda = "§ Vigía · sin informe", True, self.ctx.error
        else:
            n = len(inf.cambios) + len(inf.no_vigentes)
            if n:
                texto = f"§ Vigía · {n} norma{'s' if n > 1 else ''} cambiada{'s' if n > 1 else ''}"
            elif inf.nuevas:
                texto = f"§ Vigía · {len(inf.nuevas)} disposiciones nuevas"
            elif inf.anterior is None:
                texto = "§ Vigía · sin revisar"
            else:
                texto = "§ Vigía · al día"
            aviso = bool(n or inf.nuevas)
            ayuda = (f"Última revisión del PCCF: {inf.anterior}" if inf.anterior
                     else "Aún no se ha marcado ninguna revisión: ábrelo y márcalo como revisado")
        self.boton_vigia.setText(texto)
        self.boton_vigia.setToolTip(ayuda)
        self.boton_vigia.setProperty("aviso", aviso)
        self.boton_vigia.setProperty("ok", not aviso)
        refrescar_estilo(self.boton_vigia)

    def _repintar_estados(self) -> None:
        """Un bloque ha cambiado de estado mientras se edita: lista y estado, sin tocar el centro."""
        self.ctx.escrito()
        self.izquierda.recargar(self.izquierda.actual(), emitir=False)
        self.derecha.recargar()

    def _repintar_todo(self) -> None:
        self.ctx.escrito()
        self._repintar_barra()
        self.izquierda.recargar(self.izquierda.actual())
        self.derecha.recargar()

    def _menu_cursos(self) -> None:
        menu = QMenu(self)
        con_datos = set(self.ctx.datos.cursos(self.ctx.sigla))
        for c in self.ctx.cursos():
            a = menu.addAction(f"{c}{'' if c in con_datos else '  (sin datos del ciclo)'}")
            a.setCheckable(True)
            a.setChecked(c == self.ctx.curso)
            a.triggered.connect(lambda _=False, c=c: self.ctx.elegir(self.ctx.sigla, c))
        menu.exec(self.boton_curso.mapToGlobal(self.boton_curso.rect().bottomLeft()))

    # -- diálogos ----------------------------------------------------------------------------------------------------
    def abrir_vigia(self) -> None:
        if self.ctx.estado is None:
            return
        d = DialogoVigia(self.ctx, self)
        d.exec()
        if d.revisado:
            self.ctx.recalcular()
            self.aviso.mostrar("Vigía: revisión guardada en la carpeta de datos")

    def nuevo_curso(self) -> None:
        if self.ctx.estado is None:
            return
        self.centro.guardar_pendiente()
        d = DialogoNuevoCurso(self.ctx, self)
        if d.exec() and d.creado:
            self.ctx.elegir(self.ctx.sigla, d.creado)

    def nuevo_bloque(self, n: int) -> None:
        tipos = [t for t in self.ctx.estado.de(n).apartado.tipos if t != "derivado"]
        d = DialogoNuevoBloque(self.ctx, n, tipos, self)
        if d.exec():
            self._repintar_todo()
            self.aviso.mostrar(f"Bloque añadido: {d.bloque.ruta.relative_to(self.ctx.datos.carpeta).as_posix()}")

    def importar_bloque(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(self, "Importar bloque", str(Path.home()), "Bloque del PCCF (*.md)")
        if not ruta:
            return
        try:
            b = self.ctx.datos.importar_bloque(Path(ruta), self.ctx.sigla, self.ctx.curso)
        except FileExistsError as e:
            r = QMessageBox.question(self, "Importar bloque", f"{e}. ¿Lo sustituyes por el que traes?")
            if r != QMessageBox.StandardButton.Yes:
                return
            b = self.ctx.datos.importar_bloque(Path(ruta), self.ctx.sigla, self.ctx.curso, sustituir=True)
        except Exception as e:  # noqa: BLE001 - se dice qué le pasa al archivo
            QMessageBox.warning(self, "Importar bloque", f"No se puede importar:\n{e}")
            return
        self._repintar_todo()
        self.izquierda.ir(b.apartado)
        self.aviso.mostrar(f"Importado en el apartado {b.apartado}: {b.ruta.name}")

    def abrir_ajustes(self) -> None:
        if DialogoAjustes(self).exec():
            from .contexto import Contexto

            try:
                nuevo = Contexto()
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(self, "Ajustes", f"No se pueden abrir los datos con estos ajustes:\n{e}")
                return
            self.ctx.cat, self.ctx.datos = nuevo.cat, nuevo.datos
            self.ctx.elegir(self.ctx.sigla if self.ctx.sigla in nuevo.cat.siglas() else nuevo.sigla)

    def acerca_de(self) -> None:
        QMessageBox.about(self, f"Acerca de {NOMBRE_APP}",
                          f"<b>{NOMBRE_APP} {__version__}</b><br>Proyecto curricular de ciclo formativo (Decreto "
                          "114/2025, art. 8.4, y guía práctica de la DGFP).<br><br>Catálogo: "
                          f"{self.ctx.cat.carpeta}<br>Carpeta de datos: {self.ctx.datos.carpeta}")

    # -- documento ---------------------------------------------------------------------------------------------------
    def _opciones(self) -> documento.Opciones:
        return documento.Opciones(correo_pie=ajustes().value("correo_pie", "", str))

    def _en_segundo_plano(self, texto: str, trabajo, al_terminar) -> None:
        if self._tarea is not None:
            return
        self.centro.guardar_pendiente()
        self._espera = DialogoEspera(texto, self)
        self._tarea = Tarea(trabajo)

        def fin(res):
            self._cerrar_espera()
            al_terminar(res)

        def fallo(msg):
            self._cerrar_espera()
            QMessageBox.warning(self, NOMBRE_APP, msg)

        self._tarea.terminado.connect(fin)
        self._tarea.fallo.connect(fallo)
        self._tarea.start()
        self._espera.show()

    def _cerrar_espera(self) -> None:
        if self._espera is not None:
            self._espera.hide()
            self._espera.deleteLater()
            self._espera = None
        if self._tarea is not None:
            self._tarea.wait(2000)
            self._tarea = None

    def _generar(self) -> documento.Resultado:
        return documento.generar(self.ctx.cat, self.ctx.datos, self.ctx.sigla, self.ctx.curso, self._opciones())

    def vista_previa(self) -> None:
        if self.ctx.estado is None:
            return
        destino = Path(tempfile.gettempdir()) / "pccf-vista-previa" / f"PCCF {self.ctx.sigla} {self.ctx.curso}.pdf"
        motor = ajustes().value("motor_pdf", "auto", str)

        def trabajo(_avance):
            res = self._generar()
            return pdf.exportar_pdf(res.docx, destino, motor)

        def listo(ruta):
            self._miniatura(ruta)
            d = DialogoVistaPrevia(self)
            d.setWindowTitle(f"Vista previa · {self.ctx.sigla} {self.ctx.curso}")
            d.abrir(ruta)
            d.exec()

        self._en_segundo_plano("Preparando la vista previa…", trabajo, listo)

    def _miniatura(self, ruta: Path) -> None:
        doc = QPdfDocument(self)
        if doc.load(str(ruta)) == QPdfDocument.Error.None_ and doc.pageCount():
            img: QImage = doc.render(0, QSize(164, 232))
            self.derecha.poner_miniatura(QPixmap.fromImage(img))
        doc.close()

    def exportar(self) -> None:
        if self.ctx.estado is None:
            return
        formatos = self.derecha.formatos()
        salidas = self.ctx.datos.carpeta / "salidas"
        salidas.mkdir(parents=True, exist_ok=True)
        nombre = documento.nombre_archivo(self.ctx.sigla, self.ctx.curso)
        if "docx" in formatos:
            ruta, _ = QFileDialog.getSaveFileName(self, "Exportar", str(salidas / nombre), "Word (*.docx)")
        else:
            ruta, _ = QFileDialog.getSaveFileName(self, "Exportar", str(salidas / Path(nombre).with_suffix(".pdf")),
                                                  "PDF (*.pdf)")
        if not ruta:
            return
        base = Path(ruta).with_suffix("")
        motor = ajustes().value("motor_pdf", "auto", str)

        def trabajo(_avance):
            res = self._generar()
            hechos = []
            if "docx" in formatos:
                p = base.with_suffix(".docx")
                p.write_bytes(res.docx)
                hechos.append(p)
            if "pdf" in formatos:
                hechos.append(pdf.exportar_pdf(res.docx, base.with_suffix(".pdf"), motor))
            return hechos, res

        def listo(r):
            hechos, res = r
            estado = " en borrador" if res.borrador else ""
            self.aviso.mostrar(f"Exportado{estado}: {', '.join(p.name for p in hechos)}", 5000)
            if "pdf" in formatos:
                self._miniatura(base.with_suffix(".pdf"))

        self._en_segundo_plano("Preparando el documento…", trabajo, listo)

    def closeEvent(self, e):  # noqa: N802
        self.centro.guardar_pendiente()
        super().closeEvent(e)

    def mostrar_al_frente(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

