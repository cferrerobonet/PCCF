"""Aspecto de la familia de apps (copia de `ui/estilo.py` de Programaciones, DESIGN.md): tipografías, colores claro
y oscuro, hoja de estilos e iconos dibujados. Todo color de la interfaz sale de `T[...]` (The Token Rule)."""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QIcon,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
)

from pccf.rutas import recursos

CUERPO = "Barlow"
TITULAR = "Barlow Condensed"
MONO = "JetBrains Mono"

CLARO = {
    "bg": "#f3f5f1", "surface": "#ffffff", "surface2": "#eef2ec", "line": "#d9e0d5",
    "fg": "#1d2a20", "muted": "#5d6b60", "accent": "#2c7a3a", "accent_ink": "#ffffff",
    "accent_soft": "#e2f0e3", "gold": "#b97a12", "gold_soft": "#fbf0d9",
    "warn": "#9a5b00", "warn_soft": "#fff3dc", "danger": "#a32d2d",
    "azul": "#2f5d8a", "azul_soft": "#e4edf6",
}
OSCURO = {
    "bg": "#121713", "surface": "#1a211c", "surface2": "#222b24", "line": "#323d35",
    "fg": "#e4ebe5", "muted": "#9aa89d", "accent": "#5fbf6e", "accent_ink": "#0d1a10",
    "accent_soft": "#1f3524", "gold": "#e3a94a", "gold_soft": "#3a2e17",
    "warn": "#f0b45a", "warn_soft": "#3a2c14", "danger": "#f08a8a",
    "azul": "#8fb6de", "azul_soft": "#1c2a38",
}

T: dict[str, str] = dict(CLARO)


def cargar_fuentes() -> None:
    for f in sorted((recursos() / "fuentes").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(f))


def es_oscuro() -> bool:
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        return False


def fuente(tam: float, peso: QFont.Weight = QFont.Weight.Normal, familia: str = CUERPO) -> QFont:
    f = QFont(familia)
    f.setPixelSize(round(tam))
    f.setWeight(peso)
    return f


def etiqueta_fuente(tam: float = 12) -> QFont:
    f = fuente(tam, QFont.Weight.Bold)
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.9)
    f.setCapitalization(QFont.Capitalization.AllUppercase)
    return f


def hoja(t: dict[str, str]) -> str:
    return f"""
QMainWindow, QDialog, QWidget#raiz {{ background: {t['bg']}; }}
QWidget#lienzo {{ background: {t['surface']}; border: 1px solid {t['line']}; border-radius: 12px; }}
QWidget#barra {{ background: {t['surface2']}; border-bottom: 1px solid {t['line']};
  border-top-left-radius: 12px; border-top-right-radius: 12px; }}
QFrame#separador {{ background: {t['line']}; }}
QLabel {{ background: transparent; }}
QLabel[rol="muted"] {{ color: {t['muted']}; font-size: 13px; }}
QLabel[rol="pequeno"] {{ color: {t['muted']}; font-size: 12px; }}
QLabel[rol="etiqueta"] {{ color: {t['muted']}; }}
QLabel[rol="ok"] {{ color: {t['accent']}; font-weight: 600; }}
QLabel[rol="aviso-texto"] {{ color: {t['warn']}; font-weight: 600; }}
QLabel[rol="mono"] {{ font-family: "{MONO}"; font-size: 14px; }}
QLabel[rol="titulo-vacio"] {{ color: {t['fg']}; }}
QLabel[rol="tag-etapa"] {{ background: {t['gold_soft']}; color: {t['gold']}; font-weight: 600;
  font-size: 13px; padding: 3px 9px; border-radius: 5px; }}
QLabel[rol="tag"] {{ background: {t['surface2']}; font-weight: 600; font-size: 13px; padding: 3px 9px; border-radius: 5px; }}
QLabel[rol="aviso"] {{ background: {t['warn_soft']}; color: {t['warn']}; font-size: 13px; padding: 7px 9px; border-radius: 7px; }}
QLabel[rol="pendiente"] {{ background: {t['warn_soft']}; color: {t['warn']}; font-weight: 600; border-radius: 8px; }}
QLabel[rol="tel"] {{ font-family: "{MONO}"; font-size: 14px; }}
QLabel[rol="correo"] {{ color: {t['muted']}; font-size: 13px; }}
QFrame[rol="caja"] {{ background: {t['surface']}; border: 1px solid {t['line']}; border-radius: 10px; }}
QFrame[rol="fila"] {{ border: 0; border-top: 1px solid {t['line']}; border-radius: 0; background: transparent; }}
QFrame[rol="soltar"] {{ border: 1.5px dashed {t['line']}; border-radius: 10px; background: {t['surface']}; }}
QFrame[rol="soltar"][encima="true"] {{ border-color: {t['accent']}; background: {t['accent_soft']}; }}
QFrame[rol="dato"] {{ border: 1px solid {t['line']}; border-radius: 8px; background: {t['surface']}; }}
QFrame[rol="miniatura"] {{ border: 1px dashed {t['line']}; border-radius: 8px; background: #ffffff; }}
QLineEdit, QComboBox, QTimeEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit {{
  background: {t['bg']}; border: 1px solid {t['line']}; border-radius: 7px; padding: 6px 9px;
  selection-background-color: {t['accent']}; selection-color: {t['accent_ink']}; }}
QLineEdit:focus, QComboBox:focus, QTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus {{
  border: 1px solid {t['accent']}; }}
QLineEdit#buscador {{ padding: 9px 10px; font-size: 15px; border-radius: 8px; }}
QComboBox QAbstractItemView {{ background: {t['surface']}; border: 1px solid {t['line']};
  selection-background-color: {t['accent_soft']}; selection-color: {t['fg']}; }}
QTimeEdit#hora {{ font-family: "{TITULAR}"; font-size: 40px; font-weight: 700; padding: 2px 12px; }}
QPushButton {{ background: {t['surface']}; border: 1px solid {t['line']}; border-radius: 8px;
  padding: 7px 13px; font-weight: 600; }}
QPushButton:hover {{ border-color: {t['accent']}; }}
QPushButton:pressed {{ background: {t['surface2']}; }}
QPushButton:disabled {{ color: {t['muted']}; }}
QPushButton[pequeno="true"] {{ font-size: 13px; padding: 4px 10px; border-radius: 7px; }}
QPushButton[peligro="true"] {{ color: {t['danger']}; }}
QPushButton[dorado="true"] {{ background: {t['gold']}; border-color: {t['gold']}; color: #ffffff; }}
QPushButton[dorado="true"]:hover {{ border-color: {t['fg']}; }}
QPushButton[primario="true"] {{ background: {t['accent']}; border-color: {t['accent']}; color: {t['accent_ink']}; }}
QPushButton[primario="true"]:hover {{ background: {t['accent']}; border-color: {t['fg']}; }}
QPushButton[primario="true"]:disabled {{ background: {t['line']}; border-color: {t['line']}; color: {t['muted']}; }}
QPushButton[grande="true"] {{ font-size: 18px; padding: 14px 16px; border-radius: 10px; }}
QPushButton[chip="true"] {{ font-size: 13px; padding: 4px 11px; border-radius: 13px; }}
QPushButton[chip="true"]:checked {{ background: {t['accent']}; border-color: {t['accent']}; color: {t['accent_ink']}; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {t['line']}; border-radius: 4px; background: {t['surface']}; }}
QCheckBox::indicator:checked {{ background: {t['accent']}; border-color: {t['accent']}; image: url(:/marca); }}
QCheckBox::indicator:disabled {{ background: {t['surface2']}; }}
QCheckBox:disabled {{ color: {t['muted']}; }}
QListView#resultados {{ background: transparent; border: 0; outline: 0; }}
QListWidget#navegacion {{ background: {t['surface2']}; border: 0; border-right: 1px solid {t['line']};
  padding: 10px; outline: 0; }}
QListWidget#navegacion::item {{ padding: 0 10px; border-radius: 7px; font-weight: 600; margin-bottom: 2px; }}
QListWidget#navegacion::item:selected {{ background: {t['surface']}; color: {t['accent']}; border: 1px solid {t['line']}; }}
QListWidget {{ background: {t['surface']}; border: 1px solid {t['line']}; border-radius: 8px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {t['line']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollArea {{ background: transparent; border: 0; }}
QToolTip {{ background: {t['fg']}; color: {t['bg']}; border: 0; padding: 5px 8px; }}
QProgressBar {{ border: 1px solid {t['line']}; border-radius: 6px; background: {t['surface2']}; text-align: center; height: 14px; }}
QProgressBar::chunk {{ background: {t['accent']}; border-radius: 5px; }}
QLabel#aviso_flotante {{ background: {t['fg']}; color: {t['bg']}; padding: 10px 16px; border-radius: 9px; font-weight: 600; }}
QLabel[rol="rojo"] {{ color: {t['danger']}; }}
QLabel[rol="ra"] {{ color: {t['accent']}; font-family: "{MONO}"; font-weight: 700; font-size: 14px; }}
QLabel[rol="letra"] {{ border: 1px solid {t['line']}; border-radius: 4px; background: {t['surface']};
  font-family: "{MONO}"; font-size: 12px; padding: 0 4px; }}
QLabel[rol="codigo"] {{ color: {t['gold']}; }}
QLabel[rol="cifra"] {{ color: {t['fg']}; }}
QLabel[rol="info"] {{ background: {t['gold_soft']}; color: {t['warn']}; font-size: 13px; padding: 9px 12px;
  border-radius: 8px; }}
QLabel[rol="miniatura"] {{ border: 1px solid {t['line']}; background: {t['surface2']}; color: {t['muted']}; }}
QFrame[rol="curriculo"] {{ background: {t['surface2']}; border: 1px solid {t['line']}; border-radius: 10px; }}
QFrame[rol="codigo"] {{ background: {t['gold_soft']}; border: 0; border-radius: 12px; }}
QFrame[rol="banda"] {{ background: {t['warn_soft']}; border: 0; border-top-left-radius: 10px;
  border-top-right-radius: 10px; }}
QLabel[rol="banda"] {{ color: {t['warn']}; font-size: 14px; }}
QFrame[rol="aviso-roja"] {{ border: 1px solid {t['danger']}; border-radius: 8px; background: {t['surface']}; }}
QFrame[rol="aviso-ambar"] {{ border: 1px solid {t['warn']}; border-radius: 8px; background: {t['warn_soft']}; }}
QFrame[rol="dato"] QLabel {{ border: 0; }}
QPushButton[enlace="true"] {{ background: transparent; border: 0; padding: 2px 4px; font-weight: 700; }}
QPushButton[verde="true"] {{ color: {t['accent']}; }}
QLabel[tipo="centro"] {{ background: {t['surface2']}; color: {t['muted']}; border: 1px solid {t['line']}; }}
QLabel[tipo="ciclo"] {{ background: {t['accent_soft']}; color: {t['accent']}; border: 1px solid {t['accent_soft']}; }}
QLabel[tipo="anual"] {{ background: {t['gold_soft']}; color: {t['gold']}; border: 1px solid {t['gold_soft']}; }}
QLabel[tipo="normativo"] {{ background: {t['azul_soft']}; color: {t['azul']}; border: 1px solid {t['azul_soft']}; }}
QLabel[tipo="derivado"] {{ background: {t['surface']}; color: {t['fg']}; border: 1px solid {t['line']};
  font-family: "{MONO}"; }}
QLabel[tipo] {{ font-weight: 600; font-size: 12px; padding: 1px 7px; border-radius: 5px; }}
QLabel[tipo="cita"] {{ background: {t['azul_soft']}; color: {t['azul']}; font-family: "{MONO}"; font-size: 12px;
  font-weight: 500; }}
QLabel[rol="numero"] {{ background: {t['gold_soft']}; color: {t['gold']}; border-radius: 6px; }}
QLabel[rol="estado-confirmado"] {{ color: {t['accent']}; font-weight: 600; }}
QLabel[rol="estado-borrador"], QLabel[rol="estado-heredado"] {{ color: {t['gold']}; font-weight: 600; }}
QLabel[rol="estado-revisar"] {{ color: {t['warn']}; font-weight: 600; }}
QLabel[rol="estado-pendiente"] {{ color: {t['muted']}; font-weight: 600; }}
QLabel[rol="mas"] {{ color: {t['accent']}; font-weight: 700; }}
QLabel[rol="menos"] {{ color: {t['danger']}; font-weight: 700; }}
QFrame[rol="bloque"] {{ background: {t['surface']}; border: 1px solid {t['line']}; border-radius: 10px; }}
QFrame[rol="bloque"][heredado="true"] {{ border-color: {t['gold']}; }}
QFrame[rol="nuevo"] {{ background: transparent; border: 1.5px dashed {t['line']}; border-radius: 10px; }}
QFrame[rol="guia"] {{ background: {t['surface2']}; border: 1px solid {t['line']}; border-radius: 10px; }}
QFrame[rol="aviso-vigia"] {{ background: {t['gold_soft']}; border: 1px solid {t['gold']}; border-radius: 9px; }}
QLabel[rol="aviso-vigia"] {{ color: {t['warn']}; font-weight: 600; }}
QPushButton[aviso="true"] {{ background: {t['gold_soft']}; border-color: {t['gold']}; color: {t['warn']}; }}
QPushButton[ok="true"] {{ background: transparent; border-color: transparent; color: {t['accent']}; }}
QPushButton[ciclo="true"] {{ text-align: left; padding: 8px 12px; border-radius: 10px; }}
QPushButton[formato="true"] {{ font-size: 13px; padding: 4px 14px; border-radius: 13px; }}
QPushButton[formato="true"]:checked {{ background: {t['accent']}; border-color: {t['accent']}; color: {t['accent_ink']}; }}
QPlainTextEdit#editor {{ background: {t['surface']}; border: 1px solid {t['line']}; border-radius: 8px; padding: 8px 10px;
  font-size: 14px; }}
QListWidget#apartados {{ background: transparent; border: 0; outline: 0; }}
QListWidget#apartados::item {{ border-radius: 8px; margin: 1px 0; }}
QListWidget#apartados::item:selected {{ background: {t['accent_soft']}; color: {t['fg']}; }}
QListWidget#apartados::item:hover {{ background: {t['surface2']}; }}
QListWidget#ciclos {{ background: {t['surface']}; border: 0; outline: 0; }}
QListWidget#ciclos::item {{ border-radius: 6px; padding: 3px 6px; }}
QListWidget#ciclos::item:selected {{ background: {t['accent_soft']}; color: {t['fg']}; }}
QFrame#popup {{ background: {t['surface']}; border: 1px solid {t['line']}; border-radius: 10px; }}
QPushButton[enlace="true"]:hover {{ color: {t['accent']}; }}
QPushButton[paso="actual"] {{ background: {t['accent']}; border-color: {t['accent']}; color: {t['accent_ink']}; }}
QPushButton[paso="confirmado"] {{ color: {t['accent']}; }}
QPushButton[paso="heredado"] {{ background: {t['warn_soft']}; border-color: {t['warn_soft']}; color: {t['warn']}; }}
QTableWidget {{ background: {t['surface']}; border: 0; gridline-color: {t['line']};
  selection-background-color: {t['accent_soft']}; selection-color: {t['fg']}; }}
QHeaderView::section {{ background: {t['surface']}; color: {t['muted']}; border: 0; border-bottom: 1px solid {t['line']};
  padding: 5px 4px; font-weight: 600; }}
QListWidget#modulos {{ background: transparent; border: 0; outline: 0; }}
QListWidget#modulos::item {{ border-radius: 8px; margin: 1px 0; }}
QListWidget#modulos::item:selected {{ background: {t['accent_soft']}; color: {t['fg']}; }}
QListWidget#modulos::item:hover {{ background: {t['surface2']}; }}
"""


def aplicar(app) -> None:
    from PyQt6.QtCore import QDir

    T.clear()
    T.update(OSCURO if es_oscuro() else CLARO)
    app.setStyle("Fusion")
    pal = app.palette()
    for rol, clave in (
        (QPalette.ColorRole.Window, "bg"),
        (QPalette.ColorRole.Base, "surface"),
        (QPalette.ColorRole.AlternateBase, "surface2"),
        (QPalette.ColorRole.Text, "fg"),
        (QPalette.ColorRole.WindowText, "fg"),
        (QPalette.ColorRole.ButtonText, "fg"),
        (QPalette.ColorRole.Button, "surface"),
        (QPalette.ColorRole.Highlight, "accent"),
        (QPalette.ColorRole.HighlightedText, "accent_ink"),
        (QPalette.ColorRole.PlaceholderText, "muted"),
    ):
        pal.setColor(rol, QColor(T[clave]))
    app.setPalette(pal)
    marca = _marca()
    QDir.addSearchPath("icono", str(marca.parent))
    app.setStyleSheet(hoja(T).replace("url(:/marca)", f"url('{marca.as_posix()}')"))
    app.setFont(fuente(14))


def _marca():
    """La marca blanca de las casillas, dibujada una vez en la carpeta temporal."""
    import tempfile
    from pathlib import Path

    ruta = Path(tempfile.gettempdir()) / "pccf-marca.png"
    if not ruta.exists():
        pm = QPixmap(32, 32)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#ffffff"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPolyline([QPointF(7, 17), QPointF(13, 23), QPointF(25, 9)])
        p.end()
        pm.save(str(ruta))
    return ruta


def icono_lupa(color: str, tam: int = 18) -> QIcon:
    pm = QPixmap(tam * 2, tam * 2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), 3.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawEllipse(QRectF(5, 5, tam * 1.15, tam * 1.15))
    p.drawLine(QPointF(tam * 1.32, tam * 1.32), QPointF(tam * 1.8, tam * 1.8))
    p.end()
    return QIcon(pm)


def _lienzo(tam: int) -> tuple[QPixmap, QPainter]:
    pm = QPixmap(tam * 2, tam * 2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    return pm, p


def _terminar(pm: QPixmap, p: QPainter) -> QPixmap:
    p.end()
    pm.setDevicePixelRatio(2)
    return pm


def icono_documento(color: str, tam: int = 22) -> QPixmap:
    """Hoja con la esquina doblada y dos renglones: estados vacíos y miniatura de la vista previa."""
    pm, p = _lienzo(tam)
    s = tam * 2
    p.setPen(QPen(QColor(color), s * 0.07, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    x0, x1, y0, y1, d = s * 0.2, s * 0.8, s * 0.08, s * 0.92, s * 0.2
    p.drawPolyline([QPointF(x1 - d, y0), QPointF(x0, y0), QPointF(x0, y1), QPointF(x1, y1), QPointF(x1, y0 + d),
                    QPointF(x1 - d, y0), QPointF(x1 - d, y0 + d), QPointF(x1, y0 + d)])
    for y in (0.55, 0.72):
        p.drawLine(QPointF(s * 0.36, s * y), QPointF(s * 0.64, s * y))
    return _terminar(pm, p)


def icono_estrella(color: str, tam: int = 16, llena: bool = False) -> QPixmap:
    """Estrella de cinco puntas: rellena para un módulo favorito, solo el contorno si no lo es."""
    pm, p = _lienzo(tam)
    s = tam * 2
    c, r_ext, r_int = s / 2, s * 0.46, s * 0.19
    puntos = [QPointF(c + (r_ext if i % 2 == 0 else r_int) * math.sin(i * math.pi / 5),
                      c * 1.06 - (r_ext if i % 2 == 0 else r_int) * math.cos(i * math.pi / 5)) for i in range(10)]
    p.setPen(QPen(QColor(color), s * 0.07, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(QColor(color) if llena else Qt.BrushStyle.NoBrush)
    p.drawPolygon(puntos)
    return _terminar(pm, p)


def icono_visto(color: str, tam: int = 16, circulo: bool = False) -> QPixmap:
    """Marca de visto bueno; con `circulo`, dentro de un círculo («Catálogo al día»)."""
    pm, p = _lienzo(tam)
    s = tam * 2
    p.setPen(QPen(QColor(color), s * 0.11, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    if circulo:
        p.drawEllipse(QRectF(s * 0.08, s * 0.08, s * 0.84, s * 0.84))
        p.drawPolyline([QPointF(s * 0.32, s * 0.52), QPointF(s * 0.45, s * 0.65), QPointF(s * 0.69, s * 0.38)])
    else:
        p.drawPolyline([QPointF(s * 0.16, s * 0.54), QPointF(s * 0.4, s * 0.78), QPointF(s * 0.86, s * 0.24)])
    return _terminar(pm, p)


#: Estado de un bloque o de una programación → (token del color, forma). DESIGN.md: verde confirmado, ámbar heredado
#: o en curso, vacío sin empezar.
ESTADOS = {
    "vacio": ("line", "anillo"),
    "pendiente": ("muted", "anillo"),
    "heredado": ("warn", "punto"),
    "borrador": ("warn", "punto"),
    "en_curso": ("warn", "punto"),
    "revisar": ("warn", "alerta"),
    "confirmado": ("accent", "visto"),
    "exportada": ("accent", "visto"),
}


def icono_estado(estado: str, tam: int = 16) -> QPixmap:
    color, forma = ESTADOS.get(estado, ESTADOS["vacio"])
    if forma == "visto":
        return icono_visto(T[color], tam)
    pm, p = _lienzo(tam)
    s = tam * 2
    if forma == "alerta":
        p.setPen(QPen(QColor(T[color]), s * 0.13, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(s / 2, s * 0.16), QPointF(s / 2, s * 0.6))
        p.drawPoint(QPointF(s / 2, s * 0.84))
    elif forma == "anillo":
        p.setPen(QPen(QColor(T[color]), s * 0.08))
        p.drawEllipse(QRectF(s * 0.1, s * 0.1, s * 0.8, s * 0.8))
    else:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(T["warn_soft"]))
        p.drawEllipse(QRectF(s * 0.05, s * 0.05, s * 0.9, s * 0.9))
        p.setBrush(QColor(T[color]))
        p.drawEllipse(QRectF(s * 0.36, s * 0.36, s * 0.28, s * 0.28))
    return _terminar(pm, p)
