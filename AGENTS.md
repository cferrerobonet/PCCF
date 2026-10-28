# PCCF — instrucciones para agentes

App de escritorio (Python 3.11 + PyQt6) para generar el **Proyecto Curricular de Ciclo Formativo** (Decreto 114/2025, art. 8.4: 18 apartados) de **todos los ciclos de FP de EPLA y de todos sus departamentos** (GB, GM y GS; ADR-009), desde datos estructurados (YAML y Markdown) y con la plantilla Word del centro. **App hermana de Programaciones**: lee su catálogo curricular firmado y amplía su vigía normativo.

**Estado (2026-10-28):** diseño validado por CarlosFB y documentación de partida escrita; **sin código ni repositorio todavía**.

## Leer antes de empezar

| Qué | Dónde |
| --- | --- |
| Producto: normas, personas, tipos de contenido, los 18 apartados y qué se automatiza, requisitos, hoja de ruta | [PRD.md](PRD.md) |
| Técnica: stack, componentes, modelo de datos, carpetas, vigía · Diseño de la interfaz y del documento | [ARCHITECTURE.md](ARCHITECTURE.md) · [DESIGN.md](DESIGN.md) |
| Decisiones (ADR) · Pendiente · Cambios | [docs/DECISIONES.md](docs/DECISIONES.md) · [docs/PENDIENTE.md](docs/PENDIENTE.md) · [CHANGELOG.md](CHANGELOG.md) |
| Maqueta v0 de la interfaz (HTML y capturas), para aprobar | `../Maqueta v0 (2026-10-28)/` |
| Lo investigado: textos literales (art. 8 y 9 del Decreto 114/2025, Resolución 2026-2027), guía de la DGFP, API del BOE, DOGV, qué se reutiliza de Programaciones | [docs/INVESTIGACION.md](docs/INVESTIGACION.md) |
| App de la que se copia (catálogo, vigía, motor del documento, interfaz, empaquetado) | `../../PROGRAMACIONES/PROGRAMACIONES - CÓDIGO FUENTE/` (su `AGENTS.md` manda allí) |
| Ficha de la app en la bóveda | `../PCCF — Índice.md` |

## Forma de trabajar

- Reglas comunes (palabra prohibida y coautoría, sin datos no se implementa, secretos y datos ficticios, conexiones a IONOS): instrucciones de usuario.
- Castellano en todo: interfaz, código, comentarios, documentación y commits. Fechas `AAAA-MM-DD`.
- **CarlosFB no es jefe de departamento**: mantiene la app y la carpeta de datos con git; la jefatura de departamento coordina y aprueba el PCCF sin usar la app.
- Dudas a CarlosFB **de una en una**, con la opción recomendada primero.
- **Sin datos no se implementa**: lo que falte (textos de centro, equipo docente, empresas) se marca «pendiente» en el documento y se pide; no se inventan normas, RA, horas ni textos.
- **Datos personales** (docentes, empresas, alumnado) solo en la carpeta de datos, nunca en el repositorio de la app; pruebas con datos ficticios.
- Red: solo BOE y DOGV (vigía), el catálogo publicado de Programaciones y las releases de GitHub (actualizaciones). Nada de datos en la nube.
- **Repositorio público** (`github.com/cferrerobonet/PCCF`): secretos y datos personales, barrera común (`scripts/comprobar_secretos.sh`, gancho y CI «Secretos»); reglas en la skill de usuario `barrera-secretos`. Commits en castellano, sin coautoría; `git add` de archivos concretos.
- **Versiones:** cada versión, con su entrada en `CHANGELOG.md` (son las novedades que ve el profesorado al actualizar), etiqueta `vX.Y.Z` y compilación en GitHub, nunca en local.
- Un cambio en el Word generado se comprueba en PDF mirando todas las páginas.
- Documentación al día en la misma tarea: estado actual en `PRD.md`, `ARCHITECTURE.md` y `DESIGN.md` (sin historia); decisiones fechadas en `docs/DECISIONES.md`; cada cambio en `CHANGELOG.md`; la ficha de la bóveda (`../PCCF — Índice.md`), con su historial.

## Próximos pasos (en este orden)

1. Hecho (2026-10-28): repositorio **público** `github.com/cferrerobonet/PCCF` con la barrera de secretos, `.gitignore` y licencia MIT (ADR-008). Versiones, compilación y actualizaciones, como Programaciones (`ARCHITECTURE.md` §6), al montar el MVP.
2. Que CarlosFB apruebe la **maqueta v0** (`../Maqueta v0 (2026-10-28)/`); sus cambios van a `DESIGN.md`.
3. Entorno fuera de iCloud (`~/.venvs/pccf`), con las versiones de `requirements.txt` de Programaciones.
4. **MVP** (SEA, curso 2026-2027, apartados 1, 2, 4 y 16): esquemas y carpeta de datos de ejemplo; lectura del catálogo de Programaciones; tabla módulo × competencia; Word con los cuatro apartados (los demás, «pendiente»); interfaz mínima; informe del vigía; «Nuevo curso» y «Comparar».
5. Lo pendiente de CarlosFB, en `docs/PENDIENTE.md`, de una en una al llegar a cada parte.
6. Alta de la app en la skill `auditoria-apps` (`apps.json` y `apps/<id>.md`) cuando exista el repositorio.
