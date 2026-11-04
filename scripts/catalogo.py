"""El catálogo que va dentro de la app compilada (ARCHITECTURE.md §6): el último publicado y firmado por Programaciones.

  python scripts/catalogo.py bajar [carpeta]      baja, verifica (firma, sha256, huella) y lo deja en la carpeta
                                                  (por defecto, `catalogo/` del repositorio, que no se versiona)
  python scripts/catalogo.py comprobar [carpeta]  que la carpeta es un catálogo completo y coherente

Lo ejecuta la compilación de GitHub antes de PyInstaller. Si algo no cuadra, para con un error: la app no se compila con
un catálogo sin verificar.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from pccf import catalogo_remoto as cr  # noqa: E402


def bajar(destino: Path) -> str:
    indice = cr.leer_indice(cr.bajar(cr.URL_INDICE, cr.MAX_INDICE))
    v = indice["version"]
    paquete = cr.bajar(cr.URL_BASE + indice["archivo"], cr.MAX_PAQUETE)
    with tempfile.TemporaryDirectory(prefix="pccf-catalogo-") as tmp:
        hecho = cr.desempaquetar(paquete, indice["sha256"], v, Path(tmp))
        shutil.rmtree(destino, ignore_errors=True)
        shutil.copytree(hecho, destino)
    cr.comprobar_carpeta(destino, v)
    return v


def main(args: list[str]) -> int:
    if not args or args[0] not in ("bajar", "comprobar"):
        print(__doc__)
        return 2
    carpeta = Path(args[1]) if len(args) > 1 else RAIZ / "catalogo"
    try:
        if args[0] == "bajar":
            print(f"Catálogo {bajar(carpeta)} verificado en {carpeta}")
        else:
            print(f"Catálogo {cr.comprobar_carpeta(carpeta).version} correcto en {carpeta}")
    except cr.CatalogoNoValido as e:
        print(f"Catálogo no válido: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
