# PCCF — diseño

**Regla madre de la interfaz:** es **idéntica en diseño a Partes de salida y Programaciones** (familia de apps de CarlosFB): mismos tokens de color (verde EPLA y dorado, neutros verdosos, claro y oscuro), tipografías (Barlow Condensed, Barlow, JetBrains Mono), barra superior, ventanas modales, campos, botones, chips, avisos y listados. Referencia: `DESIGN.md` de Programaciones (`../../PROGRAMACIONES/PROGRAMACIONES - CÓDIGO FUENTE/DESIGN.md`) y su `ui/estilo.py`. Aquí solo va lo propio del PCCF.

**Maqueta:** `../Maqueta v0 (2026-10-28)/` (HTML con siete pantallas —apartados 1, 2, 4 y 16, vigía, nuevo curso y el selector con los 15 ciclos del centro—, una captura de cada una y su generador en `_generador/`, con los datos reales de SEA del catálogo), **aprobada por CarlosFB el 2026-11-03 sin cambios**: es la referencia de la interfaz. Las zonas miden 280 · flexible · 290 px en la ventana de 1100 × 700, para que la tabla de 19 competencias quepa en el centro.

## Norte

**«La mesa del equipo».** Se usa a principio de curso y en las revisiones, con calma y mucho que comprobar: **elegir ciclo y curso → recorrer los 20 apartados → completar o confirmar bloques → vista previa → exportar**. Todo a la vista y en orden.

## Reglas

- **Tres zonas** (heredada): apartados (300 px) · bloques del apartado (flexible) · estado, vista previa y exportar (340 px), con «Exportar» siempre abajo a la derecha.
- **Lo oficial, de solo lectura:** lo que viene del catálogo se ve en gris (`surface2`) con su fuente («BOE · comprobado el …») y no se edita.
- **Lo derivado no se escribe:** las tablas calculadas se ven como tablas de solo lectura con «Se calcula de…»; lo que el equipo ajusta (ponderación, contribución) va aparte, con su motivo.
- **El tipo se ve siempre:** cada bloque lleva su chip de tipo (`centro`, `ciclo`, `anual`, `normativo`, `derivado`) con su color fijo.
- **Heredado hasta que se confirma:** un bloque anual clonado del curso anterior lleva la banda dorada «Heredado de 2025-2026 · revisa y confirma» y no cuenta como hecho.
- **Los textos fijos de la plantilla no aparecen en la interfaz:** solo en la vista previa y en el documento.
- **La vista previa es el mismo documento** convertido a PDF, en estado borrador.
- **La guía a la vista** (ADR-014): cada apartado enseña, en una caja plegable de solo lectura como la del currículo, su punto de la guía de la DGFP («Guía · 2.3.2»), lo que pide en una frase y su ejemplo del anexo I cuando lo hay. Sale del índice de la guía, no se escribe en la interfaz.

## Pantallas

| Pantalla | Qué tiene |
| --- | --- |
| Principal (tres zonas) | Izquierda: ciclo (agrupado por familia o departamento y grado, con buscador: son 15 ciclos) y curso, y los apartados de su grado (20 en GM y GS: los 18 del decreto y los 2 de la guía; 19 en GB) con su número, título corto, chips de tipo e icono de estado (pendiente, en borrador, confirmado). Centro: los bloques del apartado elegido. Derecha: progreso (apartados confirmados de 20), avisos del vigía, vista previa y «Exportar» |
| Apartado con texto | Bloques con su chip de tipo, autoría y estado, editados como en Word; «Confirmar bloque»; «Importar Word…» |
| Ajustes | Como en Programaciones y Partes de salida (ADR-022): menú lateral de 220 px en `surface2` y, a la derecha, el apartado con su título en Barlow Condensed y filas «etiqueta | control» con la ayuda debajo; cada cambio se guarda al momento y los errores salen en rojo con «✕» bajo su campo (ADR-025). Apartados: **Carpetas** (datos y catálogo, «Elegir…», «Abrir», «Volver al automático») · **Documento** (programa del PDF, correo del pie) · **Versión y catálogo** (versión con «Buscar actualizaciones» y «Acerca de…», versión y origen del catálogo, «Comprobar ahora», carpeta de la app) |
| Apartado derivado | Tabla calculada de solo lectura (p. ej. módulo × competencia) con su fuente, y debajo los ajustes del equipo con su motivo |
| Marco normativo | Lista de normas con su estado (vigente, modificada, derogada) y, en cada una, los bloques que la citan |
| Vigía | Informe de la última revisión: normas con cambios, qué cambia, enlace y bloques afectados; «Marcar como revisado» |
| Nuevo curso y Comparar | Ventana modal: curso de origen y destino; comparación por apartado con lo añadido y lo quitado |

### Cómo está hecha (ADR-018)

- **Avance (ADR-024)**, encima de la lista: «N apartados en GS · X completos · Y por completar» (y «⚠ N con aviso del vigía»), una barra en tres colores (confirmado `accent`, listo `accent_soft_fuerte`, por completar `pend`) y tres filtros en chip: «Todos», «Completar N» y «Aprobar N». Pedir un apartado que el filtro esconde vuelve a «Todos».
- **Lista de apartados:** cada fila con una franja de 4 px a la izquierda y el número en su cuadro según el avance: **por completar**, ciruela (`pend_soft` y `pend`) con borde discontinuo y «● Faltan N cosas» o «● Sin contenido»; **listo para aprobar**, verde claro y «◆ Listo · falta confirmarlo»; **confirmado**, verde lleno y «✓ Confirmado». El aviso del vigía va aparte, «⚠ vigía» en `warn`, sin tapar el avance. Título cortado al ancho; la ayuda lo da entero, con su motivo y la lista de lo que falta. El panel de la derecha cuenta los completos y pone primero los que se pueden confirmar ya.
- **Apartado:** cabecera con el número «de 20», el título, los chips, la base (norma · punto de la guía) y el estado; debajo, la caja plegable de la guía y, si toca, el aviso dorado del vigía con «Ver informe ›». Lo calculado va en cajas grises «Del catálogo» con su fuente; el 1 añade «Del centro» (departamento, jefatura, tutorías) y el equipo docente con «Confirmar equipo» si está heredado o en borrador y «Abrir equipo.yaml»; el 2, sus normas con lo que dice el vigía y cuántos usos tiene cada una, y las citas sin vigilar; el 3, las competencias con el peso pendiente; el 4, la matriz con puntos verdes y «sin orient.» en oro; el 7 y el 20, sus tablas.
- **Bloque:** banda dorada «Heredado de … · revisa y confirma» o «En borrador · revisa y confirma» con «Confirmar bloque»; chip de tipo, nombre del archivo y autoría; editor como en Word (ADR-020) con su barra de chips (Subtítulo, N, Viñetas, Enlace…, Nota interna; ⌘B y ⌘K), que se guarda solo y nunca enseña Markdown: los subtítulos más grandes y en negrita, los enlaces subrayados y las notas internas sombreadas en ámbar y en cursiva; citas como chips azules (en ámbar las que el catálogo no conoce); «Exportar a Word…». Al final de cada apartado que admite texto, la caja discontinua con «Añadir bloque» e «Importar Word…» (un Word exportado vuelve a su bloque; cualquier otro, a un bloque nuevo del apartado).
- **Derecha:** progreso, lo que necesita atención (revisar, heredado, borrador; se pulsa para ir), avisos dorados con «Ir ›», miniatura de la portada tras la vista previa, formatos Word y PDF y «Exportar» abajo.
- **Barra:** «§ Vigía · N normas cambiadas» en dorado si hay cambios; «al día» o «sin revisar» en verde si no. El botón del ciclo y el curso abre la lista de cursos de la carpeta de datos.
- Ninguna zona se ensancha por su contenido: los textos y los chips se parten y las tablas ajustan sus columnas (lo comprueban las pruebas en los 20 apartados).

## Colores de los tipos de contenido

| Tipo | Chip |
| --- | --- |
| `centro` | `surface2` con texto `muted` |
| `ciclo` | `accent_soft` con texto `accent` |
| `anual` | `gold_soft` con texto `gold` |
| `normativo` | `azul_soft` con texto `azul` (tokens nuevos de la familia: `#e4edf6` / `#2f5d8a` en claro, `#1c2a38` / `#8fb6de` en oscuro); también las citas |
| `derivado` | blanco con borde `line` y texto `fg` en mono |

## Documento

**Regla madre del documento (ADR-015):** el Word del PCCF tiene **diseño propio**, distinto del de las programaciones: corporativo (verde EPLA y oro, familia Barlow, escudo del centro), formal y con carácter editorial. **Contenido:** el de la guía práctica de la DGFP, apartado por apartado (ADR-014; índice de la guía en `../GUÍA PCCF (DGFP 2024-2025)/`). **Maqueta:** `../Maqueta documento v1 (2026-11-04)/` (HTML y PDF de ocho páginas con los datos de SEA del catálogo, capturas y su generador en `_generador/`), **aprobada por CarlosFB el 2026-11-04** y programada: el Word sale ya con este diseño.

### Norte: «el expediente del ciclo»

Un documento oficial que el departamento firma y la jefatura de estudios incorpora a la PGA, y que el profesorado consulta durante dos cursos. Tiene que verse **serio y propio del centro**, ordenado como un expediente técnico (cada apartado con su base normativa, lo calculado con su fuente, lo pendiente a la vista) y **no como una plantilla**. Lo hacen reconocible la portada a sangre, la columna de margen con los números de apartado y las tablas sin rejilla.

### Lo que no se hace

Evitan el aspecto de documento genérico o de documento generado por IA (anti-patrones habituales del diseño editorial, adaptados al papel):

- Etiquetas o «antetítulos» encima de los títulos; la base normativa va **debajo** del título.
- Avisos o citas con barra lateral de color, cajas redondeadas, sombras, degradados o iconos de adorno; emojis o símbolos Unicode como iconos.
- Tablas con rejilla completa y cabecera de fondo saturado; texto centrado en celdas de texto.
- Tipos del sistema (Calibri, Arial, Aptos) como voz del documento: la familia Barlow va **incrustada** en el `.docx`.
- Logotipos repetidos en cada página: el escudo, solo en la portada.
- Marca de agua diagonal «BORRADOR»: el estado va en la portada y en el encabezado.
- Números de sección de adorno: los números grandes son los de los apartados, que la norma y la guía usan para citarlos.
- Monoespaciada: los códigos de módulo y RA van en Barlow Condensed SemiBold (la monoespaciada de la maqueta no se incrusta bien en Word por ser variable).

### Significado de los colores (ADR-025)

Cada significado tiene su color y su distintivo de forma (también para quien no distingue bien los colores). Error, aviso y consejo son los de Programaciones (su ADR-046).

| Significado | Token | Distintivo | Dónde |
| --- | --- | --- | --- |
| Error: no se puede hacer o no vale | `danger`, `danger_soft` | ✕ | Carpeta de datos ilegible, dato que no vale en Ajustes, apartado que no se puede enseñar |
| Aviso: ha cambiado algo y hay que mirarlo | `warn`, `warn_soft` | ⚠ / «!» | Vigía, citas sin vigilar, heredado del curso anterior, sin conexión |
| Consejo y borrador: qué toca hacer | `info`, `info_soft` | ⓘ / punto azul | Lo que pide la guía, «En borrador · revisa y confirma» |
| Por completar: falta contenido | `pend`, `pend_soft` (ciruela) | ● / borde discontinuo | Avance de la barra lateral, notas internas del editor y de Word, módulos sin orientación del RD |
| Completo | `accent`, `accent_soft`, `accent_soft_fuerte` | ✓ / ◆ | Confirmado, listo para aprobar, códigos de módulo |
| Marca | `gold`, `gold_soft` | — | Número del apartado, «Actualizar», novedades, chip `anual` |

Los avisos, los errores y lo que falta no usan nunca el oro.

### Tokens

| Token | Valor | Uso |
| --- | --- | --- |
| `verde-900` | `#14401A` | Bloque de portada, títulos de apartado |
| `verde-700` | `#206028` | Números de apartado, filete de cabecera de tabla, celdas de la matriz, etiquetas |
| `verde-050` | `#F3F7F3` | Reservado (no se usa como fondo de tabla) |
| `oro` | `#C98A1E` | Filetes de acento (bajo el número, sobre el número de página), banda y etiqueta de borrador, filetes de «Pendiente» |
| `oro-texto` | `#8A5A0B` | Texto en oro sobre blanco (contraste ≥ 4,5:1) |
| `tinta` / `tinta-2` / `tinta-3` | `#1E2420` / `#47504A` / `#6E7771` | Texto, secundario, fuentes y pie |
| `línea` / `línea-2` | `#D5DBD6` / `#ECEFEC` | Filetes entre filas; celda de la matriz sin contribución |

| Papel | Tipo | Cuerpo |
| --- | --- | --- |
| Siglas de portada | Barlow Condensed ExtraBold | 178 pt, o la que quepa en su celda |
| Nombre del ciclo en la portada | Barlow Condensed SemiBold | 14-64 pt, calculada para ocupar el alto de las siglas (ADR-021) |
| Número de apartado | Barlow Condensed ExtraBold | 46 pt (40 en página apaisada) |
| Título de apartado (Título 1) | Barlow Condensed Bold | 19 pt, interlineado 1,06 |
| Subapartado (Título 2) | Barlow SemiBold; número en Barlow Condensed Bold | 11 pt |
| Etiquetas, cabeceras de tabla, base normativa, encabezado | Barlow Condensed SemiBold, versalitas con espaciado 0,07-0,12 em | 7,4-7,8 pt |
| Texto | Barlow Regular, interlineado 1,45 | 9,6 pt |
| Tablas | Barlow Regular | 8,4 pt (7,6 en la matriz) |
| Citas literales de normas | Barlow Italic | 9,3 pt |
| Códigos (módulo, RA) | Barlow Condensed SemiBold, `tinta-2` | 8 pt |

### Retícula y página

- A4, márgenes 20 (izq.) · 18 (der.) · 24 (sup.) · 24 mm (inf.). **Columna de margen de 34 mm + 6 mm de calle**: en ella cuelgan los números de apartado y subapartado y las etiquetas de las fichas; el texto corre en la columna de 132 mm (unos 70 caracteres por línea). Las tablas de datos ocupan el ancho completo.
- **Encabezado:** «PROYECTO CURRICULAR · SIGLA · CURSO» a la izquierda (verde) y, si es borrador, la etiqueta «BORRADOR» en oro a la derecha; filete fino debajo.
- **Pie:** título del apartado en curso a la izquierda (campo `STYLEREF` de Título 1) y número de página grande (Barlow Condensed Bold 15 pt, verde) con «/ total» pequeño y un filete de oro de 9 mm encima.
- Los apartados no empiezan página: se mantienen con lo siguiente y llevan 9 mm de aire antes. Las tablas anchas (más de 12 columnas: matrices de los apartados 4 y 5) van en una **sección apaisada** con el mismo encabezado y pie.

### Piezas

| Pieza | Cómo es |
| --- | --- |
| Portada (sección sin márgenes) | Bloque `verde-900` a sangre en los dos tercios superiores: arriba, centro y curso en versalitas; «Proyecto curricular / de ciclo formativo» en blanco con filete de oro; siglas del ciclo enormes abajo a la izquierda y, a su derecha, el nombre del ciclo alineado a la derecha, como el código y el nombre del módulo en Programaciones: ocupa el alto de las siglas, de lo alto de las mayúsculas a la base de la última línea, sin dejar sola una palabra corta; si es corto y no cabe más grande a lo ancho, apoya en la base de las siglas (ADR-021). Si es borrador, banda de oro «Borrador · pendiente de aprobación por el departamento». Debajo, ficha en 3 × 3 (título, grado y horas, familia, departamento, jefatura, curso, real decreto, currículo, revisión). Al pie, escudo, nombre y dirección del centro, y la base normativa (el decreto de currículos del grado, art. 8; Resolución de inicio de curso, §6.2) |
| Control del documento | Página 2: elaboración, coordinación, aprobación, incorporación a la PGA, evaluación del PCCF y vigencia; **registro de revisiones** (revisión, fecha, apartados, motivo, estado), que pide la guía (2.2: documento vivo con sus mecanismos de revisión); firmas de la jefatura del departamento, la jefatura de estudios de FP y la dirección |
| Contenido | Índice enlazado en tres grupos: apartados del art. 8.4, apartados que añade la guía (19 y 20) y anexos. Número en la columna de margen, título y página a la derecha **sin puntos guía**; los apartados sin contenido llevan «pendiente» en oro |
| Apertura de apartado | Número en la columna de margen con filete de oro debajo; título; debajo, la **base**: norma y artículo · punto de la guía · origen de los datos («Se calcula del RD…», «Bloque de centro · borrador», «Vigía: comprobado el…») |
| Texto | Párrafos y viñetas (marcador verde) en la columna de texto; negrita en `verde-900` |
| Cita literal de una norma | Sangrada 6 mm, cursiva, con la norma y el artículo debajo en versalitas verdes; **sin barra lateral** |
| Pendiente / Borrador / Heredado | Filetes de oro arriba y abajo (sin caja ni barra lateral): etiqueta en oro a la izquierda y, a la derecha, qué pide la guía y qué falta, o qué queda por revisar y confirmar (un texto en borrador; el equipo docente o un bloque heredado del curso anterior) |
| Tabla | Sin líneas verticales ni fondos: cabecera en versalitas `verde-900` con filete `verde-700` de 1,3 pt; filas con filete `línea` de 0,5 pt; números a la derecha; filas de grupo («1.º curso») en versalitas verdes; fila de total con filete superior; **fuente** debajo en 7,4 pt |
| Ficha (etiqueta · valor) | Etiqueta en la columna de margen y valor a la derecha, con filetes entre filas (apartado 1, control del documento) |
| Matriz módulo × competencia | Celda rellena `verde-700` = contribuye; `línea-2` = no contribuye; vacía y «sin orientación» en oro = el RD no le asigna ninguna (módulos nuevos de la LO 3/2022, que decide el equipo). Columna final con el número de competencias |
| Anexo | Letra (A, B…) en lugar de número; campos de ficha con línea de puntos para rellenar |

### Contenido por apartado

Los apartados, sus títulos y su punto de la guía están en `src/pccf/recursos/apartados/gm-gs.yaml`; qué pide la guía en cada uno, en su índice (`../GUÍA PCCF (DGFP 2024-2025)/GUÍA PCCF — Índice.md`).

| Parte | Contenido |
| --- | --- |
| 1 | Ficha de identificación (ciclo, título, grado, familia, real decreto enlazado, duración, centro, departamento y jefatura, tutorías, curso) y 1.1 Equipo docente |
| 2 | 2.1 Normativa estatal y 2.2 Normativa autonómica, con el título completo enlazado, por fecha; normas del centro cuando las haya |
| 3 | Análisis del contexto (bloque del equipo) y tabla de ponderación de las competencias profesionales en % (suma 100), como el anexo I, ap. 1, de la guía |
| 4 | Matriz módulo × competencia (apaisada) y 4.1 con el texto de cada competencia |
| 5 | Matriz módulo × competencia personal y social, sin ponderar, con las dos notas de la guía (anexo I, ap. 3) |
| 7 | Tabla curso · código · módulo del currículo · agrupación del PCCF (anexo I, ap. 5) |
| 9 y 10 | Criterios del equipo; las fichas, en los anexos A y B |
| 14 | Criterios de uso de talleres, laboratorios y aulas y, en un subapartado propio, las **medidas de prevención de riesgos laborales** consensuadas que la guía incluye en el PCCF (2.1) |
| 19 | Otros aspectos acordados por el equipo; aquí van las actividades del profesorado durante la formación en empresa (Resolución de 2026-2027, §17.8.1) |
| 20 | Relación de las programaciones didácticas de los módulos (las genera Programaciones) |
| Anexo A | Ficha de empresa u organismo equiparado (guía, anexo III): información general, contacto, historial de colaboración por curso con alumnado y RA, valoración |
| Anexo B | Programa formativo personalizado (guía, anexo IV) |
| Resto | Sus bloques de texto o «Pendiente» con lo que pide la guía |

### Cómo se construye

- `scripts/plantilla.py crear` construye la plantilla **desde cero** (estilos con nombre propio, viñeta, ajustes, encabezado y pie interiores, pie de portada con el escudo) e **incrusta siete archivos de Barlow** (`src/pccf/recursos/fuentes/`, licencia OFL): Barlow (normal, negrita, cursiva), Barlow SemiBold y Barlow Condensed SemiBold, Bold y ExtraBold, con su clave fija (la misma plantilla da los mismos bytes). `comprobar` verifica marcas, estilos y que cada fuente se recupera.
- `documento.py` escribe el cuerpo: la portada es una sección sin márgenes con una tabla sombreada de alturas fijas; cada apertura, una tabla sin bordes de dos columnas (34 mm + resto); la matriz del apartado 4, una sección apaisada; el pie lleva `STYLEREF "Título de apartado"`, `PAGE \# "00"` y `NUMPAGES`; el contenido, hipervínculos a marcas y `PAGEREF`, que Word actualiza al abrir.
- Comprobado el 2026-11-04 con el validador de OOXML y en PDF con Word y con LibreOffice, mirando todas las páginas: Word usa las siete fuentes incrustadas sin tenerlas instaladas.
