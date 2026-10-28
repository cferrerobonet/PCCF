# PCCF — diseño

**Regla madre:** la interfaz es **idéntica en diseño a Partes de salida y Programaciones** (familia de apps de CarlosFB): mismos tokens de color (verde EPLA y dorado, neutros verdosos, claro y oscuro), tipografías (Barlow Condensed, Barlow, JetBrains Mono), barra superior, ventanas modales, campos, botones, chips, avisos y listados. Referencia: `DESIGN.md` de Programaciones (`../../PROGRAMACIONES/PROGRAMACIONES - CÓDIGO FUENTE/DESIGN.md`) y su `ui/estilo.py`. Aquí solo va lo propio del PCCF.

**Maqueta:** `../Maqueta v0 (2026-10-28)/` (HTML con seis pantallas, una captura de cada una y su generador en `_generador/`, con los datos reales de SEA del catálogo), pendiente de aprobar por CarlosFB antes de programar la interfaz. En la maqueta, las zonas miden 280 · flexible · 290 px en la ventana de 1100 × 700, para que la tabla de 19 competencias quepa en el centro; los anchos definitivos se fijan al aprobarla.

## Norte

**«La mesa del equipo».** Se usa a principio de curso y en las revisiones, con calma y mucho que comprobar: **elegir ciclo y curso → recorrer los 18 apartados → completar o confirmar bloques → vista previa → exportar**. Todo a la vista y en orden.

## Reglas

- **Tres zonas** (heredada): apartados (300 px) · bloques del apartado (flexible) · estado, vista previa y exportar (340 px), con «Exportar» siempre abajo a la derecha.
- **Lo oficial, de solo lectura:** lo que viene del catálogo se ve en gris (`surface2`) con su fuente («BOE · comprobado el …») y no se edita.
- **Lo derivado no se escribe:** las tablas calculadas se ven como tablas de solo lectura con «Se calcula de…»; lo que el equipo ajusta (ponderación, contribución) va aparte, con su motivo.
- **El tipo se ve siempre:** cada bloque lleva su chip de tipo (`centro`, `ciclo`, `anual`, `normativo`, `derivado`) con su color fijo.
- **Heredado hasta que se confirma:** un bloque anual clonado del curso anterior lleva la banda dorada «Heredado de 2025-2026 · revisa y confirma» y no cuenta como hecho.
- **Los textos fijos de la plantilla no aparecen en la interfaz:** solo en la vista previa y en el documento.
- **La vista previa es el mismo documento** convertido a PDF, con la marca «BORRADOR».

## Pantallas

| Pantalla | Qué tiene |
| --- | --- |
| Principal (tres zonas) | Izquierda: ciclo y curso, y los 18 apartados con su número, título corto, chips de tipo e icono de estado (pendiente, en borrador, confirmado). Centro: los bloques del apartado elegido. Derecha: progreso (apartados confirmados de 18), avisos del vigía, vista previa y «Exportar» |
| Apartado con texto | Bloques Markdown con su chip de tipo, autoría y estado; «Confirmar bloque»; «Importar bloque…» |
| Apartado derivado | Tabla calculada de solo lectura (p. ej. módulo × competencia) con su fuente, y debajo los ajustes del equipo con su motivo |
| Marco normativo | Lista de normas con su estado (vigente, modificada, derogada) y, en cada una, los bloques que la citan |
| Vigía | Informe de la última revisión: normas con cambios, qué cambia, enlace y bloques afectados; «Marcar como revisado» |
| Nuevo curso y Comparar | Ventana modal: curso de origen y destino; comparación por apartado con lo añadido y lo quitado |

## Colores de los tipos de contenido

| Tipo | Chip |
| --- | --- |
| `centro` | `surface2` con texto `muted` |
| `ciclo` | `accent_soft` con texto `accent` |
| `anual` | `gold_soft` con texto `gold` |
| `normativo` | azul suave (token nuevo, a proponer a la familia) |
| `derivado` | blanco con borde `line` y texto `fg` en mono |

## Documento

El `.docx` usa la plantilla de las programaciones del centro (encabezado, pie, tipografías, índice automático y legislación con hipervínculo), con los 18 apartados del art. 8.4 con sus títulos literales.
