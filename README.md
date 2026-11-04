# PCCF

App de escritorio para generar el **Proyecto Curricular de Ciclo Formativo** de FP (Decreto 114/2025, art. 8.4) desde datos estructurados, en Word con diseño propio del centro. El contenido sigue la guía práctica del PCCF de la Dirección General de FP de la Generalitat Valenciana. Para todos los ciclos y departamentos de EPLA (grado básico, medio y superior). App hermana de [Programaciones](https://github.com/cferrerobonet/programaciones_fp), cuyo catálogo curricular lee.

**Estado:** MVP en curso (2026-11-04): interfaz, Word con diseño propio y los apartados 1, 2, 4 y 16, vigía normativo, «Nuevo curso» y «Comparar»; falta la primera versión instalable. Licencia MIT.

| Documento | Qué cuenta |
| --- | --- |
| [PRD.md](PRD.md) | Qué hace, para quién, los 20 apartados y la hoja de ruta |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Stack, componentes, modelo de datos, carpetas y vigía |
| [DESIGN.md](DESIGN.md) | Interfaz y documento |
| [docs/DECISIONES.md](docs/DECISIONES.md) | Decisiones fechadas |
| [docs/PENDIENTE.md](docs/PENDIENTE.md) | Lo que falta por decidir o por recibir |
| [docs/INVESTIGACION.md](docs/INVESTIGACION.md) | Fuentes, textos literales y pruebas de las API del BOE y el DOGV |
| [CHANGELOG.md](CHANGELOG.md) | Cambios por versión |

Instalación: cuando exista la primera versión. En desarrollo: `make venv` y `PYTHONPATH=src ~/.venvs/pccf/bin/python -m pccf` (sin argumentos abre la interfaz; `python -m pccf generar <SIGLA> <curso>` y las demás órdenes, sin ella).
