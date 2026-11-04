# Cambios

Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); versiones con [SemVer](https://semver.org/lang/es/). Lo más reciente, arriba.

## [Sin publicar]

### Añadido

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
