# PCCF — producto

Qué es la app, para quién y qué debe hacer. Técnica: [ARCHITECTURE.md](ARCHITECTURE.md) · diseño: [DESIGN.md](DESIGN.md) · decisiones: [docs/DECISIONES.md](docs/DECISIONES.md) · fuentes y textos literales: [docs/INVESTIGACION.md](docs/INVESTIGACION.md).

## 1. Qué es

App de escritorio para generar el **Proyecto Curricular de Ciclo Formativo (PCCF)** de los ciclos de FP del departamento de Electricidad y Electrónica de EPLA (centro concertado, Comunitat Valenciana), en Word con la plantilla del centro.

**Idea clave:** la fuente de verdad son los **datos estructurados**, no los documentos. El PCCF se genera desde datos (módulos, RA, horas, competencias, contribución de cada módulo, empresas de FE…) y textos en bloques, para que sea coherente por construcción con las programaciones didácticas, que genera la app hermana **Programaciones** con el mismo catálogo.

## 2. Marco normativo

| Norma | Para qué |
| --- | --- |
| Decreto 114/2025, de 29 de julio (DOGV-C-2025-29742); anexos de horarios en la redacción del Decreto 95/2026 (DOGV-C-2026-21170) y su corrección (DOGV-C-2026-22324) | Art. 8: el PCCF y sus 18 apartados mínimos; art. 8.2: dos años desde la implantación del título. Art. 9: programación didáctica (la hace Programaciones) |
| RD 659/2023 (BOE-A-2023-16889), consolidado, modificado por el RD 658/2024 | Ordenación del sistema de FP |
| RD de cada título (SEA: RD 1127/2010, BOE-A-2010-15355, modificado por los RD 401/2023 y 500/2024) | Identificación, perfil, competencias, módulos y orientaciones pedagógicas |
| Orden 8/2025, de 22 de abril (DOGV-C-2025-13083), modificada por la Orden 5/2026 (DOGV-C-2026-10102) | Evaluación en los ciclos LOFP |
| Resolución de instrucciones de inicio de curso (2026-2027: de 16 de julio de 2026, DOGV-C-2026-24495) | §6: quién elabora y aprueba el PCCF; §17.8.1: actividades del profesorado durante la FE; §19.1: evaluación del PCCF (la CCP propone al claustro el plan; evalúa el equipo educativo) |
| Guía práctica de la DGFP para el PCCF (2025) | Orientativa y anterior al Decreto 114/2025 |

El vigía (§6) mantiene esta tabla al día; la vigencia comprobada y los enlaces están en `docs/INVESTIGACION.md`.

## 3. Personas

| Quién | Qué hace |
| --- | --- |
| **CarlosFB** (profesor del departamento y desarrollador; no es jefe de departamento) | Mantiene la app y la carpeta de datos del PCCF con git; mete lo que acuerda el equipo |
| Equipo docente del ciclo (incluido el profesorado de materias no profesionales) | Redacta y aporta sus bloques: desde la app (exportar e importar un bloque) o en reunión |
| Jefatura de departamento | Coordina y lidera la elaboración; revisa el borrador en Word y aprueba. No usa la app ni git |
| Jefatura de estudios de FP | Incorpora el PCCF aprobado a la Programación General Anual |

## 4. Tipos de contenido

Cada bloque de texto lleva su tipo como metadato:

| Tipo | Qué es | Ejemplo |
| --- | --- | --- |
| `centro` | Fijo de centro, común a todos los ciclos | Ideario, plan de tutoría, atención a la diversidad |
| `ciclo` | Fijo de ciclo; lo oficial, importado del RD por el catálogo | Identificación, perfil, competencias |
| `anual` | Cambia cada curso; se clona al curso siguiente y hay que confirmarlo | Equipo docente, calendario, empresas, planes del centro |
| `normativo` | Referencias a normas con identificador, artículo citado y estado de vigencia; cada referencia sabe en qué bloques aparece | Marco normativo |
| `derivado` | Tablas y textos calculados desde los datos; nunca se escriben a mano | Matriz módulo × competencia, distribución horaria, RA en FE, criterios del Proyecto intermodular |

## 5. Los 18 apartados (art. 8.4) y su automatización

| # | Apartado (literal) | Tipo | Automatizable |
| --- | --- | --- | --- |
| 1 | Identificación del ciclo formativo | ciclo + anual | Alta |
| 2 | Marco normativo para el desarrollo del proyecto curricular | normativo | Alta |
| 3 | Adecuación y arreglo de las competencias profesionales del título al contexto socioeconómico y cultural del centro | ciclo + derivado | Media: lista del RD; ponderación (%) y motivo, del equipo |
| 4 | Contribución de cada módulo a las competencias profesionales del ciclo | derivado | Alta: orientaciones pedagógicas del RD, ajustable |
| 5 | Contribución de cada módulo a las competencias para la empleabilidad del ciclo | derivado + ciclo | Media (falta la fuente estructurada) |
| 6 | Enfoques didácticos y metodológicos | ciclo | Baja |
| 7 | La organización y distribución de los módulos profesionales | derivado | Alta: horas del Decreto 95/2026 |
| 8 | Criterios de organización, comunicación y desarrollo de la evaluación del aprendizaje | normativo + ciclo | Media |
| 9 | Base de datos de empresas u organismos equiparados para la formación en empresa, y criterios de asignación del alumnado | anual + ciclo | Media |
| 10 | Criterios para la realización de los planes formativos individuales | ciclo + derivado | Media |
| 11 | Criterios para adaptar los módulos de Digitalización y Sostenibilidad a las características específicas del perfil profesional del ciclo formativo | ciclo | Baja |
| 12 | El plan de tutoría y orientación profesional | centro | Baja |
| 13 | Concreción de los planes y programas del centro vinculados al currículo | anual | Baja |
| 14 | Orientaciones para el uso de espacios, medios y equipamientos disponibles | ciclo | Baja (en el futuro, dotación desde la web de Pedidos) |
| 15 | Criterios y procedimientos para la evaluación y revisión de la práctica docente | centro | Baja |
| 16 | Atención a la Diversidad | centro | Baja |
| 17 | Criterios para la planificación de actividades complementarias y extraescolares | ciclo + anual | Baja-media |
| 18 | Criterios para la organización del módulo profesional de Proyecto intermodular | ciclo + derivado | Media |
| — | Propuesta de actividades del profesorado durante la FE (Resolución 2026-2027, §17.8.1) | anual | Baja-media |

## 6. Requisitos

| Id | Requisito |
| --- | --- |
| RF-1 | Generar el PCCF de un ciclo y un curso en `.docx` con la plantilla de las programaciones del centro, con los 18 apartados (los que no tengan contenido, con su título y «pendiente») |
| RF-2 | Editar los bloques de texto (Markdown) con su tipo, estado (borrador o confirmado) y autoría; lo oficial se ve, no se edita |
| RF-3 | Leer del catálogo firmado de Programaciones ciclos, módulos, RA, horas y competencias, y calcular los derivados |
| RF-4 | «Nuevo curso»: clonar el curso anterior; los bloques anuales pasan a borrador y hay que confirmarlos |
| RF-5 | «Comparar» dos cursos o dos versiones aprobadas, por apartado |
| RF-6 | **Vigía normativo**, a mano o programado: detectar modificaciones y derogaciones de las normas citadas (BOE y lo disponible del DOGV) e informar de los bloques afectados. **Nunca reescribe texto**: solo avisa. Opcional: resumen del cambio con un modelo de lenguaje local |
| RF-7 | Exportar e importar un bloque suelto, para que el equipo aporte textos sin la carpeta entera |
| RF-8 | Actualizaciones desde la app, como Programaciones: al arrancar y desde «Acerca de», aviso «↑ Actualizar a X.Y.Z» con las novedades de esa versión (`CHANGELOG.md`) e instalación sin pasos manuales |
| RNF-1 | Todo en local; sin bases de datos en servidor ni nube. La única red permitida: BOE y DOGV (vigía) y la descarga del catálogo publicado de Programaciones |
| RNF-2 | Datos en archivos legibles y editables a mano (YAML y Markdown), en una carpeta con git |
| RNF-3 | Instalación sencilla para el equipo: releases de `github.com/cferrerobonet/PCCF` (repositorio público) con DMG de macOS, instalador y portable de Windows y portable de Linux; para compartir los datos, se pasa la carpeta |
| RNF-4 | Datos personales (docentes, empresas, alumnado) solo en la carpeta de datos, nunca en el repositorio de la app |

## 7. Fuera de alcance

- La programación didáctica de cada módulo (art. 9): la hace Programaciones, que más adelante leerá del PCCF los acuerdos comunes (la Resolución de 2026-2027, §6.1, dice que lo del PCCF no se repite en las programaciones).
- Edición a la vez por varias personas.
- Publicar el PCCF en la web o enviarlo por correo.

## 8. Hoja de ruta

| Fase | Contenido | Estado |
| --- | --- | --- |
| F0 | Diseño, documentación de partida e investigación | Hecha (2026-10-28) |
| F1 | Repositorio con barrera de secretos, maqueta de la interfaz para aprobar y entorno | Pendiente |
| F2 | **MVP**: SEA, curso 2026-2027, apartados 1, 2, 4 y 16 (los cinco tipos de contenido), Word, vigía, «Nuevo curso» y «Comparar» | Pendiente |
| F3 | Resto de apartados de SEA | Pendiente |
| F4 | Resto de ciclos del departamento | Pendiente |
| F5 | Programaciones lee del PCCF los acuerdos comunes | Pendiente |
