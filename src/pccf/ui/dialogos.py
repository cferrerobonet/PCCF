"""Ventanas modales (maqueta v0): vigía normativo, «Nuevo curso» y «Comparar», nuevo bloque, ajustes y la espera
mientras se hace el documento."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pccf import cursos, vigia
from pccf.datos import DatosNoValidos

from . import estilo
from .componentes import boton, desplazable, etiqueta


def _titulo(texto: str) -> QLabel:
    t = QLabel(texto.upper())
    t.setFont(estilo.fuente(30, QFont.Weight.Bold, estilo.TITULAR))
    return t


def _base(dialogo: QDialog, titulo: str, ancho: int, alto: int) -> QVBoxLayout:
    dialogo.setWindowTitle(titulo)
    dialogo.resize(ancho, alto)
    capa = QVBoxLayout(dialogo)
    capa.setContentsMargins(26, 22, 26, 20)
    capa.setSpacing(12)
    capa.addWidget(_titulo(titulo))
    return capa


# ---------------------------------------------------------------------------------------------------------------------
# Vigía
# ---------------------------------------------------------------------------------------------------------------------
class DialogoVigia(QDialog):
    """El informe del vigía: normas cambiadas con qué cambia, su enlace y dónde se usan; las no vigentes, las
    disposiciones nuevas y las citas sin vigilar. «Marcar como revisado» fija el punto de partida de la próxima."""

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.revisado = False
        capa = _base(self, "Vigía normativo", 860, 640)
        inf = ctx.informe
        if inf is None:
            capa.addWidget(etiqueta(ctx.error or "Sin informe", "aviso", envolver=True))
            return
        anterior = (f"comparado con la revisión del {inf.anterior}" if inf.anterior else
                    "es la primera revisión de este PCCF: no hay con qué comparar hasta marcarla como revisada")
        capa.addWidget(etiqueta(f"{inf.sigla} · {inf.curso} · revisión del {inf.fecha} con el catálogo {inf.catalogo}, "
                                f"{anterior}. Lee lo que el vigía semanal de Programaciones ve en el BOE y el DOGV; "
                                "no sale a la red.", "muted", envolver=True))
        cuerpo = QWidget()
        lista = QVBoxLayout(cuerpo)
        lista.setContentsMargins(0, 0, 6, 0)
        lista.setSpacing(10)
        for c in inf.cambios:
            lista.addWidget(self._cambio(c, "Cambia"))
        for c in inf.no_vigentes:
            lista.addWidget(self._cambio(c, "No vigente"))
        if inf.nuevas:
            f = self._caja("caja")
            f.layout().addWidget(etiqueta("Disposiciones nuevas que ha visto el vigía de Programaciones", "aviso-texto"))
            for n in inf.nuevas:
                f.layout().addWidget(etiqueta(f"• {n}", envolver=True))
            lista.addWidget(f)
        if inf.sin_vigilar:
            f = self._caja("caja")
            f.layout().addWidget(etiqueta("Citas sin vigilar (el catálogo no las tiene)", "aviso-texto"))
            for cita, usos in inf.sin_vigilar.items():
                f.layout().addWidget(etiqueta(f"• {cita} — {', '.join(sorted({u.detalle for u in usos}))}",
                                              envolver=True))
            lista.addWidget(f)
        if not (inf.cambios or inf.no_vigentes or inf.nuevas):
            f = self._caja("curriculo")
            f.layout().addWidget(etiqueta("Sin cambios en las normas en que se apoya el PCCF" if inf.anterior else
                                          "Sin revisión anterior: no hay cambios que enseñar", "ok"))
            lista.addWidget(f)
        for a in inf.avisos:
            lista.addWidget(etiqueta(a, "info", envolver=True))
        lista.addStretch(1)
        capa.addWidget(desplazable(cuerpo), 1)
        nota = etiqueta("El vigía no cambia ningún texto: avisa. Revisa los bloques y márcalo como revisado.", "pequeno")
        nota.setAlignment(Qt.AlignmentFlag.AlignCenter)
        capa.addWidget(nota)
        botones = QHBoxLayout()
        cerrar = boton("Cerrar")
        cerrar.clicked.connect(self.reject)
        botones.addWidget(cerrar)
        botones.addStretch(1)
        guardar = boton("Guardar informe (.md)")
        guardar.clicked.connect(self.guardar)
        botones.addWidget(guardar)
        marcar = boton("Marcar como revisado", primario=True)
        marcar.setToolTip("Guarda lo que dice hoy el catálogo de las normas del PCCF: el punto de partida de la próxima "
                          "revisión (vigia.yaml del curso, en la carpeta de datos)")
        marcar.clicked.connect(self.marcar)
        botones.addWidget(marcar)
        capa.addLayout(botones)

    def _caja(self, rol: str) -> QFrame:
        f = QFrame()
        f.setProperty("rol", rol)
        c = QVBoxLayout(f)
        c.setContentsMargins(14, 10, 14, 10)
        c.setSpacing(5)
        return f

    def _cambio(self, c: vigia.Cambio, que: str) -> QFrame:
        f = self._caja("aviso-vigia")
        cab = QHBoxLayout()
        chip = QLabel(que)
        chip.setProperty("tipo", "anual")
        cab.addWidget(chip)
        t = etiqueta(c.cita)
        t.setFont(estilo.fuente(15, QFont.Weight.Bold))
        cab.addWidget(t)
        ident = etiqueta(c.norma, "codigo")
        ident.setFont(estilo.fuente(13, familia=estilo.MONO))
        cab.addWidget(ident)
        cab.addStretch(1)
        if c.enlace:
            abrir = boton("Abrir ›", enlace=True, verde=True)
            abrir.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(c.enlace)))
            cab.addWidget(abrir)
        f.layout().addLayout(cab)
        for x in c.que:
            f.layout().addWidget(etiqueta(f"• {x}", envolver=True))
        if c.usos:
            f.layout().addWidget(etiqueta(f"Dónde se usa ({len(c.usos)})", "etiqueta"))
            for u in c.usos:
                art = f" · art. {u.articulo}" if u.articulo else ""
                f.layout().addWidget(etiqueta(f"• {u.apartado or '—'} · {u.titulo} · {u.detalle}{art}",
                                              envolver=True))
        return f

    def guardar(self) -> None:
        inf = self.ctx.informe
        salida = self.ctx.datos.carpeta / "salidas" / vigia.nombre_archivo(inf.sigla, inf.curso)
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(vigia.markdown(inf), encoding="utf-8")
        QMessageBox.information(self, "Informe del vigía", f"Guardado en\n{salida}")

    def marcar(self) -> None:
        r = QMessageBox.question(self, "Marcar como revisado",
                                 "¿Das por revisado lo que dice hoy el catálogo de las normas de este PCCF? Los avisos "
                                 "de ahora dejarán de salir; los cambios que lleguen después, sí.")
        if r != QMessageBox.StandardButton.Yes:
            return
        vigia.marcar_revisado(self.ctx.cat, self.ctx.datos, self.ctx.sigla, self.ctx.curso)
        self.revisado = True
        self.accept()


# ---------------------------------------------------------------------------------------------------------------------
# Nuevo curso y Comparar
# ---------------------------------------------------------------------------------------------------------------------
class DialogoNuevoCurso(QDialog):
    """A la izquierda, «Nuevo curso» (de qué curso se parte y cuál se crea); a la derecha, «Comparar» dos cursos o un
    curso en una versión aprobada, apartado por apartado, con lo añadido y lo quitado."""

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.creado: str | None = None
        self._comparacion: cursos.Comparacion | None = None
        capa = _base(self, "Nuevo curso", 1080, 640)
        columnas = QHBoxLayout()
        columnas.setSpacing(24)
        capa.addLayout(columnas, 1)

        izq = QVBoxLayout()
        izq.setSpacing(10)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.origen = QComboBox()
        self.origen.setAccessibleName("Curso de partida")
        for c in ctx.datos.cursos(ctx.sigla):
            self.origen.addItem(f"{ctx.sigla} · {c}", c)
        self.destino = QLineEdit()
        self.destino.setAccessibleName("Curso nuevo")
        self.destino.setPlaceholderText("AAAA-AAAA")
        self.origen.currentIndexChanged.connect(self._sugerir)
        form.addRow("A partir de", self.origen)
        form.addRow("Nuevo curso", self.destino)
        izq.addLayout(form)
        for icono, texto in (("confirmado", "Bloques de centro y de ciclo: son comunes a todos los cursos, no se copian"),
                             ("heredado", "Equipo docente y bloques del curso: se copian como heredados, en borrador, "
                                          "y hay que confirmarlos"),
                             ("confirmado", "Lo calculado: se rehace con el catálogo del día"),
                             ("confirmado", "Normas: el vigía las revisa al crear el curso"),
                             ("confirmado", "Nunca sobrescribe: si el ciclo ya tiene ese curso, se para")):
            fila = QHBoxLayout()
            ic = QLabel()
            ic.setPixmap(estilo.icono_estado(icono, 13))
            fila.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)
            fila.addWidget(etiqueta(texto, envolver=True), 1)
            izq.addLayout(fila)
        if self.origen.count() == 0:
            izq.addWidget(etiqueta(f"{ctx.sigla} aún no tiene ningún curso en la carpeta de datos: no hay de dónde "
                                   "partir.", "aviso", envolver=True))
        izq.addStretch(1)
        columnas.addLayout(izq, 5)

        der = QVBoxLayout()
        der.setSpacing(8)
        der.addWidget(etiqueta("Comparar", "etiqueta"))
        elegir = QHBoxLayout()
        self.lado_a, self.lado_b = QComboBox(), QComboBox()
        lados = [(c, c) for c in ctx.datos.cursos(ctx.sigla)]
        for e in ctx.datos.etiquetas(ctx.sigla):
            partes = e.split("-")
            curso = f"{partes[1]}-{partes[2]}" if len(partes) >= 4 else ""
            if curso:
                lados.append((f"{curso} (aprobado, {e})", f"{curso}@{e}"))
        for combo, nombre in ((self.lado_a, "Antes"), (self.lado_b, "Después")):
            combo.setAccessibleName(nombre)
            for texto, valor in lados:
                combo.addItem(texto, valor)
        if len(lados) > 1:
            self.lado_a.setCurrentIndex(1)
        elegir.addWidget(self.lado_a, 1)
        elegir.addWidget(etiqueta("→"))
        elegir.addWidget(self.lado_b, 1)
        self.boton_comparar = boton("Comparar", pequeno=True)
        self.boton_comparar.clicked.connect(self.comparar)
        self.boton_comparar.setEnabled(len(lados) > 1)
        elegir.addWidget(self.boton_comparar)
        der.addLayout(elegir)
        self.tabla = QTableWidget(0, 2)
        self.tabla.setHorizontalHeaderLabels(["Apartado", "Cambios"])
        self.tabla.verticalHeader().hide()
        self.tabla.setShowGrid(False)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setColumnWidth(0, 300)
        self.tabla.currentCellChanged.connect(lambda f, *_: self._detalle(f))
        der.addWidget(self.tabla, 2)
        self.detalle = QPlainTextEdit()
        self.detalle.setReadOnly(True)
        self.detalle.setAccessibleName("Diferencias del apartado")
        self.detalle.setPlaceholderText("Elige un apartado para ver lo añadido (+) y lo quitado (−)")
        der.addWidget(self.detalle, 1)
        self.aviso_comparar = etiqueta("" if len(lados) > 1 else "Hace falta otro curso, o una versión aprobada "
                                       "(etiqueta de git de la carpeta de datos), con que comparar.", "pequeno",
                                       envolver=True)
        der.addWidget(self.aviso_comparar)
        columnas.addLayout(der, 6)

        botones = QHBoxLayout()
        self.guardar_md = boton("Guardar comparación (.md)")
        self.guardar_md.setEnabled(False)
        self.guardar_md.clicked.connect(self.guardar_comparacion)
        botones.addWidget(self.guardar_md)
        botones.addStretch(1)
        cancelar = boton("Cancelar")
        cancelar.clicked.connect(self.reject)
        botones.addWidget(cancelar)
        self.crear = boton("", primario=True)
        self.crear.clicked.connect(self.crear_curso)
        botones.addWidget(self.crear)
        capa.addLayout(botones)
        self.destino.textChanged.connect(lambda t: self.crear.setText(f"Crear {t.strip() or 'curso'}"))
        self._sugerir()
        self.crear.setEnabled(self.origen.count() > 0)

    def _sugerir(self) -> None:
        c = self.origen.currentData()
        self.destino.setText(cursos.siguiente(c) if c else "")

    def crear_curso(self) -> None:
        origen, destino = self.origen.currentData(), self.destino.text().strip()
        try:
            res = cursos.nuevo_curso(self.ctx.cat, self.ctx.datos, self.ctx.sigla, origen, destino)
        except (cursos.CursoNoValido, FileNotFoundError, FileExistsError, DatosNoValidos) as e:
            QMessageBox.warning(self, "Nuevo curso", str(e))
            return
        texto = [f"Creado {self.ctx.sigla} {destino}.",
                 f"Heredado, en borrador hasta confirmarlo: {', '.join(res.heredados) or 'nada'}."]
        texto += res.avisos
        QMessageBox.information(self, "Nuevo curso", "\n\n".join(texto))
        self.creado = destino
        self.accept()

    def comparar(self) -> None:
        a, b = self.lado_a.currentData(), self.lado_b.currentData()
        if a == b:
            self.aviso_comparar.setText("Elige dos lados distintos")
            return
        try:
            self._comparacion = cursos.comparar(self.ctx.cat, self.ctx.datos, self.ctx.sigla, a, b)
        except (cursos.CursoNoValido, DatosNoValidos) as e:
            QMessageBox.warning(self, "Comparar", str(e))
            return
        c = self._comparacion
        self.tabla.setRowCount(len(c.apartados))
        for i, d in enumerate(c.apartados):
            self.tabla.setItem(i, 0, QTableWidgetItem(f"{d.n} · {d.titulo}"))
            texto = f"+{len(d.anadidas)}  −{len(d.quitadas)}" if d.cambia else "sin cambios"
            it = QTableWidgetItem(texto)
            if d.cambia:
                it.setForeground(estilo.QColor(estilo.T["accent"]))
            self.tabla.setItem(i, 1, it)
        self.tabla.resizeRowsToContents()
        cambian = sum(1 for d in c.apartados if d.cambia)
        self.aviso_comparar.setText(f"{c.a} → {c.b}: cambian {cambian} apartados. " + " ".join(c.avisos))
        self.guardar_md.setEnabled(True)
        self.detalle.clear()

    def _detalle(self, fila: int) -> None:
        if self._comparacion is None or fila < 0:
            return
        d = self._comparacion.apartados[fila]
        lineas = [f"+ {x}" for x in d.anadidas] + [f"− {x}" for x in d.quitadas]
        self.detalle.setPlainText("\n".join(lineas) or "Sin cambios")

    def guardar_comparacion(self) -> None:
        c = self._comparacion
        salida = self.ctx.datos.carpeta / "salidas" / cursos.nombre_archivo(c.sigla, self.lado_a.currentData(),
                                                                            self.lado_b.currentData())
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(cursos.markdown(c), encoding="utf-8")
        QMessageBox.information(self, "Comparar", f"Guardada en\n{salida}")


# ---------------------------------------------------------------------------------------------------------------------
# Nuevo bloque
# ---------------------------------------------------------------------------------------------------------------------
LUGAR = {"centro": "común a todos los ciclos del centro", "ciclo": "del ciclo, para todos los cursos",
         "normativo": "del ciclo, para todos los cursos", "anual": "solo de este curso"}


class DialogoNuevoBloque(QDialog):
    def __init__(self, ctx, n: int, tipos: list[str], padre=None, nombre: str = "", explicacion: str = ""):
        super().__init__(padre)
        self.ctx = ctx
        self.n = n
        self.bloque = None
        capa = _base(self, "Añadir bloque", 520, 300)
        capa.addWidget(etiqueta(explicacion or f"Apartado {n}. El bloque empieza vacío y en borrador.", "muted",
                                envolver=True))
        form = QFormLayout()
        self.tipo = QComboBox()
        for t in tipos:
            self.tipo.addItem(f"{t} · {LUGAR.get(t, '')}", t)
        self.nombre = QLineEdit()
        self.nombre.setPlaceholderText("p. ej. metodologia-taller")
        self.nombre.setText(nombre)
        self.autor = QLineEdit()
        self.autor.setPlaceholderText("Equipo docente, departamento…")
        form.addRow("Tipo", self.tipo)
        form.addRow("Nombre del archivo", self.nombre)
        form.addRow("Aportado por", self.autor)
        capa.addLayout(form)
        capa.addStretch(1)
        botones = QHBoxLayout()
        botones.addStretch(1)
        cancelar = boton("Cancelar")
        cancelar.clicked.connect(self.reject)
        botones.addWidget(cancelar)
        crear = boton("Añadir", primario=True)
        crear.clicked.connect(self.crear)
        botones.addWidget(crear)
        capa.addLayout(botones)

    def crear(self) -> None:
        if not self.autor.text().strip():
            QMessageBox.warning(self, "Añadir bloque", "Di quién aporta el bloque")
            return
        try:
            self.bloque = self.ctx.datos.nuevo_bloque(self.ctx.sigla, self.ctx.curso, self.n, self.tipo.currentData(),
                                                      self.nombre.text(), self.autor.text(), self.ctx.hoy())
        except (DatosNoValidos, FileExistsError, OSError) as e:
            QMessageBox.warning(self, "Añadir bloque", str(e))
            return
        self.accept()


# ---------------------------------------------------------------------------------------------------------------------
# Espera
# ---------------------------------------------------------------------------------------------------------------------
class DialogoEspera(QDialog):
    """«Preparando el documento…» mientras trabaja una `Tarea` (no se cierra a mano)."""

    def __init__(self, texto: str, padre=None):
        super().__init__(padre)
        self.setWindowTitle("PCCF")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        capa = QVBoxLayout(self)
        capa.setContentsMargins(26, 22, 26, 22)
        self.texto = etiqueta(texto)
        self.texto.setFont(estilo.fuente(16, QFont.Weight.DemiBold))
        capa.addWidget(self.texto)
        barra = QProgressBar()
        barra.setRange(0, 0)
        capa.addWidget(barra)
        capa.addWidget(etiqueta("El PDF lo hace el Word del equipo (o LibreOffice): puede tardar medio minuto.",
                                "pequeno", envolver=True))
        self.setFixedWidth(420)

    def reject(self):  # noqa: D401 - Esc no la cierra
        pass
