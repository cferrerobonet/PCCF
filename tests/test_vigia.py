"""Índice de citas y vigía del PCCF, con el catálogo ficticio copiado a una carpeta temporal (sin red)."""
from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path

import pytest
import yaml

from pccf import __main__ as cli
from pccf import citas, vigia
from pccf.catalogo import Catalogo
from pccf.datos import CarpetaDatos

from .conftest import CURSO, DATOS

HOY = dt.date(2030, 9, 1)
DESPUES = dt.date(2030, 10, 1)


@pytest.fixture
def carpeta_cat(tmp_path) -> Path:
    destino = tmp_path / "catalogo"
    shutil.copytree(DATOS / "catalogo", destino)
    return destino


def _escribir(p: Path, dato) -> None:
    p.write_text(yaml.safe_dump(dato, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _editar(p: Path, cambiar) -> None:
    dato = yaml.safe_load(p.read_text(encoding="utf-8"))
    cambiar(dato)
    _escribir(p, dato)


def _bloque(carpeta: Path, nombre: str, citas_yaml: str, apartado: int = 16) -> None:
    (carpeta / "centro" / nombre).write_text(
        f"---\ntipo: centro\napartado: {apartado}\norigen: propuesta\nestado: borrador\naportado_por: Prueba\n"
        f"fecha: 2030-01-01\ncitas:\n{citas_yaml}---\n\nTexto ficticio.\n", encoding="utf-8")


def _fuentes(carpeta_cat: Path, huella: str = "sha256:aaa") -> None:
    _escribir(carpeta_cat / "fuentes.yaml", {"formato": "catalogo/4", "fuentes": [
        {"id": "DOGV-C-2001-5", "tipo": "dogv", "huella": huella},
        {"id": "BOE-A-2000-1", "tipo": "boe", "huella": "sha256:bbb"}]})


def _estado_programaciones(carpeta_cat: Path, consolidado: str = "2020-01-01|vigente", boe: dict | None = None,
                           ceice: list[str] | None = None) -> None:
    _escribir(carpeta_cat / "vigia.yaml", {"formato": "vigia/1", "consolidados": {"BOE-A-1999-9": consolidado},
                                           "boe": boe or {}, "ceice": ceice or ["Decreto 5/2001"]})


# -- citas --------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("cita, esperada", [
    ("DOGV-C-2001-5", "DOGV-C-2001-5"),
    ("Decreto 5/2001", "DOGV-C-2001-5"),
    ("decreto 5/2001", "DOGV-C-2001-5"),
    ("Decreto 5/2001 (currículos)", "DOGV-C-2001-5"),
    ("Real Decreto 1/2000", "BOE-A-2000-1"),
    ("Resolución de 1 de julio de 2030", "DOGV-C-2030-7"),
    ("Decreto 1/2000", None),          # es un real decreto: no casa
    ("Decreto 5/200", None),           # número cortado
    ("Orden 99/2000", None),           # no está en el catálogo
    ("Resolución de 1 de julio", None),   # casa con dos: ambigua
])
def test_resolver(cat, cita, esperada):
    n = citas.resolver(cat, cita)
    assert (n.id if n else None) == esperada


def test_indice_bloques_y_calculados(cat, carpeta):
    _bloque(carpeta, "otro.md", "  - {norma: Decreto 5/2001, articulo: '2'}\n  - {norma: Orden 99/2000}\n", 19)
    idx = citas.indice(cat, CarpetaDatos(carpeta), "PRU", CURSO)
    dogv = idx.usos["DOGV-C-2001-5"]
    assert {(u.apartado, u.origen) for u in dogv} == {(2, "calculado"), (16, "bloque"), (19, "bloque")}
    assert next(u for u in dogv if u.apartado == 19).detalle == "centro/otro.md"
    assert {u.apartado for u in idx.usos["BOE-A-2000-1"]} == {1, 2, 3, 4}
    assert "DOGV-C-2030-7" in idx.usos and "DOGV-C-2029-7" not in idx.usos   # la resolución de otro curso no entra
    assert set(idx.sin_vigilar) == {"Orden 99/2000", "DOGV-C-2025-29742"}  # el decreto de los apartados no está
    assert idx.sin_vigilar["DOGV-C-2025-29742"][0].apartado is None


# -- vigía --------------------------------------------------------------------------------------------------------------
def test_primera_revision_no_compara(carpeta_cat, datos):
    inf = vigia.revisar(Catalogo(carpeta_cat), datos, "PRU", CURSO, HOY)
    assert inf.anterior is None and not inf.cambios and not inf.hay_cambios
    md = vigia.markdown(inf)
    assert "Primera revisión" in md and "--revisado" in md and "no cambia ningún texto" in md
    assert any("vigia.yaml" in a for a in inf.avisos)        # catálogo sin el estado del vigía de Programaciones
    assert not vigia.ruta_estado(datos, "PRU", CURSO).exists()   # revisar no guarda nada


def test_sin_cambios_tras_marcar_revisado(carpeta_cat, datos):
    _fuentes(carpeta_cat)
    _estado_programaciones(carpeta_cat)
    p = vigia.marcar_revisado(Catalogo(carpeta_cat), datos, "PRU", CURSO, HOY)
    guardado = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert guardado["revisado"] == "2030-09-01" and "DOGV-C-2001-5" in guardado["normas"]
    assert "DOGV-C-2029-7" not in guardado["normas"]           # solo las que usa este PCCF
    inf = vigia.revisar(Catalogo(carpeta_cat), datos, "PRU", CURSO, DESPUES)
    assert inf.anterior == "2030-09-01" and not inf.cambios and not inf.nuevas and not inf.avisos


def test_huella_nueva_del_dogv_avisa_con_sus_bloques(carpeta_cat, datos):
    _fuentes(carpeta_cat)
    vigia.marcar_revisado(Catalogo(carpeta_cat), datos, "PRU", CURSO, HOY)
    _fuentes(carpeta_cat, huella="sha256:ccc")
    inf = vigia.revisar(Catalogo(carpeta_cat), datos, "PRU", CURSO, DESPUES)
    [c] = inf.cambios
    assert c.norma == "DOGV-C-2001-5" and c.cita == "DECRETO 5/2001, de 4 de mayo"
    assert "anexos del DOGV" in c.que[0]
    md = vigia.markdown(inf)
    assert "bloque `centro/diversidad.md`, art. 1 (borrador)" in md
    assert "Apartado 2 (" in md and "se calcula del catálogo" in md


def test_referencia_posterior_nueva_del_real_decreto(carpeta_cat, datos):
    vigia.marcar_revisado(Catalogo(carpeta_cat), datos, "PRU", CURSO, HOY)
    _editar(carpeta_cat / "ciclos" / "PRU.yaml", lambda d: d["rd"].update(posteriores=[
        {"id": "BOE-A-2030-1", "relacion": "SE MODIFICA", "texto": "el art. 2, por Real Decreto 9/2030"},
        {"id": "BOE-A-2030-2", "relacion": "SE DICTA DE CONFORMIDAD", "texto": "orden de currículo"}]))
    [c] = vigia.revisar(Catalogo(carpeta_cat), datos, "PRU", CURSO, DESPUES).cambios
    assert c.norma == "BOE-A-2000-1"
    assert c.que == ["Referencia posterior nueva: BOE-A-2030-1 · SE MODIFICA el art. 2, por Real Decreto 9/2030"]
    assert {u.apartado for u in c.usos} == {1, 2, 3, 4}


def test_consolidado_no_vigente_y_disposiciones_nuevas(carpeta_cat, datos):
    _estado_programaciones(carpeta_cat)
    vigia.marcar_revisado(Catalogo(carpeta_cat), datos, "PRU", CURSO, HOY)
    _estado_programaciones(carpeta_cat, consolidado="2030-09-20|NO vigente",
                           boe={"BOE-A-2030-77": {"titulo": "Orden ficticia de FP", "fecha": "2030-09-21"}},
                           ceice=["Decreto 5/2001", "Orden 3/2030"])
    inf = vigia.revisar(Catalogo(carpeta_cat), datos, "PRU", CURSO, DESPUES)
    [c] = inf.cambios
    assert c.norma == "BOE-A-1999-9" and "no vigente" in c.que[0]
    assert [x.norma for x in inf.no_vigentes] == ["BOE-A-1999-9"]
    assert inf.nuevas[0].startswith("BOE 2030-09-21: [Orden ficticia de FP]")
    assert "«Orden 3/2030» nuevo" in inf.nuevas[1]


def test_norma_que_entra_y_norma_que_sale(carpeta_cat, datos):
    vigia.marcar_revisado(Catalogo(carpeta_cat), datos, "PRU", CURSO, HOY)

    def cambiar(d):
        d["normas"] = [n for n in d["normas"] if n["id"] != "DOGV-C-2001-5"]
        d["normas"].append({"id": "BOE-A-2030-5", "ambito": "estatal", "titulo": {"es": "Real Decreto 5/2030, nuevo."},
                            "fecha": "2030-09-15", "diario": "BOE", "enlace": "https://www.boe.es/", "aplica": "todos"})
    _editar(carpeta_cat / "normativa.yaml", cambiar)
    inf = vigia.revisar(Catalogo(carpeta_cat), datos, "PRU", CURSO, DESPUES)
    que = {c.norma: c.que for c in inf.cambios}
    assert que["BOE-A-2030-5"] == ["Entra en el catálogo o empieza a aplicarse a este ciclo"]
    assert que["DOGV-C-2001-5"] == ["Ya no está en el catálogo"]
    assert "Decreto 5/2001" not in inf.sin_vigilar   # el bloque cita por id: ahora queda sin vigilar por id
    assert "DOGV-C-2001-5" in inf.sin_vigilar


def test_orden_vigia(carpeta_cat, carpeta, monkeypatch, capsys):
    monkeypatch.setenv("PCCF_CATALOGO", str(carpeta_cat))
    monkeypatch.setenv("PCCF_DATOS", str(carpeta))
    assert cli.main(["vigia", "PRU", CURSO]) == 0
    assert (carpeta / "salidas" / f"Vigía PCCF PRU {CURSO}.md").is_file()
    assert "Primera revisión" in capsys.readouterr().out
    assert cli.main(["vigia", "PRU", CURSO, "--revisado"]) == 0
    assert (carpeta / "cursos" / CURSO / "PRU" / "vigia.yaml").is_file()
    assert cli.main(["vigia", "PRU", CURSO]) == 0
    assert "Cambios desde la revisión del" in capsys.readouterr().out
