"""Ventana de Ajustes (ADR-022), como en Programaciones y Partes de salida: menú lateral y apartados; cada cambio se
guarda al momento (QSettings de este equipo).

Apartados: Carpetas (la de datos y el catálogo, con su comprobación al elegirlas) · Documento (programa del PDF y
correo del pie de la portada) · Versión y catálogo (la versión de la app con «Buscar actualizaciones» y «Acerca de…»;
la del catálogo, su origen, la última comprobación del publicado con «Comprobar ahora», y la carpeta de la app).

Al cerrar, `exec()` devuelve aceptado si la carpeta de datos y el catálogo son válidos (el arranque lo usa para
volver a intentar abrir los datos) y `carpetas_cambiadas` dice si la ventana tiene que recargarlos.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pccf import __version__
from pccf.rutas import carpeta_app, congelada

from . import estilo
from .componentes import boton, etiqueta, refrescar_estilo

APARTADOS = ["Carpetas", "Documento", "Versión y catálogo"]
MOTORES = (("Word y, si no, LibreOffice", "auto"), ("Solo Word", "word"), ("Solo LibreOffice", "libreoffice"))
RE_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Apartado(QScrollArea):
    """Página de Ajustes: título y filas «etiqueta | control» con su ayuda debajo."""

    def __init__(self, titulo: str):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        contenido = QWidget()
        contenido.setObjectName("pagina")
        self.setWidget(contenido)
        self.capa = QVBoxLayout(contenido)
        self.capa.setContentsMargins(22, 18, 22, 18)
        self.capa.setSpacing(16)
        t = QLabel(titulo)
        t.setFont(estilo.fuente(23, QFont.Weight.Bold, estilo.TITULAR))
        self.capa.addWidget(t)
        self.rejilla = QGridLayout()
        self.rejilla.setHorizontalSpacing(18)
        self.rejilla.setVerticalSpacing(10)
        self.rejilla.setColumnMinimumWidth(0, 170)
        self.rejilla.setColumnStretch(1, 1)
        self.capa.addLayout(self.rejilla)
        self._fila = 0

    def campo(self, texto: str, control, ayuda: str = "") -> QLabel:
        e = QLabel(texto)
        e.setStyleSheet("font-weight:600;")
        self.rejilla.addWidget(e, self._fila, 0, Qt.AlignmentFlag.AlignTop)
        if isinstance(control, QWidget):
            self.rejilla.addWidget(control, self._fila, 1)
        else:
            self.rejilla.addLayout(control, self._fila, 1)
        nota = etiqueta(ayuda, "pequeno", envolver=True)
        self.rejilla.addWidget(nota, self._fila + 1, 1)
        nota.setVisible(bool(ayuda))
        self._fila += 2
        return nota

    def fin(self) -> None:
        self.capa.addStretch(1)


def _fila(*widgets, estirar: bool = True) -> QHBoxLayout:
    f = QHBoxLayout()
    f.setSpacing(8)
    for w in widgets:
        f.addWidget(w, 1 if isinstance(w, QLineEdit) else 0)
    if estirar:
        f.addStretch(1)
    return f


def _rol(e: QLabel, rol: str, texto: str) -> None:
    e.setProperty("rol", rol)
    e.setText(texto)
    e.setVisible(bool(texto))
    refrescar_estilo(e)


def datos_validos(ruta: str) -> str:
    """Vacío si la carpeta de datos vale; si no, qué le pasa."""
    p = Path(ruta)
    if not ruta.strip():
        return "Elige la carpeta de datos (PCCF - DATOS)"
    if not p.is_dir():
        return "Esa carpeta no existe"
    return ""


def catalogo_valido(ruta: str) -> str:
    if not (Path(ruta) / "normativa.yaml").is_file():
        return "En esa carpeta no hay un catálogo (falta normativa.yaml)"
    return ""


class DialogoAjustes(QDialog):
    def __init__(self, padre=None, apartado: str | None = None):
        super().__init__(padre)
        from .contexto import ajustes

        self._a = ajustes()
        self.ventana = padre if padre is not None and hasattr(padre, "comprobar_catalogo") else None
        self.carpetas_cambiadas = False
        self.setWindowTitle("Ajustes")
        self.resize(940, 600)
        capa = QHBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.setSpacing(0)
        self.nav = QListWidget()
        self.nav.setObjectName("navegacion")
        self.nav.setFixedWidth(220)
        self.nav.setFont(estilo.fuente(14, QFont.Weight.DemiBold))
        for nombre in APARTADOS:
            item = QListWidgetItem(nombre)
            item.setSizeHint(QSize(0, 38))
            self.nav.addItem(item)
        capa.addWidget(self.nav)
        self.pila = QStackedWidget()
        self.pila.setStyleSheet(f"QStackedWidget, QWidget#pagina {{ background: {estilo.T['surface']}; }}")
        capa.addWidget(self.pila, 1)
        for crear in (self._carpetas, self._documento, self._version):
            self.pila.addWidget(crear())
        self.nav.currentRowChanged.connect(self.pila.setCurrentIndex)
        self.nav.setCurrentRow(APARTADOS.index(apartado) if apartado in APARTADOS else 0)

    def ir(self, apartado: str) -> None:
        self.nav.setCurrentRow(APARTADOS.index(apartado))

    # -- Carpetas ------------------------------------------------------------------------------------------------------
    def _carpetas(self) -> QWidget:
        from .contexto import carpeta_catalogo, carpeta_datos, catalogo_elegido

        ap = Apartado("Carpetas")
        self.datos = QLineEdit(str(carpeta_datos()))
        self.datos.setReadOnly(True)
        self.datos.setAccessibleName("Carpeta de datos")
        self.datos.setToolTip(self.datos.text())
        elegir = boton("Elegir…", pequeno=True)
        elegir.clicked.connect(self.elegir_datos)
        abrir = boton("Abrir", pequeno=True)
        abrir.setToolTip("Abrir la carpeta en el explorador de archivos")
        abrir.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.datos.text())))
        self.estado_datos = ap.campo("Carpeta de datos", _fila(self.datos, elegir, abrir, estirar=False),
                                     "La carpeta con git que mantiene el equipo (PCCF - DATOS): bloques, equipo "
                                     "docente y documentos generados.")
        self.catalogo = QLineEdit(str(carpeta_catalogo()) if catalogo_elegido() else "")
        self.catalogo.setReadOnly(True)
        self.catalogo.setPlaceholderText("Automático")
        self.catalogo.setAccessibleName("Catálogo")
        elegir_cat = boton("Elegir…", pequeno=True)
        elegir_cat.clicked.connect(self.elegir_catalogo)
        self.boton_automatico = boton("Volver al automático", pequeno=True)
        self.boton_automatico.clicked.connect(self.catalogo_automatico)
        self.estado_catalogo = ap.campo("Catálogo", _fila(self.catalogo, elegir_cat, self.boton_automatico,
                                                          estirar=False), " ")
        variables = [v for v in ("PCCF_DATOS", "PCCF_CATALOGO") if os.environ.get(v)]
        if variables:
            ap.campo("Variables", etiqueta(" y ".join(variables), "mono"),
                     "Están definidas en este equipo y mandan sobre estas carpetas.")
        ap.fin()
        self._pintar_catalogo_elegido()
        return ap

    def _pintar_catalogo_elegido(self) -> None:
        fijado = bool(self.catalogo.text())
        self.boton_automatico.setEnabled(fijado)
        _rol(self.estado_catalogo, "pequeno",
             "Fijado a mano: la app no baja el catálogo publicado." if fijado else
             "El catálogo curricular de Programaciones. La app instalada lleva uno y busca al arrancar, como mucho "
             "una vez al día, uno publicado más nuevo con su firma comprobada.")

    def elegir_datos(self, ruta: str | None = None) -> bool:
        ruta = ruta if isinstance(ruta, str) else QFileDialog.getExistingDirectory(self, "Carpeta de datos",
                                                                                   self.datos.text())
        if not ruta:
            return False
        error = datos_validos(ruta)
        if error:
            _rol(self.estado_datos, "error-texto", f"✕ {error}")
            return False
        self._a.setValue("carpeta_datos", ruta)
        self.datos.setText(ruta)
        self.datos.setToolTip(ruta)
        self.carpetas_cambiadas = True
        _rol(self.estado_datos, "ok", "Guardada. Al cerrar Ajustes se abren sus datos.")
        return True

    def elegir_catalogo(self, ruta: str | None = None) -> bool:
        ruta = ruta if isinstance(ruta, str) else QFileDialog.getExistingDirectory(self, "Catálogo",
                                                                                   self.catalogo.text())
        if not ruta:
            return False
        error = catalogo_valido(ruta)
        if error:
            _rol(self.estado_catalogo, "error-texto", f"✕ {error}")
            return False
        self._a.setValue("catalogo", ruta)
        self.catalogo.setText(ruta)
        self.carpetas_cambiadas = True
        self._pintar_catalogo_elegido()
        return True

    def catalogo_automatico(self) -> None:
        self._a.remove("catalogo")
        self.catalogo.setText("")
        self.carpetas_cambiadas = True
        self._pintar_catalogo_elegido()

    # -- Documento -----------------------------------------------------------------------------------------------------
    def _documento(self) -> QWidget:
        ap = Apartado("Documento")
        self.motor = QComboBox()
        for texto, valor in MOTORES:
            self.motor.addItem(texto, valor)
        self.motor.setCurrentIndex(max(0, self.motor.findData(self._a.value("motor_pdf", "auto", str))))
        self.motor.currentIndexChanged.connect(lambda _i: self._a.setValue("motor_pdf", self.motor.currentData()))
        ap.campo("PDF con", _fila(self.motor), "El programa que convierte el Word en PDF al exportar y en la vista "
                                               "previa. Con «Word y, si no, LibreOffice», el que haya en el equipo.")
        self.correo = QLineEdit(self._a.value("correo_pie", "", str))
        self.correo.setPlaceholderText("correo del centro o del departamento (opcional)")
        self.correo.setAccessibleName("Correo del pie")
        self.correo.editingFinished.connect(lambda: self.poner_correo(self.correo.text()))
        self.estado_correo = ap.campo("Correo del pie", self.correo, "Sale al pie de la portada, a la derecha. Vacío, "
                                                                     "no sale.")
        ap.fin()
        return ap

    def poner_correo(self, valor: str) -> bool:
        valor = valor.strip()
        if valor and not RE_CORREO.match(valor):
            _rol(self.estado_correo, "error-texto", "✕ No parece un correo: no se ha guardado")
            return False
        self._a.setValue("correo_pie", valor)
        _rol(self.estado_correo, "pequeno", "Guardado. Sale al pie de la portada." if valor else
             "Sin correo: el pie de la portada no lo lleva.")
        return True

    # -- Versión y catálogo --------------------------------------------------------------------------------------------
    def _version(self) -> QWidget:
        ap = Apartado("Versión y catálogo")
        self.boton_buscar = boton("Buscar actualizaciones", pequeno=True)
        self.boton_buscar.clicked.connect(self.buscar_actualizaciones)
        acerca = boton("Acerca de…", pequeno=True)
        acerca.clicked.connect(self.acerca_de)
        self.estado_version = ap.campo("Versión de la app", _fila(etiqueta(__version__, "mono"), self.boton_buscar,
                                                                  acerca),
                                       "La app busca versiones nuevas al arrancar; si hay una, sale el botón dorado "
                                       "«Actualizar» arriba." if congelada() else
                                       "Copia de desarrollo: las actualizaciones solo se instalan en la app "
                                       "instalada.")
        self.catalogo_version = etiqueta("", "mono")
        ap.campo("Versión del catálogo", self.catalogo_version)
        self.catalogo_origen = etiqueta("", "pequeno", envolver=True)
        ap.campo("Origen", self.catalogo_origen)
        self.boton_comprobar = boton("Comprobar ahora", pequeno=True)
        self.boton_comprobar.clicked.connect(self.comprobar_catalogo)
        self.catalogo_comprobado = etiqueta("", "pequeno", envolver=True)
        fila = QHBoxLayout()
        fila.setSpacing(10)
        fila.addWidget(self.boton_comprobar, 0, Qt.AlignmentFlag.AlignTop)
        fila.addWidget(self.catalogo_comprobado, 1)
        ap.campo("Catálogo publicado", fila,
                 "Solo se acepta con su firma comprobada. Sin conexión, la app sigue con el que tiene.")
        ruta = etiqueta(str(carpeta_app()), "pequeno", envolver=True)
        ruta.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        ap.campo("Carpeta de la app", ruta, "Registro, catálogos descargados y archivos de trabajo de este equipo. "
                                            "Los datos del PCCF están en la carpeta de datos.")
        ap.fin()
        self._pintar_version()
        return ap

    def _catalogo_actual(self):
        if self.ventana is not None:
            return self.ventana.ctx.cat
        try:
            from pccf.catalogo import Catalogo

            from .contexto import carpeta_catalogo

            return Catalogo(carpeta_catalogo())
        except Exception:  # noqa: BLE001 - sin catálogo válido todavía (arranque)
            return None

    def _pintar_version(self, mensaje: str = "") -> None:
        from pccf import catalogo_remoto

        from .contexto import catalogo_elegido

        cat = self._catalogo_actual()
        self.catalogo_version.setText(f"{cat.version} · {cat.fecha}" if cat else "—")
        if catalogo_elegido():
            origen = "Fijado en Carpetas (o con PCCF_CATALOGO)."
        elif not congelada():
            origen = "El del repositorio de Programaciones (copia de desarrollo)."
        elif cat is not None and Path(cat.carpeta).is_relative_to(catalogo_remoto.carpeta_versiones(carpeta_app())):
            origen = "Publicado y descargado después, con la firma comprobada."
        else:
            origen = "El que lleva la app."
        self.catalogo_origen.setText(origen)
        puede = congelada() and not catalogo_elegido()
        self.boton_comprobar.setEnabled(puede)
        if not puede:
            _rol(self.catalogo_comprobado, "pequeno", "No se comprueba: el catálogo está fijado o es una copia de "
                                                      "desarrollo.")
            return
        estado = catalogo_remoto.leer_estado(carpeta_app())
        texto = mensaje or estado.get("mensaje") or ""
        cuando = estado.get("ultima_comprobacion") or estado.get("ultimo_intento")
        if cuando:
            texto = f"{str(cuando)[:16].replace('T', ' ')} · {texto}" if texto else str(cuando)[:16].replace("T", " ")
        aviso = estado.get("resultado") in ("error", "sin_red") and not mensaje
        _rol(self.catalogo_comprobado, "aviso-texto" if aviso else "pequeno",
             (f"⚠ {texto}" if aviso else texto) or "Todavía no se ha comprobado")

    def buscar_actualizaciones(self) -> None:
        from .actualizar import buscar_actualizaciones, ofrecer

        def encontrada(version: str, url: str, notas: str) -> None:
            if self.ventana is not None:
                self.accept()
                self.ventana.actualizacion_disponible(version, url, notas)
            else:
                ofrecer(self, version, url, notas)

        buscar_actualizaciones(self, avisar_si_al_dia=True, al_encontrar=encontrada)

    def acerca_de(self) -> None:
        if self.ventana is not None:
            self.ventana.acerca_de()

    def comprobar_catalogo(self) -> None:
        self.boton_comprobar.setEnabled(False)
        _rol(self.catalogo_comprobado, "pequeno", "Comprobando…")

        def listo(res) -> None:
            try:
                self._pintar_version(res.mensaje)
            except RuntimeError:   # Ajustes ya está cerrado
                pass

        if self.ventana is not None:
            self.ventana.comprobar_catalogo(forzar=True, al_terminar=listo)
        else:
            from .actualizar import buscar_catalogo

            cat = self._catalogo_actual()
            buscar_catalogo(carpeta_app(), cat.version if cat else "0", listo, forzar=True)

    # -- cerrar --------------------------------------------------------------------------------------------------------
    def done(self, r: int) -> None:  # noqa: D401
        """Al cerrar (Esc, la cruz o tras una actualización): aceptado si las carpetas valen."""
        from .contexto import carpeta_catalogo, carpeta_datos

        del r

        valido = not datos_validos(str(carpeta_datos())) and not catalogo_valido(str(carpeta_catalogo()))
        super().done(QDialog.DialogCode.Accepted if valido else QDialog.DialogCode.Rejected)
