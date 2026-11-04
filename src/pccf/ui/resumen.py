"""Zona derecha (290 px, maqueta v0): progreso (apartados confirmados), lo que necesita atención, avisos (heredados sin
confirmar, vigía), vista previa y exportar, con «Exportar» siempre abajo."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from pccf import estado as estado_mod

from . import estilo
from .componentes import atajo, boton, etiqueta, limpiar


class ZonaResumen(QWidget):
    pedir_apartado = pyqtSignal(int)
    pedir_vigia = pyqtSignal()
    pedir_vista_previa = pyqtSignal()
    pedir_exportar = pyqtSignal()

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setFixedWidth(290)
        capa = QVBoxLayout(self)
        capa.setContentsMargins(14, 16, 14, 14)
        capa.setSpacing(8)
        capa.addWidget(etiqueta("Estado", "etiqueta"))
        self.progreso = QProgressBar()
        self.progreso.setTextVisible(False)
        self.progreso.setFixedHeight(10)
        self.progreso.setAccessibleName("Apartados confirmados")
        capa.addWidget(self.progreso)
        self.cuenta = etiqueta("", "muted", envolver=True)
        capa.addWidget(self.cuenta)
        self.atencion = QVBoxLayout()
        self.atencion.setSpacing(4)
        capa.addLayout(self.atencion)
        self.avisos = QVBoxLayout()
        self.avisos.setSpacing(6)
        capa.addLayout(self.avisos)
        capa.addSpacing(8)
        capa.addWidget(etiqueta("Vista previa", "etiqueta"))
        fila = QHBoxLayout()
        fila.setSpacing(12)
        self.miniatura = QLabel()
        self.miniatura.setProperty("rol", "miniatura")
        self.miniatura.setFixedSize(84, 118)
        self.miniatura.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.miniatura.setPixmap(estilo.icono_documento(estilo.T["muted"], 26))
        fila.addWidget(self.miniatura)
        textos = QVBoxLayout()
        self.texto_vista = etiqueta("", "pequeno", envolver=True)
        textos.addWidget(self.texto_vista)
        self.boton_vista = boton(f"Vista previa {atajo('P')}", pequeno=True)
        self.boton_vista.setToolTip("El mismo documento, convertido a PDF")
        self.boton_vista.clicked.connect(self.pedir_vista_previa)
        textos.addWidget(self.boton_vista)
        textos.addStretch(1)
        fila.addLayout(textos, 1)
        capa.addLayout(fila)
        capa.addSpacing(6)
        capa.addWidget(etiqueta("Exportar", "etiqueta"))
        formatos = QHBoxLayout()
        formatos.setSpacing(6)
        self.word = boton("Word", formato=True)
        self.pdf = boton("PDF", formato=True)
        for b, ayuda in ((self.word, "Documento de Word (.docx)"), (self.pdf, "PDF hecho con el Word del equipo o "
                                                                              "con LibreOffice")):
            b.setCheckable(True)
            b.setToolTip(ayuda)
            formatos.addWidget(b)
        formatos.addStretch(1)
        self.word.setChecked(True)
        self.word.toggled.connect(self._formatos)
        self.pdf.toggled.connect(self._formatos)
        capa.addLayout(formatos)
        capa.addStretch(1)
        self.exportar = boton(f"Exportar {atajo('E')}", primario=True, grande=True)
        self.exportar.setFont(estilo.fuente(20, QFont.Weight.Bold, estilo.TITULAR))
        self.exportar.clicked.connect(self.pedir_exportar)
        capa.addWidget(self.exportar)
        nota = etiqueta("Los apartados sin texto salen con «Pendiente» y lo que pide la guía", "pequeno", envolver=True)
        nota.setAlignment(Qt.AlignmentFlag.AlignCenter)
        capa.addWidget(nota)

    def _formatos(self) -> None:
        if not self.word.isChecked() and not self.pdf.isChecked():
            self.word.setChecked(True)

    def formatos(self) -> list[str]:
        return [f for f, b in (("docx", self.word), ("pdf", self.pdf)) if b.isChecked()]

    def poner_miniatura(self, imagen: QPixmap | None) -> None:
        if imagen is None or imagen.isNull():
            self.miniatura.setPixmap(estilo.icono_documento(estilo.T["muted"], 26))
        else:
            self.miniatura.setPixmap(imagen.scaled(82, 116, Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation))

    def recargar(self) -> None:
        limpiar(self.atencion)
        limpiar(self.avisos)
        e = self.ctx.estado
        activo = e is not None
        for w in (self.boton_vista, self.exportar, self.word, self.pdf):
            w.setEnabled(activo)
        if e is None:
            self.progreso.setValue(0)
            self.cuenta.setText("Hay un error en la carpeta de datos" if self.ctx.error else
                                "Sin apartados para este grado")
            self.texto_vista.setText("")
            return
        total = len(e.apartados)
        self.progreso.setMaximum(total)
        self.progreso.setValue(e.confirmados)
        self.cuenta.setText(f"{e.confirmados} de {total} apartados confirmados · {len(e.con('pendiente'))} "
                            "pendientes")
        orden = [a for est in ("revisar", "heredado", "borrador") for a in e.con(est)]
        for a in orden[:7]:
            self.atencion.addWidget(self._fila(a))
        if len(orden) > 7:
            self.atencion.addWidget(etiqueta(f"y {len(orden) - 7} más", "pequeno"))
        heredados = sum(1 for a in e.apartados for b in a.bloques if estado_mod.de_bloque(b) == "heredado")
        if e.de(1).estado == "heredado":
            heredados += 1
        if heredados:
            primero = next(a.n for a in e.apartados if a.estado == "heredado")
            self.avisos.addWidget(self._aviso(f"{heredados} heredado{'s' if heredados > 1 else ''} sin confirmar",
                                              lambda: self.pedir_apartado.emit(primero)))
        inf = e.informe
        if self.ctx.error:
            self.avisos.addWidget(etiqueta(self.ctx.error, "aviso", envolver=True))
        elif inf is not None and (inf.hay_cambios or inf.no_vigentes):
            n = len(inf.cambios) + len(inf.no_vigentes)
            texto = (f"Vigía: {inf.cambios[0].cita} ha cambiado" if n == 1 and inf.cambios
                     else f"Vigía: {n} normas con cambios" if n else f"Vigía: {len(inf.nuevas)} disposiciones nuevas")
            self.avisos.addWidget(self._aviso(texto, self.pedir_vigia.emit))
        borrador = e.confirmados < total
        self.texto_vista.setText(f"Portada, control, contenido, {total} apartados y anexos."
                                 + (" Con «Borrador» en la portada y el encabezado." if borrador else ""))

    def _fila(self, a: estado_mod.EstadoApartado) -> QWidget:
        w = boton("", enlace=True)
        w.setToolTip(a.motivo)
        fila = QHBoxLayout(w)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(6)
        icono = QLabel()
        icono.setPixmap(estilo.icono_estado(a.estado, 12))
        fila.addWidget(icono)
        t = etiqueta(f"{a.n} · {a.apartado.titulo}")
        t.setMaximumWidth(170)
        t.setText(t.fontMetrics().elidedText(t.text(), Qt.TextElideMode.ElideRight, 170))
        fila.addWidget(t, 1)
        fila.addWidget(etiqueta(estado_mod.NOMBRES[a.estado], f"estado-{a.estado}"))
        w.setMinimumHeight(24)
        w.setAccessibleName(f"Ir al apartado {a.n}: {estado_mod.NOMBRES[a.estado]}")
        w.clicked.connect(lambda: self.pedir_apartado.emit(a.n))
        return w

    def _aviso(self, texto: str, accion) -> QWidget:
        f = QFrame()
        f.setProperty("rol", "aviso-vigia")
        fila = QHBoxLayout(f)
        fila.setContentsMargins(12, 6, 6, 6)
        fila.addWidget(etiqueta(texto, "aviso-vigia", envolver=True), 1)
        ir = boton("Ir ›", enlace=True)
        ir.setStyleSheet(f"color: {estilo.T['warn']};")
        ir.clicked.connect(accion)
        fila.addWidget(ir)
        return f
