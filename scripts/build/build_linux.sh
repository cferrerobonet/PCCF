#!/bin/bash
# Compila la app en Linux (x86_64) y la empaqueta en un tar.gz portable. Copia del de Programaciones.
# Solo lo ejecuta la CI (compilar.yml): no se compila en local.
#   PY=<python>     intérprete con las dependencias (por defecto, python3 del sistema)
# El tar.gz lleva la app, un lanzador, el icono y el script que crea el acceso directo del menú. La carpeta dist/ se
# deja: la CI comprueba el paquete y arranca la app desde ella.
set -euo pipefail
cd "$(dirname "$0")/../.."

APP_NAME="PCCF"
PY="${PY:-$(command -v python3)}"
VERSION=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)
# Nombre fijo del instalador: lo usa el actualizador de la app (actualizaciones.py).
ARCH="x86_64"
SALIDA="PCCF-${VERSION}-Linux-${ARCH}.tar.gz"
echo "== $APP_NAME $VERSION → $SALIDA"
[ "$(uname -m)" = "$ARCH" ] || { echo "La máquina es $(uname -m) y el paquete es para $ARCH"; exit 1; }

[ -d catalogo ] || "$PY" scripts/catalogo.py bajar   # el catálogo publicado y firmado que va dentro
rm -rf build dist
"$PY" -m PyInstaller PCCF.spec --clean --noconfirm
APP_PATH="dist/${APP_NAME}"
[ -d "$APP_PATH" ] || { echo "No se generó $APP_PATH"; exit 1; }
[ -x "$APP_PATH/$APP_NAME" ] || { echo "No se generó el ejecutable $APP_PATH/$APP_NAME"; exit 1; }

# El icono lo lleva el acceso directo del menú, no el ejecutable.
cp imagenes/icono.png "$APP_PATH/icono.png"

cat > "$APP_PATH/${APP_NAME}.sh" <<'SH'
#!/bin/sh
# Lanzador de PCCF en Linux: arranca la app desde la carpeta donde está.
CARPETA="$(cd "$(dirname "$0")" && pwd)"
chmod +x "$CARPETA/PCCF" 2>/dev/null || true
exec "$CARPETA/PCCF" "$@"
SH
chmod +x "$APP_PATH/${APP_NAME}.sh"

cat > "$APP_PATH/instalar.sh" <<'SH'
#!/bin/sh
# Acceso directo de PCCF en el menú de aplicaciones (XDG) y permiso de ejecución.
CARPETA="$(cd "$(dirname "$0")" && pwd)"
DESTINO="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$DESTINO"
cat > "$DESTINO/pccf.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=PCCF
Comment=Proyecto curricular de los ciclos formativos de EPLA
Exec=$CARPETA/PCCF.sh
Icon=$CARPETA/icono.png
Terminal=false
Categories=Office;Education;
EOF
chmod +x "$CARPETA/PCCF" "$CARPETA/PCCF.sh" 2>/dev/null || true
echo "Acceso directo creado: $DESTINO/pccf.desktop"
echo "Para actualizar, extrae el tar.gz nuevo encima de esta carpeta."
SH
chmod +x "$APP_PATH/instalar.sh"

cat > "$APP_PATH/LEEME.txt" <<'TXT'
PCCF para Linux (carpeta portable)

1. Ejecuta «PCCF.sh» (o el archivo «PCCF») para abrir la app.
2. Si quieres que aparezca en el menú de aplicaciones, ejecuta «instalar.sh» una vez.
3. Para actualizar, descarga el tar.gz nuevo y extráelo encima de esta carpeta.

El registro de la app va en ~/.local/share/PCCF; el PCCF, en la carpeta de datos que se elige en Ajustes.
TXT

tar -czf "$SALIDA" -C dist "$APP_NAME"
echo "Creado: $SALIDA ($(du -h "$SALIDA" | cut -f1))"
