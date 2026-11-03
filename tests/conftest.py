"""Catálogo y carpeta de datos ficticios (`tests/datos/`), copiados a una carpeta temporal para poder estropearlos."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pccf.catalogo import Catalogo
from pccf.datos import CarpetaDatos

DATOS = Path(__file__).resolve().parent / "datos"
CURSO = "2030-2031"


@pytest.fixture
def cat() -> Catalogo:
    return Catalogo(DATOS / "catalogo")


@pytest.fixture
def carpeta(tmp_path) -> Path:
    destino = tmp_path / "datos"
    shutil.copytree(DATOS / "datos", destino)
    return destino


@pytest.fixture
def datos(carpeta) -> CarpetaDatos:
    return CarpetaDatos(carpeta)
