"""PDF del PCCF con el Word del equipo o, si no hay, con LibreOffice sin interfaz (ARCHITECTURE.md §1). Copia del de
Programaciones (`src/programaciones/pdf.py`), sin ONLYOFFICE.

- Word: AppleScript en macOS y COM (PowerShell) en Windows. El documento llega sin `updateFields` (con él, Word pregunta
  si actualiza los campos y se queda esperando) y se actualizan aquí los campos del cuerpo (las páginas del contenido,
  `PAGEREF`); los del encabezado y el pie (página, total, título del apartado) los pone Word al paginar. En macOS se
  convierte en una carpeta fija de la app, para que Word pida permiso solo la primera vez.
- LibreOffice: `soffice --headless --convert-to pdf` con un perfil propio y temporal, para no chocar con uno abierto.
- Siempre con tiempo máximo y un error claro.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from pccf import ooxml
from pccf.ooxml import W

TIEMPO_MAX = 180   # segundos
RUTAS_SOFFICE = ["/Applications/LibreOffice.app/Contents/MacOS/soffice",
                 r"C:\Program Files\LibreOffice\program\soffice.exe",
                 r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"]
SIN_PROGRAMA = ("En este equipo no hay Word de escritorio ni LibreOffice para hacer el PDF. Instala LibreOffice (gratis, "
                "en libreoffice.org) y vuelve a probar; mientras, el Word (.docx) sí se exporta.")
AYUDA_PERMISO_WORD = ("Si Word ha pedido «Conceder acceso al archivo», pulsa «Seleccionar…» y después «Conceder "
                      "acceso»: solo lo pide la primera vez.")


class ErrorPDF(RuntimeError):
    """No se ha podido hacer el PDF (sin Word ni LibreOffice, tiempo agotado o error del programa)."""


def soffice() -> str | None:
    for nombre in ("soffice", "libreoffice"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    return next((r for r in RUTAS_SOFFICE if Path(r).is_file()), None)


def hay_word() -> bool:
    if sys.platform == "darwin":
        return Path("/Applications/Microsoft Word.app").is_dir()
    if sys.platform.startswith("win"):
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"):
                return True
        except OSError:
            return False
    return False


def motores() -> list[str]:
    """Los programas para el PDF que hay en este equipo, en el orden en que «auto» los prueba."""
    return (["word"] if hay_word() else []) + (["libreoffice"] if soffice() else [])


def _ejecutar(orden: list[str], tiempo_max: int) -> None:
    try:
        r = subprocess.run(orden, capture_output=True, text=True, timeout=tiempo_max)
    except subprocess.TimeoutExpired as e:
        raise ErrorPDF(f"El PDF tarda más de {tiempo_max} s: se cancela") from e
    except OSError as e:
        raise ErrorPDF(f"No se puede ejecutar {Path(orden[0]).name}: {e}") from e
    if r.returncode != 0:
        raise ErrorPDF(f"{Path(orden[0]).name} ha fallado: {(r.stderr or r.stdout).strip()[:300]}")


def con_libreoffice(docx: Path, pdf: Path, tiempo_max: int = TIEMPO_MAX) -> Path:
    programa = soffice()
    if not programa:
        raise ErrorPDF("No hay LibreOffice en este equipo")
    with tempfile.TemporaryDirectory(prefix="pccf-lo-") as tmp:
        perfil = Path(tmp) / "perfil"
        salida = Path(tmp) / "salida"
        salida.mkdir()
        _ejecutar([programa, f"-env:UserInstallation={perfil.as_uri()}", "--headless", "--convert-to", "pdf",
                   "--outdir", str(salida), str(docx)], tiempo_max)
        hechos = list(salida.iterdir())
        if not hechos:
            raise ErrorPDF("LibreOffice no ha escrito el archivo")
        pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(hechos[0]), pdf)
    return pdf


#: Como el de Programaciones: espera a que Word tenga el documento, actualiza los campos del cuerpo, guarda en PDF con
#: reintentos y cierra sin guardar. Si Word no estaba abierto, se arranca sin traerlo al frente y se cierra al terminar.
APPLESCRIPT = '''on run argv
  set entrada to POSIX file (item 1 of argv)
  set salida to item 2 of argv
  set nombre to item 3 of argv
  set estaba to application "Microsoft Word" is running
  if not estaba then launch application "Microsoft Word"
  tell application "Microsoft Word"
    open entrada add to recent files false
    set k to 0
    repeat until (exists document nombre)
      set k to k + 1
      if k > 120 then error "Word no ha abierto el documento"
      delay 0.5
    end repeat
    set d to document nombre
    try
      repeat with f in (fields of d)
        update field f
      end repeat
    end try
    set fallo to ""
    repeat 20 times
      try
        save as d file name salida file format format PDF
        set fallo to ""
        exit repeat
      on error e
        set fallo to e
        delay 0.5
      end try
    end repeat
    try
      close d saving no
    end try
    if not estaba and (count of documents) = 0 then quit saving no
    if fallo is not "" then error fallo
  end tell
end run'''

POWERSHELL = ("$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
              "try {{ $d = $w.Documents.Open('{entrada}', $false, $true); $d.Fields.Update() | Out-Null; "
              "$d.SaveAs([ref]'{salida}', [ref]17); $d.Close($false) }} finally {{ $w.Quit() }}")


def sin_actualizar_campos(docx: bytes) -> bytes:
    """El .docx sin `w:updateFields`, para Word: con él, Word pregunta al abrirlo si actualiza los campos."""
    pq = ooxml.Paquete.desde_docx(docx)
    ajustes = pq.xml("word/settings.xml")
    for uf in ajustes.findall(W + "updateFields"):
        ajustes.remove(uf)
    return pq.a_bytes()


def con_word(docx: Path, pdf: Path, tiempo_max: int = TIEMPO_MAX) -> Path:
    if sys.platform == "darwin":
        try:
            _ejecutar(["osascript", "-e", APPLESCRIPT, str(docx.resolve()), str(pdf.resolve()), docx.name], tiempo_max)
        except ErrorPDF as e:
            raise ErrorPDF(f"{e}. {AYUDA_PERMISO_WORD}") from e
    elif sys.platform.startswith("win"):
        orden = POWERSHELL.format(entrada=str(docx.resolve()).replace("'", "''"),
                                  salida=str(pdf.resolve()).replace("'", "''"))
        _ejecutar(["powershell", "-NoProfile", "-NonInteractive", "-Command", orden], tiempo_max)
    else:
        raise ErrorPDF("Word solo está en macOS y Windows")
    if not pdf.is_file():
        raise ErrorPDF("Word no ha escrito el PDF")
    return pdf


def carpeta_de_trabajo(usa_word: bool) -> Path | None:
    """En macOS con Word, una carpeta fija de la app (Word va aislado y pide permiso por cada carpeta nueva)."""
    if usa_word and sys.platform == "darwin":
        from pccf.rutas import carpeta_app

        carpeta = carpeta_app() / "conversion"
        carpeta.mkdir(parents=True, exist_ok=True)
        return carpeta
    return None


def exportar_pdf(docx: bytes, pdf: Path, motor: str = "auto", tiempo_max: int = TIEMPO_MAX) -> Path:
    """PDF del PCCF. `motor`: «auto» (Word y, si falla o no está, LibreOffice), «word» o «libreoffice»."""
    pdf = Path(pdf)
    disponibles = motores()
    orden = disponibles if motor == "auto" else [motor]
    if not orden:
        raise ErrorPDF(SIN_PROGRAMA)
    errores = []
    for m in orden:
        fija = carpeta_de_trabajo(m == "word")
        with tempfile.TemporaryDirectory(prefix="pccf-pdf-") as tmp:
            base = fija / f"{pdf.stem}-{uuid.uuid4().hex[:8]}" if fija else Path(tmp) / pdf.stem
            entrada, salida = Path(f"{base}.docx"), Path(f"{base}.pdf")
            try:
                entrada.write_bytes(sin_actualizar_campos(docx) if m == "word" else docx)
                hecho = (con_word if m == "word" else con_libreoffice)(entrada, salida, tiempo_max)
                pdf.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(hecho), pdf)
                os.utime(pdf)
                return pdf
            except ErrorPDF as e:
                errores.append(str(e))
            finally:
                entrada.unlink(missing_ok=True)
                salida.unlink(missing_ok=True)
    raise ErrorPDF("; ".join(errores))
