"""Vigía del PCCF (ADR-016): qué normas han cambiado desde la última revisión del PCCF de un ciclo y un curso, y qué
apartados y bloques se apoyan en ellas (índice de `citas.py`).

**No consulta la red.** Lee lo que el vigía semanal de Programaciones deja en el catálogo:
- la huella de cada documento oficial (`fuentes.yaml`);
- las referencias posteriores (modificaciones, derogaciones, correcciones) del real decreto de cada ciclo
  (`ciclos/<SIGLA>.yaml`);
- el título y el enlace de cada norma (`normativa.yaml`);
- en el catálogo de desarrollo, además, la fecha y la vigencia de los textos consolidados del BOE y las disposiciones
  nuevas del BOE y de la página de normativa de FP de la Conselleria (`vigia.yaml`; el catálogo publicado no lo lleva).

**No toca ningún texto** ni hace resúmenes (ADR-010): avisa. Lo revisado se guarda en
`cursos/<curso>/<SIGLA>/vigia.yaml` de la carpeta de datos solo al marcarlo como revisado: ejecutar el vigía no hace
desaparecer un aviso.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pccf import citas
from pccf.catalogo import Catalogo
from pccf.datos import CarpetaDatos

FORMATO = "pccf-vigia/1"
SIN_CONFORMIDAD = "SE DICTA DE CONFORMIDAD"   # una orden de currículo que se dicta conforme al RD no lo cambia


def _leer(p: Path) -> dict | None:
    if not p.is_file():
        return None
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------------------------------------------------
# Lo que dice hoy el catálogo
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class Foto:
    normas: dict[str, dict]                 # id → {titulo, enlace, huella?, tipo_fuente?, consolidado?, posteriores?}
    boe: dict[str, dict] | None             # disposiciones nuevas del BOE que ha visto el vigía de Programaciones
    ceice: list[str] | None                 # citas de la página de normativa de FP de la Conselleria


def foto(cat: Catalogo) -> Foto:
    fuentes = {f["id"]: f for f in (_leer(cat.carpeta / "fuentes.yaml") or {}).get("fuentes", [])}
    estado = _leer(cat.carpeta / "vigia.yaml")
    consolidados = (estado or {}).get("consolidados") or {}
    posteriores: dict[str, list[str]] = {}
    for sigla in cat.siglas():
        rd = cat.ciclo(sigla).get("rd") or {}
        if rd.get("id"):
            posteriores[rd["id"]] = sorted(f"{p['id']} · {p['relacion']} {p.get('texto', '')}".strip()
                                           for p in rd.get("posteriores", []) if p.get("relacion") != SIN_CONFORMIDAD)
    normas = {}
    for n in cat.normas.values():
        d: dict = {"titulo": n.titulo, "enlace": n.enlace}
        if n.id in fuentes:
            d["huella"] = fuentes[n.id].get("huella", "")
            d["tipo_fuente"] = fuentes[n.id].get("tipo", "")
        if n.id in consolidados:
            d["consolidado"] = str(consolidados[n.id])
        if n.id in posteriores:
            d["posteriores"] = posteriores[n.id]
        normas[n.id] = d
    return Foto(normas=normas, boe=None if estado is None else dict(estado.get("boe") or {}),
                ceice=None if estado is None else list(estado.get("ceice") or []))


# ---------------------------------------------------------------------------------------------------------------------
# Comparación con la última revisión
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class Cambio:
    norma: str                          # id
    cita: str                           # «Decreto 114/2025, de 29 de julio» o el id
    enlace: str
    que: list[str]
    usos: list[citas.Uso]


@dataclass
class Informe:
    sigla: str
    curso: str
    fecha: str
    catalogo: str                       # versión del catálogo
    anterior: str | None                # fecha de la revisión anterior; None: es la primera
    cambios: list[Cambio] = field(default_factory=list)
    no_vigentes: list[Cambio] = field(default_factory=list)
    nuevas: list[str] = field(default_factory=list)
    sin_vigilar: dict[str, list[citas.Uso]] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)

    @property
    def hay_cambios(self) -> bool:
        return bool(self.cambios or self.nuevas)


def ruta_estado(datos: CarpetaDatos, sigla: str, curso: str) -> Path:
    return datos.carpeta / "cursos" / curso / sigla / "vigia.yaml"


def _no_vigente(d: dict | None) -> bool:
    return bool(d) and str(d.get("consolidado", "")).endswith("NO vigente")


def diferencias(antes: dict | None, ahora: dict | None) -> list[str]:
    """Qué cambia en una norma entre la revisión anterior y el catálogo de hoy, en frases."""
    if antes is None:
        return ["Entra en el catálogo o empieza a aplicarse a este ciclo"]
    if ahora is None:
        return ["Ya no está en el catálogo"]
    out = []
    if antes.get("titulo") != ahora.get("titulo"):
        out.append("Cambia su título en el catálogo")
    if antes.get("enlace") != ahora.get("enlace"):
        out.append(f"Cambia su enlace: {antes.get('enlace') or '—'} → {ahora.get('enlace') or '—'}")
    if antes.get("huella") != ahora.get("huella") and "huella" in ahora:
        dogv = " (los anexos del DOGV se revisan a mano)" if ahora.get("tipo_fuente") == "dogv" else ""
        out.append(f"El documento publicado ha cambiado: huella distinta{dogv}")
    if antes.get("consolidado") != ahora.get("consolidado") and "consolidado" in ahora:
        if _no_vigente(ahora) and not _no_vigente(antes):
            out.append("El BOE la da como **no vigente**")
        out.append(f"Texto consolidado actualizado: {antes.get('consolidado') or '—'} → {ahora['consolidado']}")
    for p in sorted(set(ahora.get("posteriores", [])) - set(antes.get("posteriores", []))):
        out.append(f"Referencia posterior nueva: {p}")
    return out


def _cambio(cat: Catalogo, ident: str, que: list[str], usos: list[citas.Uso], ahora: dict | None,
            antes: dict | None) -> Cambio:
    n = cat.normas.get(ident)
    return Cambio(norma=ident, cita=n.cita if n else (antes or {}).get("titulo", ident), usos=usos, que=que,
                  enlace=(ahora or antes or {}).get("enlace", ""))


def revisar(cat: Catalogo, datos: CarpetaDatos, sigla: str, curso: str, hoy: dt.date | None = None) -> Informe:
    """El informe del vigía para el PCCF de un ciclo y un curso. Solo lee: no guarda nada."""
    hoy = hoy or dt.date.today()
    idx = citas.indice(cat, datos, sigla, curso)
    f = foto(cat)
    previo = _leer(ruta_estado(datos, sigla, curso))
    inf = Informe(sigla=sigla, curso=curso, fecha=hoy.isoformat(), catalogo=cat.version,
                  anterior=str(previo["revisado"]) if previo else None, sin_vigilar=idx.sin_vigilar)
    if f.boe is None:
        inf.avisos.append("Este catálogo no lleva el estado del vigía de Programaciones (`vigia.yaml`; el catálogo "
                          "publicado no lo trae): no se ven los textos consolidados del BOE ni las disposiciones "
                          "nuevas. Sí se ven los documentos con huella distinta y las referencias posteriores.")
    for ident in sorted(i for i, u in idx.usos.items() if _no_vigente(f.normas.get(i))):
        inf.no_vigentes.append(_cambio(cat, ident, [f"Consolidado: {f.normas[ident]['consolidado']}"],
                                       idx.usos[ident], f.normas[ident], None))
    if previo is None:
        return inf
    vistas = previo.get("normas") or {}
    for ident in sorted(set(idx.usos) | set(vistas)):
        antes, ahora = vistas.get(ident), f.normas.get(ident)
        if ident not in idx.usos and ahora is not None:
            que = ["Este PCCF ya no se apoya en ella: sale del marco normativo del ciclo o de las citas de los bloques"]
        else:
            que = diferencias(antes, ahora)
        if que:
            usos = idx.usos.get(ident) or idx.sin_vigilar.get(ident, [])   # la que sale del catálogo, por su id
            inf.cambios.append(_cambio(cat, ident, que, usos, ahora, antes))
    if f.boe is not None and "boe" in previo:
        for ident, d in sorted(f.boe.items(), key=lambda x: (str(x[1].get("fecha", "")), x[0]), reverse=True):
            if ident not in previo["boe"] and ident not in cat.normas:
                inf.nuevas.append(f"BOE {d.get('fecha', '')}: [{d.get('titulo', ident)}]"
                                  f"(https://www.boe.es/buscar/doc.php?id={ident})")
    if f.ceice is not None and "ceice" in previo:
        for c in sorted(set(f.ceice) - set(previo["ceice"])):
            inf.nuevas.append(f"Página de normativa de FP de la Conselleria: «{c}» nuevo")
    return inf


def marcar_revisado(cat: Catalogo, datos: CarpetaDatos, sigla: str, curso: str, hoy: dt.date | None = None) -> Path:
    """Guarda lo que dice hoy el catálogo de las normas que usa el PCCF: el punto de partida de la próxima revisión."""
    hoy = hoy or dt.date.today()
    idx = citas.indice(cat, datos, sigla, curso)
    f = foto(cat)
    estado: dict = {"formato": FORMATO, "revisado": hoy.isoformat(), "catalogo": cat.version,
                    "normas": {i: f.normas[i] for i in sorted(idx.usos) if i in f.normas}}
    if f.boe is not None:
        estado["boe"] = sorted(f.boe)
        estado["ceice"] = sorted(f.ceice or [])
    p = ruta_estado(datos, sigla, curso)
    escribir_estado(p, sigla, curso, estado)
    return p


def escribir_estado(p: Path, sigla: str, curso: str, estado: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"# Lo que el vigía del PCCF dio por revisado de {sigla} {curso}. No se edita a mano: "
                 f"python -m pccf vigia {sigla} {curso} --revisado\n"
                 + yaml.safe_dump(estado, allow_unicode=True, sort_keys=False, width=10_000), encoding="utf-8")


# ---------------------------------------------------------------------------------------------------------------------
# Informe en Markdown
# ---------------------------------------------------------------------------------------------------------------------
def _uso(u: citas.Uso) -> str:
    sitio = "Estructura del PCCF" if u.apartado is None else f"Apartado {u.numero or u.apartado} ({u.titulo})"
    if u.origen == "calculado":
        return f"{sitio}: se calcula del catálogo ({u.detalle}); se rehace al generar el Word, que hay que repasar"
    art = "" if not u.articulo else f", art. {u.articulo}" if u.articulo[0].isdigit() else f", artículo {u.articulo}"
    return f"{sitio}: bloque `{u.detalle}`{art} ({u.estado}); revisar el texto"


def _usos(usos: list[citas.Uso]) -> list[str]:
    orden = sorted(usos, key=lambda u: (-1 if u.apartado is None else u.apartado, u.origen, u.detalle))
    return [f"  - {_uso(u)}" for u in orden]


def _norma(c: Cambio) -> list[str]:
    nombre = f"[{c.cita}]({c.enlace})" if c.enlace else c.cita
    donde = ["  - Dónde se usa:", *[f"  {x}" for x in _usos(c.usos)]] if c.usos else []
    return [f"- **{nombre}** · `{c.norma}`", *[f"  - {q}" for q in c.que], *donde]


def markdown(inf: Informe) -> str:
    md = [f"# Vigía del PCCF · {inf.sigla} {inf.curso} · {inf.fecha}", "",
          f"Catálogo {inf.catalogo}. "
          + (f"Cambios desde la revisión del {inf.anterior}." if inf.anterior else
             "**Primera revisión:** no hay punto de partida, así que no se puede decir qué ha cambiado. Se marca como "
             f"revisado con `python -m pccf vigia {inf.sigla} {inf.curso} --revisado` y, desde ahí, el vigía avisa "
             "de lo que cambie."), ""]
    md += ["## Normas que han cambiado", ""]
    if inf.cambios:
        for c in inf.cambios:
            md += _norma(c)
    else:
        md.append("- Ninguna." if inf.anterior else "- Sin revisión anterior con la que comparar.")
    md.append("")
    if inf.no_vigentes:
        md += ["## Normas citadas que el BOE da como no vigentes", ""]
        for c in inf.no_vigentes:
            md += _norma(c)
        md.append("")
    if inf.nuevas:
        md += ["## Disposiciones nuevas que ha visto el vigía de Programaciones", "",
               "No las cita ningún apartado: se miran por si afectan al PCCF.", "",
               *[f"- {x}" for x in inf.nuevas], ""]
    if inf.sin_vigilar:
        md += ["## Citas sin vigilar", "",
               "No casan con una sola norma del catálogo de Programaciones: el vigía no sabe si han cambiado. Se "
               "comprueban a mano o se pide que la norma entre en el catálogo.", ""]
        for cita, usos in sorted(inf.sin_vigilar.items()):
            md += [f"- {cita}", *[f"  {x}" for x in _usos(usos)]]
        md.append("")
    if inf.avisos:
        md += ["## Avisos", "", *[f"- {x}" for x in inf.avisos], ""]
    md += ["El vigía no cambia ningún texto: avisa. Lo calculado del catálogo se rehace al generar el Word; los "
           "bloques los revisa el equipo y los aprueba la jefatura de departamento."]
    return "\n".join(md) + "\n"


def nombre_archivo(sigla: str, curso: str) -> str:
    return f"Vigía PCCF {sigla} {curso}.md"
