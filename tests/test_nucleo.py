"""Núcleo del MVP: apartados, carpeta de datos (esquemas y comprobaciones) y derivados de los apartados 1, 2 y 4."""
from __future__ import annotations

import pytest

from pccf import apartados, bloques, derivados
from pccf.catalogo import Catalogo
from pccf.datos import DatosNoValidos

from .conftest import CURSO


# -- apartados -------------------------------------------------------------------------------------------------------
def test_apartados_gm_gs_son_los_18_del_art_8_4_y_los_2_de_la_guia():
    lista = apartados.apartados("GS")
    assert [a.n for a in lista] == list(range(1, 21))
    assert [a.n for a in lista if a.origen == "norma"] == list(range(1, 19))
    assert [a.n for a in lista if a.origen == "guia"] == [19, 20]
    assert all(a.guia == f"2.3.{a.n - 1}" for a in lista)
    assert lista == apartados.apartados("GM")
    assert apartados.apartado("GS", 1).titulo == "Identificación del ciclo formativo"
    assert apartados.apartado("GS", 16).titulo == "Atención a la Diversidad"
    assert apartados.apartado("GS", 16).tipos == ("centro",)


def test_grado_basico_sin_digitalizacion_y_con_su_numero():
    gb = apartados.apartados("GB")
    gm = {a.n: a for a in apartados.apartados("GM")}
    assert len(gb) == 19 and 11 not in [a.n for a in gb]
    assert [a.numero for a in gb] == list(range(1, 20))            # se ve seguido
    assert apartados.numero("GB", 12) == 11 and apartados.numero("GB", 20) == 19
    assert apartados.numero("GM", 12) == 12
    assert apartados.apartado("GB", 18).titulo.endswith("Proyecto intermodular de aprendizaje colaborativo")
    for a in gb:   # mismos títulos que GM y GS, salvo el del proyecto
        if a.n != 18:
            assert a.titulo == gm[a.n].titulo
    assert apartados.norma("GB") == "DOGV-C-2025-32763"
    with pytest.raises(KeyError):
        apartados.apartados("XX")


# -- carpeta de datos -----------------------------------------------------------------------------------------------
def test_carpeta_ficticia_sin_errores(datos):
    assert datos.comprobar("PRU", CURSO) == []


def test_equipo_y_departamento(datos):
    eq = datos.equipo(CURSO, "PRU")
    assert eq.nombres(eq.del_modulo("9001")["docentes"]) == ["Docente Uno", "Docente Dos"]
    assert eq.del_modulo("9999") is None
    assert datos.departamento_de("PRU")["jefatura"] == "Jefa Ficticia"
    assert datos.departamento_de("OTRO") is None


def test_sin_equipo_es_none_no_error(datos):
    assert datos.equipo("2031-2032", "PRU") is None


def test_docente_sin_ficha_es_error(datos, carpeta):
    p = carpeta / "cursos" / CURSO / "PRU" / "equipo.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace("docentes: [DDOS]", "docentes: [NADIE]"), encoding="utf-8")
    with pytest.raises(DatosNoValidos, match="NADIE"):
        datos.equipo(CURSO, "PRU")


def test_equipo_en_carpeta_de_otro_ciclo_es_error(datos, carpeta):
    p = carpeta / "cursos" / CURSO / "PRU" / "equipo.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace("ciclo: PRU", "ciclo: XYZ"), encoding="utf-8")
    with pytest.raises(DatosNoValidos, match="XYZ"):
        datos.equipo(CURSO, "PRU")


def test_ciclo_en_dos_departamentos_es_error(datos, carpeta):
    p = carpeta / "centro" / "departamentos.yaml"
    p.write_text(p.read_text(encoding="utf-8") + "  - {id: OTR, nombre: Otro, jefatura: X, orden: 2, ciclos: [PRU]}\n",
                 encoding="utf-8")
    with pytest.raises(DatosNoValidos, match="PRU"):
        datos.departamentos()


def test_bloque_con_cabecera_mal_lo_dice_comprobar(datos, carpeta):
    p = carpeta / "centro" / "diversidad.md"
    p.write_text(p.read_text(encoding="utf-8").replace("estado: borrador", "estado: casi"), encoding="utf-8")
    errs = datos.comprobar("PRU", CURSO)
    assert len(errs) == 1 and "diversidad.md" in errs[0] and "estado" in errs[0]


def test_bloque_sin_cabecera(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("Solo texto\n", encoding="utf-8")
    with pytest.raises(bloques.BloqueNoValido, match="cabecera"):
        bloques.leer(p)


def test_bloques_por_apartado(datos):
    (b,) = datos.bloques("PRU", CURSO, apartado=16)
    assert b.tipo == "centro" and not b.confirmado and b.fecha == "2030-01-01"
    assert b.cuerpo == "Texto ficticio de atención a la diversidad."
    assert datos.bloques("PRU", CURSO, apartado=6) == []


# -- derivados ------------------------------------------------------------------------------------------------------
def test_identificacion(cat, datos):
    i = derivados.identificacion(cat, datos, "PRU", CURSO)
    assert (i.nombre, i.grado_largo, i.rd.cita_corta) == ("Pruebas automatizadas", "Grado Superior", "Real Decreto 1/2000")
    assert i.departamento["nombre"] == "Departamento de Pruebas"
    assert i.tutorias == [("1PRU", "Docente Uno")]
    claves = [m.clave for m in i.modulos]
    assert claves == ["9001", "9002", "OPT-PRU-A", "OPT-PRU-B"]   # cada optativa ofertada en lugar de su casilla
    por_clave = {m.clave: m for m in i.modulos}
    assert por_clave["9001"].docentes == ["Docente Uno", "Docente Dos"]
    assert por_clave["OPT-PRU-B"].docentes is None                  # sin docente: pendiente
    assert i.horas_total == 133 + 100 + 100                         # las optativas cuentan una vez


def test_identificacion_sin_equipo_ni_departamentos(cat, datos, carpeta):
    (carpeta / "centro" / "departamentos.yaml").unlink()
    i = derivados.identificacion(cat, datos, "PRU", "2031-2032")
    assert i.departamento is None and i.tutorias is None
    assert all(m.docentes is None for m in i.modulos)


def test_marco_normativo_por_ambito_y_curso(cat):
    m = derivados.marco_normativo(cat, "PRU", CURSO)
    assert [n.id for n in m["estatal"]] == ["BOE-A-1999-9", "BOE-A-2000-1"]          # por fecha
    assert [n.id for n in m["autonomico"]] == ["DOGV-C-2001-5", "DOGV-C-2030-7"]     # solo la resolución de su curso


def test_contribucion(cat):
    k = derivados.contribucion(cat, "PRU")
    assert [x[0] for x in k.competencias] == ["a", "b", "c"]
    assert {f.clave: letras for f, letras in k.filas} == {"9001": ["a", "b"], "9002": ["c"], "OPT-PRU-A": [], "OPT-PRU-B": []}
    assert k.fuente == "BOE-A-2000-1"


# -- con el catálogo real (equipo de desarrollo) ---------------------------------------------------------------------
@pytest.mark.real
def test_sea_en_el_catalogo_real():
    try:
        cat = Catalogo()
    except FileNotFoundError:
        pytest.skip("Sin el catálogo de Programaciones junto al repositorio")
    k = derivados.contribucion(cat, "SEA")
    assert len(k.competencias) == 19
    assert dict((f.clave, letras) for f, letras in k.filas)["0524"] == ["a", "b", "c", "d"]
