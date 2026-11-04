"""Sin argumentos, abre la interfaz. Uso sin interfaz:
  python -m pccf generar <SIGLA> <curso> [salida.docx]
  python -m pccf comprobar <SIGLA> <curso>
  python -m pccf vigia <SIGLA> <curso> [--revisado]
  python -m pccf nuevo-curso <SIGLA> <curso de partida> [curso nuevo]
  python -m pccf comparar <SIGLA> <curso>[@etiqueta] <curso>[@etiqueta]

La carpeta de datos es `PCCF_DATOS` o, en desarrollo, `../PCCF - DATOS/`; el catálogo, el de Programaciones. Sin
salida, el Word y los informes van a `salidas/` de la carpeta de datos (fuera de git). `vigia --revisado` da por
revisado lo que dice hoy el catálogo: es el punto de partida de la próxima revisión. `nuevo-curso` copia el curso de
partida del ciclo (el siguiente, si no se dice) con lo anual como heredado y pasa el vigía. `comparar` compara dos
cursos, o un curso en una versión aprobada (etiqueta de git de la carpeta de datos), apartado por apartado."""
from __future__ import annotations

import sys
from pathlib import Path

from pccf import cursos, documento, vigia
from pccf.catalogo import Catalogo
from pccf.datos import CarpetaDatos, DatosNoValidos


def main(args: list[str]) -> int:
    if not args:
        from pccf.app import main as interfaz

        return interfaz()
    if len(args) < 3 or args[0] not in ("generar", "comprobar", "vigia", "nuevo-curso", "comparar") \
            or (args[0] == "comparar" and len(args) < 4):
        print(__doc__)
        return 2
    orden, sigla, curso = args[:3]
    datos = CarpetaDatos()
    try:
        if orden == "nuevo-curso":
            return _nuevo_curso(Catalogo(), datos, sigla, curso, args[3] if len(args) > 3 else None)
        if orden == "comparar":
            return _comparar(Catalogo(), datos, sigla, curso, args[3])
    except (cursos.CursoNoValido, FileNotFoundError, FileExistsError, DatosNoValidos) as e:
        print(e)
        return 1
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


def _nuevo_curso(cat: Catalogo, datos: CarpetaDatos, sigla: str, origen: str, destino: str | None) -> int:
    res = cursos.nuevo_curso(cat, datos, sigla, origen, destino)
    destino = res.carpeta.parent.name
    print(f"Creado {sigla} {destino}: {res.carpeta}")
    print(f"Heredado, en borrador hasta confirmarlo: {', '.join(res.heredados) or 'nada'}")
    for a in res.avisos:
        print(f"  · {a}")
    print()
    return _vigia(cat, datos, sigla, destino, False)


def _comparar(cat: Catalogo, datos: CarpetaDatos, sigla: str, a: str, b: str) -> int:
    md = cursos.markdown(cursos.comparar(cat, datos, sigla, a, b))
    salida = datos.carpeta / "salidas" / cursos.nombre_archivo(sigla, a, b)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(md, encoding="utf-8")
    print(md)
    print(salida)
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
