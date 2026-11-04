#!/bin/bash
# Crea los iconos de la app a partir de imagenes/icono.png (1024 × 1024, con transparencia):
#   imagenes/icono.ico   Windows: 16, 24, 32, 48, 64, 128 y 256 px (Pillow). Va en el repositorio.
#   imagenes/icono.icns  macOS (sips e iconutil, solo en macOS). No se versiona: lo rehace la compilación.
# Como scripts/crear_icono.sh de Programaciones. El PNG sale de imagenes/icono.svg.
set -e
cd "$(dirname "$0")/.."
PY="${PY:-$HOME/.venvs/pccf/bin/python}"
[ -f imagenes/icono.png ] || { echo "Falta imagenes/icono.png"; exit 1; }

# Sin Pillow (la CI de macOS no lo instala), se conserva el .ico del repositorio.
if "$PY" -I -c "import PIL" 2>/dev/null; then
"$PY" -I - <<'PY'
from PIL import Image
im = Image.open("imagenes/icono.png").convert("RGBA")
im.save("imagenes/icono.ico", sizes=[(t, t) for t in (16, 24, 32, 48, 64, 128, 256)])
PY
echo "Icono creado: imagenes/icono.ico"
else
    echo "Sin Pillow: se conserva imagenes/icono.ico"
fi

if command -v iconutil >/dev/null 2>&1; then
    SET="$(mktemp -d)/icono.iconset"
    mkdir -p "$SET"
    for t in 16 32 128 256 512; do
        sips -z $t $t imagenes/icono.png --out "$SET/icon_${t}x${t}.png" >/dev/null
        d=$((t * 2))
        sips -z $d $d imagenes/icono.png --out "$SET/icon_${t}x${t}@2x.png" >/dev/null
    done
    iconutil -c icns "$SET" -o imagenes/icono.icns
    rm -rf "$(dirname "$SET")"
    echo "Icono creado: imagenes/icono.icns"
fi
