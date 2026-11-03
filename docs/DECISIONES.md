# Decisiones

Registro fechado de decisiones (ADR). Lo más reciente, arriba. El estado actual está en `PRD.md`, `ARCHITECTURE.md` y `DESIGN.md`.

## ADR-013 · Plantilla derivada de la de Programaciones y cuerpo escrito en código (2026-11-03)

- **Decisión:** `scripts/plantilla.py crear` saca la plantilla del PCCF de la de Programaciones: conserva estilos, numeración, tema, encabezados, pies y la sección de la portada; cambia la portada (departamento, horas del ciclo, jefatura y curso) y la franja del encabezado («Proyecto curricular»), y deja dos marcas de párrafo, `{{indice}}` y `{{cuerpo}}`. `documento.py` escribe el cuerpo apartado por apartado con los estilos de la plantilla y el índice con hipervínculos y campos de página, que Word actualiza al abrir.
- **Motivo:** el cuerpo depende de los datos (18 apartados, cada uno con tablas calculadas o bloques de texto de longitud variable). Las marcas de repetición de Programaciones están pensadas para un documento fijo y aquí no aportarían nada.
- **Consecuencia:** un cambio de identidad del centro en la plantilla de Programaciones llega volviendo a pasar `crear`. Los bloques admiten un Markdown sencillo (párrafos, «###», viñetas, negrita y enlaces). Las citas «>» son notas internas y no van al documento. Si queda algo pendiente o en borrador, el documento lleva la marca de agua «BORRADOR».
- **Descartado:** copiar el motor de marcas completo de Programaciones (`Motor`), porque obligaría a tener una plantilla con los 18 apartados escritos a mano.

## ADR-012 · Departamentos y orden de entrada de los ciclos (2026-11-03)

- **Decisión de CarlosFB:** un departamento por familia profesional para GM y GS (Electricidad y Electrónica, Automoción, Administración y Servicios Sociales), y un departamento propio de **Grado Básico** que lleva los cuatro ciclos de GB. Quién es la jefatura de cada uno está en `centro/departamentos.yaml` de la carpeta de datos (son datos personales).
- **Orden después de SEA:** primero el resto de Electricidad y Electrónica (STI, ARI, IEA e IT); después Automoción, Administración y Servicios Sociales; y al final Grado Básico, que tiene 17 apartados.
- **Cierra el abierto de ADR-009:** CarlosFB mantiene una sola carpeta de datos con todos los ciclos y departamentos; cada departamento le pasa sus bloques con «exportar bloque».
- **Descartado:** una carpeta de datos por departamento con su propio responsable (habría que formar a una persona por departamento en la app y en git).

## ADR-011 · Competencias para la empleabilidad: las personales y sociales del título (2026-11-03)

- **Decisión de CarlosFB:** el apartado 5 usa las **competencias personales y sociales** del real decreto del título, que ya están en el catálogo de Programaciones. Siguiendo la guía de la DGFP (2.3.4), no se ponderan.
- **Descartado:** los RA de los módulos comunes (IPE I y II, Digitalización, Sostenibilidad e Inglés), porque mezclan módulos con competencias, y una lista propia del centro, que alguien tendría que redactar y aprobar.

## ADR-010 · Vigía sin resumen con un modelo de lenguaje (2026-11-03)

- **Decisión de CarlosFB:** el informe del vigía da, para cada norma, el tipo de cambio según el BOE (modifica, deroga o corrige) o la huella del DOGV, el enlace y los apartados que la citan. **No incluye ningún resumen** generado.
- **Motivo:** no hay que instalar nada, el resultado es igual en todos los equipos y no hay riesgo de un resumen equivocado. Se puede añadir más adelante.
- **Descartado:** resumen con un modelo local (Ollama).

## ADR-009 · Para todos los ciclos y departamentos del centro (2026-10-28)

- **Decisión de CarlosFB:** la app sirve para todos los departamentos y todos los ciclos de EPLA (15: 4 de GB, 5 de GM y 6 de GS, de cinco familias profesionales), no solo para Electricidad y Electrónica.
- **Consecuencias:** los apartados se guardan por grado (GB tiene 17: Decreto 117/2025, art. 8.4); los ciclos salen del catálogo de Programaciones, que ya los tiene todos; cada ciclo tiene su carpeta de datos y su jefatura de departamento; la interfaz agrupa los ciclos por familia o departamento y grado. El MVP sigue siendo SEA.
- **Cerrado (ADR-012):** quién mantiene la carpeta de datos de los demás departamentos.

## ADR-008 · Repositorio público, con versiones y actualizaciones como Programaciones (2026-10-28)

- **Decisión de CarlosFB:** el repositorio es público, `github.com/cferrerobonet/PCCF`, con el mismo ciclo de versiones que Programaciones: etiquetas `vX.Y.Z`, compilación en GitHub Actions (DMG de macOS, instalador y portable de Windows, portable de Linux) publicada como release, y actualización desde la app (botón dorado «↑ Actualizar a X.Y.Z» y ventana de novedades con la entrada del `CHANGELOG.md`).
- **Consecuencias:** barrera de secretos desde el primer commit (gancho y CI «Secretos»); en el repositorio, nunca datos reales (docentes, empresas, alumnado) ni PCCF reales: van en la carpeta de datos (ADR-002); licencia MIT, como Programaciones; `CHANGELOG.md` en formato Keep a Changelog, porque sus entradas son las novedades que ve el profesorado.

## ADR-007 · Vigía: avisa, nunca reescribe (2026-10-28)

- **Decisión:** el vigía consulta BOE y DOGV, detecta modificaciones y derogaciones de las normas citadas e informa de los bloques afectados; no cambia ningún texto. El resumen con un modelo de lenguaje, si se hace, solo con un modelo local.
- **Motivo:** petición de CarlosFB; la única red permitida es la del BOE y el DOGV (RNF-1).
- **Cómo:** amplía el vigía de Programaciones (BOE: API de datos abiertos y XML del diario; DOGV: sin API ni RSS, huella del PDF y página de normativa de FP de la Conselleria). Detalle: `docs/INVESTIGACION.md` §4 y §5.

## ADR-006 · MVP: SEA, curso 2026-2027, apartados 1, 2, 4 y 16 (2026-10-28)

- **Decisión de CarlosFB:** Identificación (ciclo + anual), Marco normativo (normativo), Contribución de cada módulo a las competencias profesionales (derivado) y Atención a la diversidad (centro): los cinco tipos de contenido en cuatro apartados.

## ADR-005 · El Word parte de la plantilla de las programaciones (2026-10-28)

- **Decisión de CarlosFB:** no hay PCCF previo que seguir; el documento usa la plantilla de las programaciones del centro (encabezado, pie, tipografías, índice, legislación con hipervínculo) y el motor de plantilla con marcas de Programaciones, con los 18 apartados del art. 8.4.
- **Descartado:** el anexo I de la guía de la DGFP, que es un PDF de ejemplo, sin plantilla editable.

## ADR-004 · Stack: Python 3.11 y PyQt6, como Programaciones (2026-10-28)

- **Decisión:** las mismas versiones y piezas que Programaciones (PyQt6 6.7, `lxml`, PyYAML, `jsonschema`, `cryptography`), empaquetado en GitHub Actions.
- **Motivo:** se reutilizan su interfaz, su motor del documento, su lector de catálogo y su empaquetado; el profesorado ya conoce la interfaz (familia de apps de CarlosFB).
- **Descartado:** app web local (FastAPI o Flask con HTMX) y NiceGUI o Streamlit (ver `ARCHITECTURE.md` §1).

## ADR-003 · Datos en YAML y Markdown con git, mantenidos por CarlosFB (2026-10-28)

- **Decisión de CarlosFB:** CarlosFB (profesor del departamento, no jefe de departamento) guarda la carpeta de datos del PCCF con git y mete lo que acuerda el equipo; el equipo aporta bloques (desde la app o en reunión) y la jefatura de departamento coordina y aprueba sin usar la app ni git.
- **Consecuencia:** sin bloqueos ni fusión de copias; «exportar e importar bloque» para las aportaciones; versionado y comparación por curso con git.
- **Descartado:** carpeta compartida en la nube editada por varios (necesitaría bloqueos) y una copia por docente (conflictos).

## ADR-002 · La carpeta de datos va aparte del repositorio de la app (2026-10-28)

- **Decisión:** `PCCF - DATOS/` con su propio git, fuera de GitHub público; el repositorio de la app solo lleva código, esquemas, plantilla y datos ficticios.
- **Motivo:** los nombres del equipo docente y los datos de empresas no pueden acabar en un repositorio (barrera de secretos).

## ADR-001 · App hermana de Programaciones (2026-10-28)

- **Decisión de CarlosFB:** app nueva que lee el catálogo firmado de Programaciones (ciclos, módulos, RA, horas, competencias) y amplía su vigía; las programaciones del art. 9 siguen en Programaciones, que más adelante leerá del PCCF los acuerdos comunes.
- **Motivo:** Programaciones ya tiene catálogo, vigía y plantilla; duplicarlos daría dos fuentes que se contradicen. La Resolución de 2026-2027 (§6.1) dice que el contenido del PCCF no se repite en las programaciones.
- **Descartado:** el PCCF dentro de Programaciones (agranda una app en piloto y de repositorio público) y una app independiente que genere también las programaciones (duplicaría todo).
