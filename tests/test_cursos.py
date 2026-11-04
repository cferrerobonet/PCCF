"""«Nuevo curso» y «Comparar», con la carpeta de datos ficticia copiada a una carpeta temporal."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from pccf import __main__ as cli
from pccf import cursos, documento, vigia
from pccf.datos import CarpetaDatos

from .conftest import CURSO, DATOS

NUEVO = "2031-2032"
BLOQUE = """---
tipo: anual
apartado: 13
origen: equipo
estado: confirmado
aportado_por: Prueba
fecha: 2030-01-01
---

Plan ficticio del curso.

Segundo párrafo ficticio.
"""


@pytest.fixture
def con_bloque(carpeta) -> Path:
    b = carpeta / "cursos" / CURSO / "PRU" / "bloques"
    b.mkdir()
    (b / "planes.md").write_text(BLOQUE, encoding="utf-8")
    return carpeta


def _git(carpeta: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(carpeta), "-c", "user.name=Prueba", "-c", "user.email=prueba@example.com",
                    *args], check=True, capture_output=True)


def test_cursos_escolares():
    assert cursos.siguiente("2026-2027") == "2027-2028"
    for malo in ("2026-2028", "2026/2027", "26-27", ""):
        with pytest.raises(cursos.CursoNoValido):
            cursos.siguiente(malo)


def test_nuevo_curso_hereda_lo_anual(cat, con_bloque):
    datos = CarpetaDatos(con_bloque)
    (con_bloque / "cursos" / CURSO / "PRU" / "empresas.yaml").write_text("empresas: []\n", encoding="utf-8")
    vigia.marcar_revisado(cat, datos, "PRU", CURSO)
    res = cursos.nuevo_curso(cat, datos, "PRU", CURSO)
    dst = con_bloque / "cursos" / NUEVO / "PRU"
    assert res.carpeta == dst
    assert sorted(res.heredados) == [f"cursos/{NUEVO}/PRU/bloques/planes.md", f"cursos/{NUEVO}/PRU/equipo.yaml"]
    assert res.copiados == [f"cursos/{NUEVO}/PRU/empresas.yaml"]
    equipo = datos.equipo(NUEVO, "PRU")
    assert (equipo.curso, equipo.estado, equipo.origen) == (NUEVO, "borrador", f"heredado del curso {CURSO}")
    assert equipo.docentes == datos.equipo(CURSO, "PRU").docentes
    [b] = datos.bloques("PRU", NUEVO, 13)
    assert (b.estado, b.origen) == ("borrador", f"heredado del curso {CURSO}")
    assert b.cuerpo == datos.bloques("PRU", CURSO, 13)[0].cuerpo
    assert (dst / "vigia.yaml").read_text(encoding="utf-8").startswith(f"# Lo que el vigía del PCCF dio por revisado "
                                                                        f"de PRU {NUEVO}")
    assert datos.comprobar("PRU", NUEVO) == []
    assert datos.equipo(CURSO, "PRU").estado == "confirmado"           # el de partida, intacto
    assert any("resolución de instrucciones" in a for a in res.avisos)   # el catálogo no tiene la de 2031-2032
    # el primer informe del vigía del curso nuevo ya compara: la resolución del curso anterior sale del marco
    inf = vigia.revisar(cat, datos, "PRU", NUEVO)
    assert inf.anterior and any(c.norma == "DOGV-C-2030-7" for c in inf.cambios)


def test_nuevo_curso_no_sobrescribe_ni_retrocede(cat, datos, carpeta):
    (carpeta / "cursos" / NUEVO / "PRU").mkdir(parents=True)
    with pytest.raises(FileExistsError):
        cursos.nuevo_curso(cat, datos, "PRU", CURSO)
    with pytest.raises(cursos.CursoNoValido):
        cursos.nuevo_curso(cat, datos, "PRU", CURSO, "2029-2030")
    with pytest.raises(FileNotFoundError):
        cursos.nuevo_curso(cat, datos, "PRU", "2020-2021")


def test_word_del_curso_heredado_es_borrador(cat, con_bloque):
    datos = CarpetaDatos(con_bloque)
    cursos.nuevo_curso(cat, datos, "PRU", CURSO)
    res = documento.generar(cat, datos, "PRU", NUEVO)
    assert res.borrador
    assert any("equipo docente sin confirmar (heredado del curso 2030-2031)" in a for a in res.avisos)
    assert any("planes.md» heredado del curso 2030-2031" in a for a in res.avisos)


def test_comparar_dos_cursos(cat, con_bloque):
    datos = CarpetaDatos(con_bloque)
    cursos.nuevo_curso(cat, datos, "PRU", CURSO)
    p = con_bloque / "cursos" / NUEVO / "PRU" / "bloques" / "planes.md"
    p.write_text(p.read_text(encoding="utf-8").replace("Segundo párrafo ficticio.", "Párrafo nuevo."),
                 encoding="utf-8")
    c = cursos.comparar(cat, datos, "PRU", CURSO, NUEVO)
    d = {x.n: x for x in c.apartados}
    assert d[1].anadidas == [f"Equipo docente sin confirmar (heredado del curso {CURSO})"] and not d[1].quitadas
    assert d[2].quitadas and "1 de julio de 2030" in d[2].quitadas[0] and not d[2].anadidas
    assert "Párrafo nuevo." in d[13].anadidas and "Segundo párrafo ficticio." in d[13].quitadas
    assert not d[4].cambia and not d[16].cambia
    md = cursos.markdown(c)
    assert f"# Comparar PCCF PRU · {CURSO} → {NUEVO}" in md
    assert "| 13 · " in md and "| 4 · " not in md and "Sin cambios: 3, 4," in md and "+ Párrafo nuevo." in md


def test_comparar_con_una_version_aprobada(cat, carpeta):
    datos = CarpetaDatos(carpeta)
    _git(carpeta, "init", "-q")
    _git(carpeta, "add", ".")
    _git(carpeta, "commit", "-q", "-m", "versión aprobada")
    _git(carpeta, "tag", "PRU-2030-2031-v1")
    p = carpeta / "centro" / "diversidad.md"
    p.write_text(p.read_text(encoding="utf-8") + "\nOtro párrafo ficticio.\n", encoding="utf-8")
    c = cursos.comparar(cat, datos, "PRU", f"{CURSO}@PRU-2030-2031-v1", CURSO)
    assert c.a == f"{CURSO} (PRU-2030-2031-v1)"
    cambian = [x for x in c.apartados if x.cambia]
    assert [(x.n, x.anadidas, x.quitadas) for x in cambian] == [(16, ["Otro párrafo ficticio."], [])]
    with pytest.raises(cursos.CursoNoValido, match="no tiene la versión"):
        cursos.comparar(cat, datos, "PRU", f"{CURSO}@no-existe", CURSO)


def test_ordenes_nuevo_curso_y_comparar(carpeta, monkeypatch, capsys):
    monkeypatch.setenv("PCCF_CATALOGO", str(DATOS / "catalogo"))
    monkeypatch.setenv("PCCF_DATOS", str(carpeta))
    assert cli.main(["nuevo-curso", "PRU", CURSO]) == 0
    out = capsys.readouterr().out
    assert f"Creado PRU {NUEVO}" in out and "# Vigía del PCCF" in out
    assert cli.main(["nuevo-curso", "PRU", CURSO]) == 1        # ya existe: no se toca
    assert "No se sobrescribe" in capsys.readouterr().out
    assert cli.main(["comparar", "PRU", CURSO, NUEVO]) == 0
    assert (carpeta / "salidas" / f"Comparar PCCF PRU {CURSO} - {NUEVO}.md").is_file()
    assert cli.main(["comparar", "PRU", CURSO]) == 2
    eq = yaml.safe_load((carpeta / "cursos" / NUEVO / "PRU" / "equipo.yaml").read_text(encoding="utf-8"))
    assert eq["estado"] == "borrador"
