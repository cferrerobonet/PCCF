"""Portada (ADR-021): las siglas a la medida de su celda y el nombre del ciclo con su mismo alto, como en Programaciones."""
from __future__ import annotations

import pytest

from pccf import portada

ANCHO = (11906 - 6237 - 1021) / 20
NOMBRES = ["Sistemas electrotécnicos y automatizados", "Electromecánica de vehículos automóviles",
           "Sistemas de telecomunicaciones e informáticos", "Administración y finanzas", "Automoción",
           "Instalaciones de telecomunicaciones", "Integración social"]


def _alto_bloque(c: dict) -> float:
    m = portada.medidas()
    return m["nombre"]["cap"] * c["nombre_pt"] + (len(c["lineas"]) - 1) * c["interlineado"]


@pytest.mark.parametrize("nombre", NOMBRES)
def test_el_nombre_no_pasa_del_alto_de_las_siglas_ni_deja_palabras_cortas_solas(nombre):
    c = portada.colocacion("PRU", nombre, ANCHO)
    alto = c["siglas_pt"] * portada.medidas()["siglas"]["cap"]
    assert _alto_bloque(c) <= alto + 0.5
    assert " ".join(c["lineas"]) == nombre
    assert not any(linea.lower() in portada.CORTAS for linea in c["lineas"])
    letras = portada.medidas()["nombre"]["anchos"]
    assert all(sum(letras.get(x, 0.55) for x in linea) * c["nombre_pt"] <= ANCHO * 0.9 for linea in c["lineas"])


def test_un_nombre_de_tres_lineas_ocupa_el_alto_de_las_siglas():
    c = portada.colocacion("SEA", "Sistemas electrotécnicos y automatizados", ANCHO)
    assert c["lineas"] == ["Sistemas", "electrotécnicos", "y automatizados"]
    assert _alto_bloque(c) >= 0.9 * c["siglas_pt"] * portada.medidas()["siglas"]["cap"]


def test_las_siglas_largas_se_ajustan_a_su_celda():
    assert portada.letra_siglas("SEA") == portada.SIGLAS_PT
    assert portada.letra_siglas("ADMW") < portada.SIGLAS_PT
