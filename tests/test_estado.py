"""Estado de los apartados y lo que la interfaz escribe en la carpeta de datos (bloques y equipo), con los datos
ficticios copiados a una carpeta temporal."""
from __future__ import annotations

import subprocess

import pytest

from pccf import bloques, citas, cursos, estado, vigia
from pccf.datos import DatosNoValidos

from .conftest import CURSO

HOY = "2030-02-01"


def _estados(cat, datos, informe=None) -> dict[int, str]:
    return {a.n: a.estado for a in estado.calcular(cat, datos, "PRU", CURSO, informe).apartados}


def test_estado_de_los_apartados(cat, datos):
    e = estado.calcular(cat, datos, "PRU", CURSO)
    assert len(e.apartados) == 20
    est = {a.n: a.estado for a in e.apartados}
    assert est[1] == "confirmado"                 # equipo confirmado, departamento y tutorías
    assert est[2] == est[4] == est[20] == "confirmado"   # se calculan del catálogo
    assert est[16] == "borrador"                  # su bloque está en borrador
    assert est[3] == est[6] == "pendiente"
    assert e.confirmados == 4
    assert [b.ruta.name for b in e.de(16).bloques] == ["diversidad.md"]


def test_sin_equipo_el_apartado_1_queda_pendiente(cat, datos, carpeta):
    (carpeta / "cursos" / CURSO / "PRU" / "equipo.yaml").unlink()
    e = estado.calcular(cat, datos, "PRU", CURSO)
    assert e.de(1).estado == "pendiente"
    assert "equipo docente" in e.de(1).motivo


def test_el_vigia_pone_a_revisar_lo_afectado(cat, datos):
    idx = citas.indice(cat, datos, "PRU", CURSO)
    norma = next(i for i, us in idx.usos.items() if any(u.apartado == 16 for u in us))
    inf = vigia.Informe(sigla="PRU", curso=CURSO, fecha=HOY, catalogo="x", anterior="2030-01-15",
                        cambios=[vigia.Cambio(norma=norma, cita="Norma ficticia", enlace="", que=["cambia"],
                                              usos=idx.usos[norma])])
    est = _estados(cat, datos, inf)
    assert est[16] == "revisar"
    assert estado.calcular(cat, datos, "PRU", CURSO, inf).de(16).normas == ["Norma ficticia"]


def test_guardar_un_bloque_lo_devuelve_a_borrador(cat, datos, carpeta):
    b = bloques.confirmar(datos.bloques("PRU", CURSO, 16)[0], HOY)
    assert b.confirmado and b.fecha == HOY
    b = bloques.guardar(b, "Texto nuevo ficticio.\n\n- Una viñeta.", "2030-02-02")
    assert b.estado == "borrador" and b.fecha == "2030-02-02"
    assert b.cuerpo == "Texto nuevo ficticio.\n\n- Una viñeta."
    texto = (carpeta / "centro" / "diversidad.md").read_text(encoding="utf-8")
    assert "DOGV-C-2001-5" in texto              # las citas siguen ahí
    assert bloques.guardar(b, b.cuerpo, "2030-03-03").fecha == "2030-02-02"   # sin cambios, no se toca


def test_confirmar_un_bloque_heredado_conserva_su_origen(cat, datos, carpeta):
    p = carpeta / "centro" / "diversidad.md"
    p.write_text(cursos.heredar_bloque(p.read_text(encoding="utf-8"), "2029-2030"), encoding="utf-8")
    b = datos.bloques("PRU", CURSO, 16)[0]
    assert estado.de_bloque(b) == "heredado"
    b = bloques.confirmar(b, HOY)
    assert b.confirmado and b.origen == "heredado del curso 2029-2030"
    assert estado.de_bloque(b) == "confirmado"


def test_nuevo_bloque_en_la_carpeta_de_su_tipo(datos, carpeta):
    b = datos.nuevo_bloque("PRU", CURSO, 6, "ciclo", "Metodología del taller", "Equipo ficticio", HOY)
    assert b.ruta == carpeta / "ciclos" / "PRU" / "bloques" / "metodologia-del-taller.md"
    assert (b.tipo, b.apartado, b.estado, b.origen) == ("ciclo", 6, "borrador", "equipo")
    anual = datos.nuevo_bloque("PRU", CURSO, 13, "anual", "plan", "Equipo ficticio", HOY)
    assert anual.ruta.parent == carpeta / "cursos" / CURSO / "PRU" / "bloques"
    with pytest.raises(FileExistsError):
        datos.nuevo_bloque("PRU", CURSO, 6, "ciclo", "metodologia del taller", "Otro", HOY)
    with pytest.raises(DatosNoValidos):
        datos.nuevo_bloque("PRU", CURSO, 4, "derivado", "matriz", "Otro", HOY)


def test_importar_un_bloque_suelto(datos, carpeta, tmp_path):
    suelto = tmp_path / "suelto" / "empresas.md"
    suelto.parent.mkdir()
    suelto.write_text("---\ntipo: anual\napartado: 9\norigen: equipo\nestado: borrador\naportado_por: Prueba\n"
                      "fecha: 2030-01-02\n---\n\nCriterios ficticios.\n", encoding="utf-8")
    b = datos.importar_bloque(suelto, "PRU", CURSO)
    assert b.ruta == carpeta / "cursos" / CURSO / "PRU" / "bloques" / "empresas.md"
    with pytest.raises(FileExistsError):
        datos.importar_bloque(suelto, "PRU", CURSO)
    assert datos.importar_bloque(suelto, "PRU", CURSO, sustituir=True).apartado == 9
    malo = tmp_path / "suelto" / "malo.md"
    malo.write_text("sin cabecera", encoding="utf-8")
    with pytest.raises(bloques.BloqueNoValido):
        datos.importar_bloque(malo, "PRU", CURSO)


def test_confirmar_el_equipo_heredado(cat, datos):
    nuevo = cursos.siguiente(CURSO)
    cursos.nuevo_curso(cat, datos, "PRU", CURSO, nuevo)
    assert estado.calcular(cat, datos, "PRU", nuevo).de(1).estado == "heredado"
    eq = datos.confirmar_equipo(nuevo, "PRU")
    assert eq.confirmado and eq.origen == f"heredado del curso {CURSO}"
    texto = (datos.carpeta / "cursos" / nuevo / "PRU" / "equipo.yaml").read_text(encoding="utf-8")
    assert not texto.startswith("# Heredado")
    assert estado.calcular(cat, datos, "PRU", nuevo).de(1).estado == "confirmado"


def test_cursos_y_versiones_aprobadas(datos, carpeta):
    assert datos.cursos("PRU") == [CURSO]
    assert datos.cursos("OTRO") == []
    assert datos.etiquetas("PRU") == []            # sin git
    for orden in (["init", "-q"], ["add", "-A"], ["-c", "user.name=P", "-c", "user.email=p@example.com", "commit",
                                                  "-qm", "datos"], ["tag", "PRU-2030-2031-v1"]):
        subprocess.run(["git", "-C", str(carpeta), *orden], check=True, capture_output=True)
    assert datos.etiquetas("PRU") == ["PRU-2030-2031-v1"]
