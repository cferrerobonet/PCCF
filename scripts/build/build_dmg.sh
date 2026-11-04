#!/bin/bash
# Compila «PCCF.app» (arm64) y el DMG instalable en macOS. Copia del de Programaciones.
# Solo lo ejecuta la CI (compilar.yml): no se compila en local.
#   PY=<python>     intérprete con las dependencias (por defecto el venv del proyecto)
# Firma ad-hoc salvo que haya APPLE_DEVELOPER_ID (y notariza si hay APPLE_ID, APPLE_TEAM_ID y APPLE_APP_PASSWORD).
set -e
cd "$(dirname "$0")/../.."

APP_NAME="PCCF"
PY="${PY:-$HOME/.venvs/pccf/bin/python}"
[ -x "$PY" ] || PY="$(command -v python3)"
VERSION=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)
DMG_NAME="PCCF-${VERSION}-macOS-arm64.dmg"
echo "== $APP_NAME $VERSION → $DMG_NAME"

[ -d catalogo ] || "$PY" scripts/catalogo.py bajar   # el catálogo publicado y firmado que va dentro
PY="$PY" scripts/crear_icono.sh
rm -rf build dist
"$PY" -m PyInstaller PCCF.spec --clean --noconfirm
APP_PATH="dist/${APP_NAME}.app"
[ -d "$APP_PATH" ] || { echo "No se generó $APP_PATH"; exit 1; }
ARQ=$(lipo -archs "$APP_PATH/Contents/MacOS/$APP_NAME")
echo "Arquitectura: $ARQ"
[[ "$ARQ" == *arm64* ]] || { echo "La app no es arm64"; exit 1; }

# Nombres con acentos dentro del bundle rompen la firma al copiarlo.
if find "$APP_PATH" -type f | LC_ALL=C grep -q '[^ -~]'; then
    echo "Hay archivos con caracteres no ASCII dentro de la app:"; find "$APP_PATH" -type f | LC_ALL=C grep '[^ -~]'; exit 1
fi

# Se firma FUERA de iCloud: sus atributos extendidos rompen codesign.
TMP="$(mktemp -d)"
ditto --norsrc --noextattr --noqtn "$APP_PATH" "$TMP/${APP_NAME}.app"
xattr -cr "$TMP/${APP_NAME}.app"
if [ -n "${APPLE_DEVELOPER_ID:-}" ]; then
    codesign --force --deep --options runtime --timestamp -s "$APPLE_DEVELOPER_ID" "$TMP/${APP_NAME}.app"
else
    codesign -s - --force --deep "$TMP/${APP_NAME}.app"
fi
codesign --verify --deep --strict "$TMP/${APP_NAME}.app"
ln -s /Applications "$TMP/Applications"

# Sin «LÉEME» dentro del DMG, como Programaciones.

rm -f "$DMG_NAME"
hdiutil create -volname "$APP_NAME $VERSION" -srcfolder "$TMP" -ov -format UDZO "$DMG_NAME"

if [ -n "${APPLE_ID:-}" ] && [ -n "${APPLE_TEAM_ID:-}" ] && [ -n "${APPLE_APP_PASSWORD:-}" ]; then
    xcrun notarytool submit "$DMG_NAME" --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" \
        --password "$APPLE_APP_PASSWORD" --wait
    xcrun stapler staple "$DMG_NAME"
fi
rm -rf "$TMP"
echo "DMG creado: $DMG_NAME ($(du -h "$DMG_NAME" | cut -f1))"
