# Compilación en Windows: exe (PyInstaller) e instalador (Inno Setup). Copia de la de Programaciones.
#
# IMPORTANTE: este fichero se guarda en UTF-8 CON marca de orden de bytes (BOM):
# Windows PowerShell 5.1 lee sin BOM como ANSI y rompe los acentos.
#
# Solo la ejecuta la CI (compilar.yml): no se compila en local.

param(
    [switch]$SkipInstaller = $false
)

$Raiz = $PSScriptRoot | Split-Path -Parent
Set-Location $Raiz
$Version = (Select-String -Path "pyproject.toml" -Pattern '^version = "([^"]+)"').Matches[0].Groups[1].Value
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) { Write-Host "[ERROR] No se encuentra Python"; exit 1 }
Write-Host "[INFO] PCCF $Version con $Python"

& $Python -m pip install --upgrade pip setuptools | Out-Null
& $Python -m pip install -r requirements.txt pyinstaller==6.22.3
if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] Fallo al instalar dependencias"; exit 1 }

# El catálogo publicado y firmado que va dentro de la app.
if (-not (Test-Path "catalogo")) {
    & $Python scripts/catalogo.py bajar
    if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] No se ha podido bajar el catálogo publicado"; exit 1 }
}

Remove-Item -Recurse -Force build, "dist\PCCF", Output -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path Output | Out-Null

# Siempre desde el spec del repositorio, el mismo que macOS.
& $Python -m PyInstaller --noconfirm --clean PCCF.spec
$Exe = "dist\PCCF\PCCF.exe"
if (-not (Test-Path $Exe)) { Write-Host "[ERROR] PyInstaller no generó $Exe"; exit 1 }
Write-Host "[OK] Ejecutable: $Exe"
if ($SkipInstaller) { exit 0 }

$Inno = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $Inno)) {
    $Inno = Get-ChildItem -Path "C:\Program Files*" -Recurse -Filter "ISCC.exe" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $Inno) { Write-Host "[ERROR] Inno Setup no encontrado"; exit 1 }
& $Inno "/DMyAppVersion=$Version" installer_windows.iss
if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] Inno Setup falló"; exit 1 }
Write-Host "[OK] Instalador: Output\PCCF-$Version-Windows-Setup.exe"
