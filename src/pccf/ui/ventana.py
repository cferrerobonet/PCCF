"""Ventana principal (maqueta v0, aprobada el 2026-11-03): barra superior y tres zonas, apartados (280 px) · apartado
elegido (flexible) · estado, vista previa y exportar (290 px), en una ventana de 1100 × 700.

Barra: «PCCF · Formación Profesional», catálogo, vigía (dorado si ha visto cambios), ciclo y curso, «Nuevo curso…» y
«Ajustes». La vista previa y exportar trabajan en una `Tarea` (fuera de la interfaz) con la ventana de espera.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QFont, QImage, QKeySequence, QPixmap
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMenu, QMessageBox, QVBoxLayout, QWidget

from pccf import __version__, bloques, documento, pdf, word
from pccf.datos import WordSinBloque
from pccf.rutas import carpeta_app, congelada

from . import estilo
from .ajustes import DialogoAjustes
from .apartado import VistaApartado
from .apartados import ZonaApartados
from .componentes import AvisoFlotante, Tarea, boton, etiqueta, refrescar_estilo, separador_vertical
from .contexto import ajustes
from .dialogos import DialogoEspera, DialogoNuevoBloque, DialogoNuevoCurso, DialogoVigia
from .resumen import ZonaResumen
from .vista_previa import DialogoVistaPrevia

logger = logging.getLogger(__name__)
NOMBRE_APP = "PCCF"


#: Las dos zonas laterales: una cuarta parte de la ventana cada una, entre 330 y 400 px (ADR-026). Con la ventana
#: mínima, el centro conserva los 530 px de la maqueta v0 (la tabla de 19 competencias del apartado 4).
LATERAL = (330, 400)
ANCHO_MINIMO = 1240


def ancho_lateral(ancho_ventana: int) -> int:
    return max(LATERAL[0], min(LATERAL[1], ancho_ventana // 4))


class VentanaPrincipal(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._actualizacion: tuple[str, str, str] | None = None
        self._tarea: Tarea | None = None
        self._espera: DialogoEspera | None = None
        self.setWindowTitle(NOMBRE_APP)
        self.setMinimumSize(ANCHO_MINIMO, 660)
        pantalla = self.screen().availableGeometry() if self.screen() else None
        ancho = min(1440, pantalla.width() - 40) if pantalla else 1440
        self.resize(max(ANCHO_MINIMO, ancho), min(900, pantalla.height() - 40) if pantalla else 880)
        # Solo el botón de cerrar: ni maximizar ni minimizar; la ventana ocupa la pantalla (ADR-027)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint
                            | Qt.WindowType.WindowCloseButtonHint)
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
        self.boton_actualizar = boton("", pequeno=True, dorado=True)
        self.boton_actualizar.hide()
        self.boton_actualizar.clicked.connect(self._ofrecer_actualizacion)
        fila.addWidget(self.boton_actualizar)
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
        self.boton_salir = boton("Salir", pequeno=True, salir=True)
        self.boton_salir.setToolTip("Guarda y cierra la aplicación")
        self.boton_salir.clicked.connect(self.close)
        fila.addWidget(self.boton_salir)
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
        accion(ayuda, "Buscar actualizaciones", lambda: self.buscar_actualizaciones(avisar_si_al_dia=True))
        accion(ayuda, "Abrir el registro de la app", lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(carpeta_app() / "logs"))))
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

    def _numero(self, n: int) -> int:
        """El número que se ve del apartado de clave `n` en el grado del ciclo (ADR-023)."""
        from pccf import apartados as aps

        try:
            return aps.numero(self.ctx.grado, n)
        except KeyError:
            return n

    def importar_bloque(self) -> None:
        """Un Word exportado desde la app vuelve a su bloque; cualquier otro Word, a un bloque nuevo del apartado
        abierto (ADR-020). Se aceptan también los bloques `.md` de la versión 0.1.0."""
        ruta, _ = QFileDialog.getOpenFileName(self, "Importar Word", str(Path.home()),
                                              "Word (*.docx);;Bloque de la versión 0.1.0 (*.md)")
        if not ruta:
            return
        self.centro.guardar_pendiente()
        origen = Path(ruta)
        try:
            try:
                b = self.ctx.datos.importar_bloque(origen, self.ctx.sigla, self.ctx.curso, hoy=self.ctx.hoy())
            except FileExistsError as e:
                r = QMessageBox.question(self, "Importar Word", f"{e}. ¿Lo sustituyes por el texto que traes?")
                if r != QMessageBox.StandardButton.Yes:
                    return
                b = self.ctx.datos.importar_bloque(origen, self.ctx.sigla, self.ctx.curso, sustituir=True,
                                                   hoy=self.ctx.hoy())
        except WordSinBloque:
            b = self._word_a_bloque_nuevo(origen)
            if b is None:
                return
        except Exception as e:  # noqa: BLE001 - se dice qué le pasa al archivo
            QMessageBox.warning(self, "Importar Word", f"No se puede importar:\n{e}")
            return
        self._repintar_todo()
        self.izquierda.ir(b.apartado)
        self.aviso.mostrar(f"Importado en el apartado {self._numero(b.apartado)}, en borrador: {b.ruta.name}")

    def _word_a_bloque_nuevo(self, origen: Path):
        """Un Word cualquiera: su texto va a un bloque nuevo del apartado abierto (se pide el tipo y la autoría)."""
        n = self.centro.n
        if n is None:
            QMessageBox.information(self, "Importar Word", "Elige antes el apartado al que va el texto")
            return None
        try:
            imp = word.importar(origen.read_bytes())
        except (OSError, word.WordNoValido) as e:
            QMessageBox.warning(self, "Importar Word", str(e))
            return None
        if not imp.parrafos:
            QMessageBox.warning(self, "Importar Word", "El Word no tiene texto")
            return None
        tipos = [t for t in self.ctx.estado.de(n).apartado.tipos if t != "derivado"]
        if not tipos:
            QMessageBox.information(self, "Importar Word", f"El apartado {self._numero(n)} se calcula: no lleva textos del equipo")
            return None
        d = DialogoNuevoBloque(self.ctx, n, tipos, self, nombre=origen.stem,
                               explicacion=f"Apartado {self._numero(n)}. El texto de «{origen.name}» entra en un bloque nuevo, en "
                                           "borrador." + ("".join(f" {a}." for a in imp.avisos)))
        if not d.exec():
            return None
        return bloques.escribir_de_word(d.bloque.ruta, bloques.cabecera(d.bloque), imp.parrafos, self.ctx.hoy())

    def resizeEvent(self, e) -> None:  # noqa: N802
        super().resizeEvent(e)
        lateral = ancho_lateral(self.width())
        self.izquierda.setFixedWidth(lateral)
        self.derecha.setFixedWidth(lateral)

    def abrir_ajustes(self, apartado: str | None = None) -> None:
        self.centro.guardar_pendiente()
        d = DialogoAjustes(self, apartado)
        d.exec()
        if d.carpetas_cambiadas:
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
                          f"<b>{NOMBRE_APP} {__version__}</b> · catálogo {self.ctx.cat.version}<br>Proyecto curricular de ciclo formativo (Decreto "
                          "114/2025 y Decreto 117/2025, art. 8.4, y guía práctica de la DGFP).<br><br>Catálogo: "
                          f"{self.ctx.cat.carpeta}<br>Carpeta de datos: {self.ctx.datos.carpeta}")

    # -- actualizaciones y catálogo publicado ------------------------------------------------------------------------
    def buscar_actualizaciones(self, avisar_si_al_dia: bool = False) -> None:
        from .actualizar import buscar_actualizaciones

        buscar_actualizaciones(self, avisar_si_al_dia, al_encontrar=self.actualizacion_disponible)

    def actualizacion_disponible(self, version: str, url: str, notas: str) -> None:
        """Hay versión nueva: botón dorado fijo y, la primera vez, el diálogo por encima."""
        nueva = self._actualizacion is None or self._actualizacion[0] != version
        self._actualizacion = (version, url, notas)
        self.boton_actualizar.setText(f"↑  Actualizar a {version}")
        self.boton_actualizar.setToolTip("Hay una versión nueva de la aplicación")
        self.boton_actualizar.show()
        if nueva and self.isVisible():
            self._ofrecer_actualizacion()

    def _ofrecer_actualizacion(self) -> None:
        from .actualizar import ofrecer

        if self._actualizacion:
            self.centro.guardar_pendiente()
            self.mostrar_al_frente()
            ofrecer(self, *self._actualizacion)

    def comprobar_catalogo(self, forzar: bool = False, al_terminar=None) -> None:
        """En la app instalada, al arrancar y como mucho una vez al día (o ya, desde Ajustes): si hay un catálogo
        publicado más nuevo y verificado, se pasa a él y el vigía dice qué ha cambiado. Con el catálogo fijado en
        Ajustes, nada. `al_terminar(resultado)`, después."""
        from .actualizar import buscar_catalogo
        from .contexto import catalogo_elegido

        if not congelada() or catalogo_elegido():
            return

        def listo(res):
            if al_terminar is not None:
                al_terminar(res)
            if not res.nuevas:
                return
            from pccf import catalogo_remoto
            from pccf.catalogo import Catalogo

            nuevo = catalogo_remoto.mas_nuevo(catalogo_remoto.disponibles(carpeta_app(), Catalogo()))
            if nuevo.version != self.ctx.cat.version:
                self.centro.guardar_pendiente()
                self.ctx.cat = nuevo
                self.ctx.recalcular()
                self.aviso.mostrar(f"Catálogo {nuevo.version} verificado: el vigía dice qué ha cambiado", 6000)

        buscar_catalogo(carpeta_app(), self.ctx.cat.version, listo, forzar=forzar)

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

    def ocupar_pantalla(self) -> None:
        """Pantalla completa (ADR-027), como Programaciones: la del botón verde de macOS, sin la barra de menús ni el
        Dock a la vista; en Windows y Linux, sin la barra de tareas ni la del título. Se sale con «Salir» (o ⌘Q /
        Alt+F4)."""
        self.showFullScreen()

    def mostrar_al_frente(self) -> None:
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.ocupar_pantalla()
        self.raise_()
        self.activateWindow()

