# Prueba de humo del exe congelado (copia de la de Programaciones): arranca con
# PCCF_PRUEBA_DE_ARRANQUE, espera a que salga y busca en su registro las marcas de la
# ventana principal, de los datos empaquetados (catalogo, esquemas, plantilla) y de QtPdf.
# Que el exe exista no basta: tiene que arrancar y encontrar lo que lleva dentro.
# Solo ASCII a proposito: asi da igual con que PowerShell se abra.
#
# Uso: pwsh scripts/prueba_arranque_windows.ps1 -Exe dist/PCCF/PCCF.exe

param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [int]$Segundos = 180
)

$ErrorActionPreference = "Stop"
$Logs = Join-Path $env:APPDATA "PCCF\logs"
$Marcas = @(
    "PRUEBA DE ARRANQUE: datos empaquetados",
    "PRUEBA DE ARRANQUE: QtPdf",
    "PRUEBA DE ARRANQUE: ventana principal a la vista"
)
if (-not (Test-Path $Exe)) { Write-Host "[ERROR] No existe $Exe"; exit 1 }
$Exe = (Resolve-Path $Exe).Path

$env:PCCF_PRUEBA_DE_ARRANQUE = "ventana"
$proceso = Start-Process -FilePath $Exe -WorkingDirectory (Split-Path $Exe) -PassThru
$termino = $proceso.WaitForExit($Segundos * 1000)
Remove-Item Env:PCCF_PRUEBA_DE_ARRANQUE -ErrorAction SilentlyContinue
if (-not $termino) {
    Write-Host "[ERROR] Sigue abierto tras $Segundos s: se da por colgado"
    Stop-Process -Id $proceso.Id -Force -ErrorAction SilentlyContinue
}

$registro = $null
if (Test-Path $Logs) {
    $registro = Get-ChildItem $Logs -Filter "app_*.log" | Sort-Object LastWriteTime | Select-Object -Last 1
}
$faltan = @()
if ($null -eq $registro) {
    Write-Host "[ERROR] No hay registro: el proceso no llego a ejecutar Python"
    $faltan = $Marcas
} else {
    Write-Host "=== $($registro.Name) (ultimas 80 lineas) ==="
    Get-Content $registro.FullName -Encoding UTF8 | Select-Object -Last 80 | ForEach-Object { Write-Host $_ }
    foreach ($m in $Marcas) {
        if (-not (Select-String -Path $registro.FullName -SimpleMatch $m -Quiet)) { $faltan += $m }
    }
}
$falta = Join-Path $Logs "faulthandler.log"
if ((Test-Path $falta) -and ((Get-Item $falta).Length -gt 0)) {
    Write-Host "=== faulthandler.log ==="
    Get-Content $falta | Select-Object -Last 60 | ForEach-Object { Write-Host $_ }
}
if ($faltan.Count -eq 0 -and $termino -and $proceso.ExitCode -eq 0) {
    Write-Host "[OK] Ventana, datos empaquetados y QtPdf; salida limpia"
    exit 0
}
foreach ($m in $faltan) { Write-Host "[ERROR] Falta en el registro: $m" }
Write-Host "[ERROR] El exe no ha pasado la prueba de arranque (termino=$termino, codigo=$($proceso.ExitCode))"
exit 1
