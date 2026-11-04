# Decisiones

Registro fechado de decisiones (ADR). Lo más reciente, arriba. El estado actual está en `PRD.md`, `ARCHITECTURE.md` y `DESIGN.md`.

## ADR-018 · Interfaz mínima: la maqueta v0, con lo que tiene datos (2026-11-04)

- **Decisión:** la interfaz sigue la maqueta v0 aprobada (tres zonas, barra superior, vigía, «Nuevo curso» y «Comparar», selector de los 15 ciclos) y el diseño de Programaciones, de la que se copian el estilo, los componentes y la vista previa. `python -m pccf` sin argumentos la abre.
- **Estado de los apartados** (`estado.py`), con las reglas del documento: pendiente (sin contenido o sin el equipo docente), heredado, borrador, confirmado y «revisar» cuando el vigía ha visto cambiar una norma en la que se apoya. Lo usan la lista, el progreso y los avisos.
- **Bloques:** se editan en Markdown y se guardan solos al dejar de escribir y al cambiar de apartado; **un texto cambiado vuelve a borrador** y hay que confirmarlo otra vez, para que no salga como aprobado algo que nadie ha revisado. La cabecera se cambia línea a línea, sin tocar comentarios ni el resto de campos, y el archivo solo se sustituye si el bloque resultante es válido. «Añadir bloque» lo crea vacío y en borrador en la carpeta de su tipo: de centro en `centro/`, de ciclo y normativo en `ciclos/<SIGLA>/bloques/`, anual en el curso. «Importar bloque» comprueba el archivo y pregunta antes de sustituir uno con el mismo nombre.
- **Equipo docente:** la app lo enseña y lo confirma; se edita en `equipo.yaml` (botón «Abrir equipo.yaml»), porque son datos personales que mantiene CarlosFB en la carpeta de datos. Un editor de la tabla, si hace falta, después.
- **PDF:** con el Word del equipo (actualizando los campos del contenido antes de guardar) o con LibreOffice; sin ONLYOFFICE, que Programaciones añadió para equipos sin ninguno de los dos.
- **Lo que la maqueta enseñaba y aún no tiene datos**, que no se programa (sin datos no se implementa): «Añadir norma del centro» (`normativa.yaml` de la carpeta de datos), «Añadir ajuste» de la matriz del apartado 4 (`ajustes.yaml`), el ejemplo del anexo I en la caja de la guía y las actualizaciones (llegan con el empaquetado, ARCHITECTURE.md §6).
- **Descartado:** guardar con un botón (se olvida y se pierde texto al cambiar de apartado) y dejar confirmado un bloque que se edita (daría por aprobado un texto nuevo).

## ADR-017 · «Nuevo curso» hereda lo anual y «Comparar» lee el catálogo de hoy (2026-11-04)

- **Decisión:** «Nuevo curso» copia solo la carpeta del ciclo en el curso (`cursos/<curso>/<SIGLA>/`): lo de centro y de ciclo es común a todos los cursos y no se duplica. El equipo docente y los bloques del curso pasan como heredados (`estado: borrador` y `origen: heredado del curso …`; el esquema del equipo admite ahora `origen`); el Word los marca «Heredado» y sale en borrador hasta confirmarlos (DESIGN.md: «heredado hasta que se confirma»). Se copia lo que el vigía dio por revisado, para que su primer informe del curso nuevo diga qué ha cambiado (la resolución de instrucciones, sobre todo). Nunca sobrescribe ni deja un curso a medias.
- **«Comparar»:** cada lado es un curso de la carpeta de datos o un curso en una etiqueta de git de esa carpeta (sin red). Lo calculado se rehace con el catálogo de hoy en los dos lados, porque la carpeta de datos no guarda el catálogo con el que se generó cada versión: las diferencias de un apartado calculado entre dos versiones solo salen si cambian los datos (equipo, departamento), y las del catálogo las da el vigía.
- **Descartado:** copiar también los bloques de centro y de ciclo a cada curso (dos copias del mismo texto que pueden separarse) y guardar el catálogo con cada versión aprobada (pesa y lo resuelve el vigía).

## ADR-016 · El vigía del PCCF lee el catálogo, no la red (2026-11-04)

- **Decisión:** el vigía del PCCF no consulta el BOE ni el DOGV. Compara lo que el vigía semanal de Programaciones deja en el catálogo (huellas de los documentos, referencias posteriores de cada real decreto, normativa y, en el catálogo de desarrollo, textos consolidados y disposiciones nuevas) con lo que se dio por revisado del PCCF de cada ciclo y curso (`cursos/<curso>/<SIGLA>/vigia.yaml` de la carpeta de datos), y dice qué apartados y bloques se apoyan en cada norma que cambia. Precisa ADR-007 («consulta BOE y DOGV»).
- **Motivo:** Programaciones ya hace esas consultas cada semana, con pausa entre peticiones, y CarlosFB revisa lo que encuentra antes de publicarlo; repetirlas daría dos registros de lo visto que pueden no coincidir. Así la app no necesita más red que la del catálogo publicado (RNF-1) y las pruebas no dependen de respuestas grabadas.
- **Cómo:** `citas.py` casa cada cita de un bloque con el catálogo por id o por el principio del título («Decreto 114/2025»); si no casa con una sola norma, no se adivina: sale como «sin vigilar». Ejecutar el vigía solo lee; lo revisado se guarda a mano (`--revisado`), para que un aviso no desaparezca por mirarlo.
- **Límite:** el catálogo publicado no lleva `vigia.yaml` (estado de trabajo de Programaciones): con él no se ven los textos consolidados ni las disposiciones nuevas, y el informe lo avisa. La carpeta de datos la mantiene CarlosFB con el catálogo de desarrollo, que sí lo lleva.
- **Descartado:** consultar desde el PCCF la API del BOE y las huellas del DOGV de cada norma citada (duplica el vigía de Programaciones) y vigilar normas que no están en el catálogo (una cita por nombre no da su id: se pide que entre en el catálogo).

## ADR-015 · El documento tiene diseño propio, no el de las programaciones (2026-11-04)

- **Decisión de CarlosFB:** el Word del PCCF rompe con el formato y el aspecto de las programaciones: diseño corporativo del centro, formal pero rompedor, que no parezca un documento genérico ni hecho con IA. Sustituye a ADR-005 y, en lo visual, a ADR-013.
- **Aprobada por CarlosFB el 2026-11-04** y programada el mismo día: `DESIGN.md` § Documento y la maqueta `../Maqueta documento v1 (2026-11-04)/`: portada con bloque verde a sangre y las siglas del ciclo, control del documento con registro de revisiones, retícula con columna de margen para los números de apartado, base normativa bajo cada título, tablas sin rejilla, matrices apaisadas con celdas rellenas, «Pendiente» con filetes de oro y Barlow incrustada.
- **Cómo se buscó:** guías públicas de diseño con mucho uso, de las que se toma la lista de lo que delata un diseño genérico (antetítulos, barras laterales de color, tarjetas iguales, tipos del sistema), adaptada al papel en `DESIGN.md`, y la mecánica de OOXML. Descartadas las recetas de documento «corporativo» con Calibri o Aptos: dan justo el aspecto que se quiere evitar.
- **Consecuencia:** `scripts/plantilla.py` construye la plantilla desde cero e incrusta las fuentes Barlow (licencia OFL); sin marca de agua: el borrador se ve en la portada y en el encabezado. **Medidas de prevención de riesgos laborales** que la guía incluye en el PCCF (2.1): en el apartado 14, como subapartado propio (decisión de CarlosFB: van ligadas al uso de talleres y equipos).
- **Descartado:** mantener la plantilla de Programaciones con otra portada; diseño en Canva o en otra herramienta externa (el documento se genera desde datos y lo edita el equipo en Word).

## ADR-014 · La guía práctica de la DGFP es la base del contenido (2026-11-04)

- **Decisión de CarlosFB:** el contenido de los PCCF sigue al pie de la letra, en la medida de lo posible, la «Guía práctica para el docente» del PCCF de la Dirección General de FP (curso 2024-2025): sus apartados, lo que pide en cada uno, sus tablas y sus fichas.
- **Cómo:** la lista de apartados lleva para cada uno su punto de la guía (apartado N = 2.3.(N−1)) y suma los dos que la guía añade al art. 8.4: **19 «Otros aspectos del proyecto curricular»** (2.3.18; aquí van las actividades del profesorado durante la FE de la Resolución de 2026-2027, §17.8.1) y **20 «Las programaciones didácticas de los módulos y/o proyectos»** (2.3.19). El documento añade el control del documento con el registro de revisiones (2.2) y los anexos A (ficha de empresa, anexo III) y B (programa formativo personalizado, anexo IV).
- **Donde choca con la norma, manda la norma:** títulos literales del Decreto 114/2025 (la guía cambia los de 2.3.7, 2.3.8, 2.3.15 y 2.3.17), Orden 8/2025 en lugar de la Orden 79/2010, plazo del art. 8.2, grado básico con sus 17 apartados y los términos de la LO 3/2022. La tabla completa está en el índice de la guía.
- **Dónde está:** el PDF, su espejo troceado en ocho partes y su índice (qué pide cada apartado, en qué trozo y con qué ejemplo) están en `../GUÍA PCCF (DGFP 2024-2025)/`, **fuera del repositorio**: la licencia de la guía (CC BY-NC-ND 4.0) no casa con la MIT del repositorio. Aquí solo se cita.
- **Descartado:** usar la guía solo como orientación (planteamiento de ADR-005).

## ADR-013 · Plantilla derivada de la de Programaciones y cuerpo escrito en código (2026-11-03) · la plantilla, sustituida por ADR-015; el cuerpo escrito en código sigue

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

## ADR-007 · Vigía: avisa, nunca reescribe (2026-10-28) · cómo se entera de los cambios, precisado por ADR-016

- **Decisión:** el vigía consulta BOE y DOGV, detecta modificaciones y derogaciones de las normas citadas e informa de los bloques afectados; no cambia ningún texto. El resumen con un modelo de lenguaje, si se hace, solo con un modelo local.
- **Motivo:** petición de CarlosFB; la única red permitida es la del BOE y el DOGV (RNF-1).
- **Cómo:** amplía el vigía de Programaciones (BOE: API de datos abiertos y XML del diario; DOGV: sin API ni RSS, huella del PDF y página de normativa de FP de la Conselleria). Detalle: `docs/INVESTIGACION.md` §4 y §5.

## ADR-006 · MVP: SEA, curso 2026-2027, apartados 1, 2, 4 y 16 (2026-10-28)

- **Decisión de CarlosFB:** Identificación (ciclo + anual), Marco normativo (normativo), Contribución de cada módulo a las competencias profesionales (derivado) y Atención a la diversidad (centro): los cinco tipos de contenido en cuatro apartados.

## ADR-005 · El Word parte de la plantilla de las programaciones (2026-10-28) · sustituida por ADR-015

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
