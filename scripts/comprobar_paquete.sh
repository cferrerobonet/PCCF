#!/bin/bash
# Comprueba que la app compilada lleva dentro lo que necesita: catálogo (con su versión), apartados, esquemas,
# plantilla (con «_rels/.rels»), escudo, tipografías, icono, la clave pública del catálogo publicado y las bibliotecas
# de QtPdf. Lo ejecuta la CI (compilar.yml) tras compilar, en las tres plataformas (copia del de Programaciones).
# Uso: scripts/comprobar_paquete.sh <dist/PCCF | dist/PCCF.app>
set -uo pipefail
raiz="${1:?Uso: scripts/comprobar_paquete.sh <carpeta de la app compilada>}"
[ -d "$raiz" ] || { echo "No existe $raiz"; exit 1; }
fallo=0
buscar() {  # $1 = descripción; resto = expresión de find
    local que="$1"; shift
    local hallado
    hallado=$(find "$raiz" "$@" -print 2>/dev/null | head -1)
    if [ -n "$hallado" ]; then echo "OK    $que: ${hallado#"$raiz"/}"; else echo "FALTA $que"; fallo=1; fi
}
buscar "catálogo: normativa"        -path '*catalogo/normativa.yaml'
buscar "catálogo: ciclo SEA"        -path '*catalogo/ciclos/SEA.yaml'
buscar "catálogo: módulo 0517"      -path '*catalogo/modulos/0517.yaml'
buscar "catálogo: versión"          -path '*catalogo/version.yaml'
buscar "clave pública del catálogo" -path '*pccf/recursos/clave_catalogo.txt'
buscar "apartados de GM y GS"       -path '*pccf/recursos/apartados/gm-gs.yaml'
buscar "esquema del bloque"         -path '*pccf/esquemas/bloque.json'
buscar "plantilla: document.xml"    -path '*pccf/recursos/plantilla/es/word/document.xml'
buscar "plantilla: _rels/.rels"     -path '*pccf/recursos/plantilla/es/_rels/.rels'
buscar "plantilla: metadatos"       -path '*pccf/recursos/plantilla/plantilla.yaml'
buscar "escudo del centro"          -path '*pccf/recursos/imagenes/escudo.png'
buscar "tipografía Barlow"          -name 'Barlow-Regular.ttf'
buscar "tipografía JetBrains Mono"  -name 'JetBrainsMono.ttf'
buscar "icono de la app"            -path '*pccf/recursos/icono.png'
buscar "módulo QtPdf de PyQt6"      \( -name 'QtPdf.pyd' -o -name 'QtPdf.abi3.so' -o -name 'QtPdf.*.so' \)
buscar "biblioteca Qt Pdf"          \( -name 'Qt6Pdf.dll' -o -name 'QtPdf.framework' -o -name 'libQt6Pdf.so*' \)
[ $fallo -eq 0 ] && echo "Datos empaquetados: completos" || echo "Datos empaquetados: FALTAN piezas"
exit $fallo
