# Cambios

Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); versiones con [SemVer](https://semver.org/lang/es/). Lo más reciente, arriba.

## [Sin publicar]

### Añadido

- 2026-11-03 · Word del PCCF: plantilla sacada de la de Programaciones, con la portada del PCCF; índice enlazado; apartados 1 (identificación y equipo docente), 2 (normativa), 4 (contribución de cada módulo a las competencias) y los bloques de texto (16, Atención a la diversidad); «Pendiente» en lo demás y marca «BORRADOR». Orden `python -m pccf generar`.
- 2026-11-03 · Núcleo del MVP: lector del catálogo de Programaciones, apartados de GM y GS (art. 8.4), esquemas de la carpeta de datos (bloque, equipo y departamentos), carga y comprobación de la carpeta y cálculo de los apartados 1, 2 y 4, con pruebas sobre datos ficticios.
- 2026-11-03 · Decisiones: vigía sin resumen generado (ADR-010), competencias para la empleabilidad = personales y sociales del título (ADR-011), departamentos y orden de los ciclos (ADR-012).
- 2026-11-03 · Entorno de desarrollo: `requirements.txt`, `requirements-dev.txt` y `Makefile` (`make venv` en `~/.venvs/pccf`, `make comprobar`).
- 2026-11-03 · Maqueta v0 aprobada: es la referencia de la interfaz.
- 2026-10-28 · Documentación de partida: `README.md`, `PRD.md`, `ARCHITECTURE.md`, `DESIGN.md`, `docs/DECISIONES.md`, `docs/PENDIENTE.md` y `docs/INVESTIGACION.md` (marco normativo comprobado, guía de la DGFP y API del BOE y el DOGV).
- 2026-10-28 · Alcance: todos los ciclos y departamentos del centro (GB con sus 17 apartados).
- 2026-10-28 · Repositorio público con la barrera de secretos (gancho y CI «Secretos») y licencia MIT.
- 2026-10-28 · Maqueta v0 de la interfaz, para aprobar (`../Maqueta v0 (2026-10-28)/`).
