"""Uso sin interfaz:
  python -m pccf generar <SIGLA> <curso> [salida.docx]
  python -m pccf comprobar <SIGLA> <curso>
  python -m pccf vigia <SIGLA> <curso> [--revisado]

La carpeta de datos es `PCCF_DATOS` o, en desarrollo, `../PCCF - DATOS/`; el catálogo, el de Programaciones. Sin
salida, el Word y el informe del vigía van a `salidas/` de la carpeta de datos (fuera de git). `vigia --revisado` da
por revisado lo que dice hoy el catálogo: es el punto de partida de la próxima revisión."""
from __future__ import annotations

import sys
from pathlib import Path

from pccf import documento, vigia
from pccf.catalogo import Catalogo
from pccf.datos import CarpetaDatos


def main(args: list[str]) -> int:
    if len(args) < 3 or args[0] not in ("generar", "comprobar", "vigia"):
        print(__doc__)
        return 2
    orden, sigla, curso = args[:3]
    datos = CarpetaDatos()
    errores = datos.comprobar(sigla, curso)
    if errores or orden == "comprobar":
        print("\n".join(errores) or "Carpeta de datos correcta")
        return 1 if errores else 0
    if orden == "vigia":
        return _vigia(Catalogo(), datos, sigla, curso, "--revisado" in args[3:])
    res = documento.generar(Catalogo(), datos, sigla, curso)
    salida = Path(args[3]) if len(args) > 3 else datos.carpeta / "salidas" / documento.nombre_archivo(sigla, curso)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_bytes(res.docx)
    print(f"{salida}{' (BORRADOR)' if res.borrador else ''}")
    for a in res.avisos:
        print(f"  · {a}")
    return 0


def _vigia(cat: Catalogo, datos: CarpetaDatos, sigla: str, curso: str, revisado: bool) -> int:
    if revisado:
        print(f"Revisado: {vigia.marcar_revisado(cat, datos, sigla, curso)}")
        return 0
    inf = vigia.revisar(cat, datos, sigla, curso)
    md = vigia.markdown(inf)
    salida = datos.carpeta / "salidas" / vigia.nombre_archivo(sigla, curso)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(md, encoding="utf-8")
    print(md)
    print(salida)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
