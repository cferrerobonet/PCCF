# Cambios

Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); versiones con [SemVer](https://semver.org/lang/es/). Lo más reciente, arriba.

## [Sin publicar]

- 2026-11-09 · Un color para cada cosa: errores en rojo (✕), avisos en ámbar (⚠), consejos y borradores en azul (ⓘ), lo que falta por completar en ciruela y lo completo en verde (ADR-025).

## [0.4.0] - 2026-11-09

Todos los ciclos del centro y, de un vistazo, qué apartados están completos y cuáles faltan.

- Ya se puede preparar el PCCF de los quince ciclos, también los de grado básico, con sus apartados y su decreto.
- La lista de apartados pinta en verde los completos, que solo esperan que el equipo los confirme, y en ámbar los que aún hay que alimentar, con cuántas cosas les faltan. Arriba, una barra de avance y los filtros «Todos», «Completar» y «Aprobar».

### Añadido

- 2026-11-09 · Todos los ciclos del centro, también los de grado básico, con sus apartados (sin el de Digitalización y Sostenibilidad, y el Proyecto intermodular de aprendizaje colaborativo) y su decreto (ADR-023).
- 2026-11-09 · La lista de apartados distingue de un vistazo los completos, que solo esperan que el equipo los confirme, de los que aún hay que alimentar, con lo que les falta; barra de avance y filtros «Todos · Completar · Aprobar» (ADR-024).

## [0.3.0] - 2026-11-09

Portada más clara y Ajustes nuevos.

- La portada pone el nombre del ciclo grande, a la derecha de las siglas y con su misma altura, como las programaciones.
- Ajustes, con menú lateral como en las programaciones: carpetas, documento y versión. Desde ahí se buscan actualizaciones y se comprueba el catálogo; cada cambio se guarda al momento.

### Cambiado

- 2026-11-09 · Ajustes con menú lateral, como en las programaciones: carpetas, documento y versión; «Buscar actualizaciones» y «Comprobar ahora» el catálogo, sin cerrar la app. Cada cambio se guarda al momento (ADR-022).

- 2026-11-09 · Portada: el nombre del ciclo, grande y a la derecha de las siglas, con su mismo alto, como el código y el nombre del módulo en las programaciones (ADR-021).

## [0.2.0] - 2026-11-09

Los textos del PCCF se escriben como en Word: ya no hace falta saber Markdown.

- Editor con su barra: subtítulo, negrita, viñetas, enlace y nota interna (sombreada, no sale en el PCCF); los atajos de Word (⌘B o Ctrl+B, ⌘K o Ctrl+K) y «- » al principio para empezar una viñeta. Lo que pegues de Word conserva los títulos, las viñetas, la negrita y los enlaces.
- «Exportar a Word…» guarda un bloque en Word para que alguien del equipo lo escriba o lo revise; «Importar Word…» lo devuelve a su sitio, en borrador. Un Word cualquiera entra como bloque nuevo del apartado abierto.

### Cambiado

- 2026-11-09 · Editor de los bloques como en Word e importación y exportación en Word (ADR-020). Los bloques `.md` exportados con la versión 0.1.0 se siguen pudiendo importar.

## [0.1.0] - 2026-11-04

Primera versión del PCCF: el proyecto curricular de un ciclo y un curso, desde los datos del catálogo y los textos del equipo, en Word con el diseño del centro. Sirve ya para el ciclo de Sistemas Electrotécnicos y Automatizados (SEA) en 2026-2027, con los apartados 1, 2, 4 y 16; los demás salen «Pendiente» con lo que pide la guía de la DGFP.

- Ventana con los apartados y su estado, lo que pide la guía, lo que se calcula del catálogo y los textos del equipo, que se escriben y se guardan solos.
- Vista previa y exportación a Word y PDF.
- Vigía normativo: avisa si cambia una norma en la que se apoya el PCCF y dice qué apartados toca. No cambia ningún texto.
- «Nuevo curso» (el curso siguiente, con lo del curso como heredado hasta confirmarlo) y «Comparar» dos cursos o una versión aprobada.
- La app lleva el catálogo curricular publicado por Programaciones, busca uno más nuevo al arrancar (como mucho una vez al día) y avisa de las versiones nuevas de la app.

### Añadido

- 2026-11-04 · Compilación en GitHub para macOS, Windows y Linux, con la prueba de arranque de la app compilada; actualizaciones desde la app; catálogo publicado y firmado por Programaciones dentro de la app y descarga de uno más nuevo; registro de la app; icono propio.

- 2026-11-04 · Interfaz (ADR-018), con el diseño de la maqueta v0: `python -m pccf` abre la ventana. A la izquierda, el ciclo (los del catálogo, por familia y con buscador) y los 20 apartados con su estado; en el centro, el apartado con lo que pide la guía, lo calculado del catálogo y los bloques de texto, que se editan en Markdown y se guardan solos; a la derecha, el progreso, los avisos, la vista previa y «Exportar» a Word y PDF.
- 2026-11-04 · Bloques desde la interfaz: confirmar (también los heredados), añadir, importar y exportar un bloque suelto; un texto cambiado vuelve a borrador. Confirmar el equipo docente heredado.
- 2026-11-04 · Vigía, «Nuevo curso» y «Comparar» en la interfaz: el informe con «Marcar como revisado» y «Guardar informe»; crear el curso siguiente y comparar dos cursos o una versión aprobada, apartado por apartado.
- 2026-11-04 · PDF con el Word del equipo o con LibreOffice, con las páginas del contenido puestas.
- 2026-11-04 · Ajustes: carpeta de datos, catálogo, programa del PDF y correo del pie de la portada.
- 2026-11-04 · «Nuevo curso» (ADR-017): `python -m pccf nuevo-curso <SIGLA> <curso> [curso nuevo]` crea el curso siguiente del ciclo con el equipo docente y los bloques del curso como heredados (en borrador hasta confirmarlos; el Word los marca «Heredado»), copia lo revisado por el vigía y pasa el vigía. Nunca sobrescribe.
- 2026-11-04 · «Comparar»: `python -m pccf comparar <SIGLA> <curso>[@etiqueta] <curso>[@etiqueta]` compara dos cursos, o un curso con una versión aprobada, apartado por apartado (lo añadido y lo quitado).
- 2026-11-04 · El vigía también avisa de las normas en que el PCCF deja de apoyarse (p. ej., la resolución de instrucciones del curso anterior).
- 2026-11-04 · Vigía normativo (ADR-016): `python -m pccf vigia <SIGLA> <curso>` dice qué normas han cambiado desde la última revisión del PCCF (documento publicado distinto, referencias posteriores del real decreto, texto consolidado o vigencia, normas que entran o salen del marco normativo) y qué apartados y bloques se apoyan en cada una; también las disposiciones nuevas y las citas que el catálogo no conoce. No toca ningún texto; `--revisado` fija el punto de partida de la próxima revisión. Índice de citas: las de los bloques, por id o por nombre, y lo que se calcula del catálogo.
- 2026-11-04 · El contenido del PCCF sigue la guía práctica de la DGFP (ADR-014): cada apartado lleva su punto de la guía y se suman el 19 («Otros aspectos del proyecto curricular») y el 20 («Las programaciones didácticas de los módulos y/o proyectos»), que la guía añade a los 18 del decreto.
- 2026-11-04 · Word con diseño propio (ADR-015): portada a sangre con las siglas del ciclo, control del documento con registro de revisiones, contenido enlazado, apertura de cada apartado con su base normativa y su punto de la guía, «Pendiente» con lo que pide la guía, matriz módulo × competencia apaisada, organización de los módulos (apartado 7), relación de programaciones (20) y anexos A (ficha de empresa) y B (programa formativo personalizado). Fuentes Barlow incrustadas; sin marca de agua.
- 2026-11-03 · Word del PCCF: plantilla sacada de la de Programaciones, con la portada del PCCF; índice enlazado; apartados 1 (identificación y equipo docente), 2 (normativa), 4 (contribución de cada módulo a las competencias) y los bloques de texto (16, Atención a la diversidad); «Pendiente» en lo demás y marca «BORRADOR». Orden `python -m pccf generar`.
- 2026-11-03 · Núcleo del MVP: lector del catálogo de Programaciones, apartados de GM y GS (art. 8.4), esquemas de la carpeta de datos (bloque, equipo y departamentos), carga y comprobación de la carpeta y cálculo de los apartados 1, 2 y 4, con pruebas sobre datos ficticios.
- 2026-11-03 · Decisiones: vigía sin resumen generado (ADR-010), competencias para la empleabilidad = personales y sociales del título (ADR-011), departamentos y orden de los ciclos (ADR-012).
- 2026-11-03 · Entorno de desarrollo: `requirements.txt`, `requirements-dev.txt` y `Makefile` (`make venv` en `~/.venvs/pccf`, `make comprobar`).
- 2026-11-03 · Maqueta v0 aprobada: es la referencia de la interfaz.
- 2026-10-28 · Documentación de partida: `README.md`, `PRD.md`, `ARCHITECTURE.md`, `DESIGN.md`, `docs/DECISIONES.md`, `docs/PENDIENTE.md` y `docs/INVESTIGACION.md` (marco normativo comprobado, guía de la DGFP y API del BOE y el DOGV).
- 2026-10-28 · Alcance: todos los ciclos y departamentos del centro (GB con sus 17 apartados).
- 2026-10-28 · Repositorio público con la barrera de secretos (gancho y CI «Secretos») y licencia MIT.
- 2026-10-28 · Maqueta v0 de la interfaz, para aprobar (`../Maqueta v0 (2026-10-28)/`).
