# Decisiones

Registro fechado de decisiones (ADR). Lo más reciente, arriba. El estado actual está en `PRD.md`, `ARCHITECTURE.md` y `DESIGN.md`.

## ADR-009 · Para todos los ciclos y departamentos del centro (2026-10-28)

- **Decisión de CarlosFB:** la app sirve para todos los departamentos y todos los ciclos de EPLA (15: 4 de GB, 5 de GM y 6 de GS, de cinco familias profesionales), no solo para Electricidad y Electrónica.
- **Consecuencias:** los apartados se guardan por grado (GB tiene 17: Decreto 117/2025, art. 8.4); los ciclos salen del catálogo de Programaciones, que ya los tiene todos; cada ciclo tiene su carpeta de datos y su jefatura de departamento; la interfaz agrupa los ciclos por familia o departamento y grado. El MVP sigue siendo SEA.
- **Abierto:** quién mantiene la carpeta de datos de los demás departamentos (ADR-003 se pensó para uno solo).

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
