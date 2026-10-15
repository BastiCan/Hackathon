<#
.SYNOPSIS
  Arma el zip de la Lambda postits-ocr con wheels de Linux desde Windows, sin Docker.

.DESCRIPTION
  1. pip install -r requirements.txt en <Destino>\package con wheels cp312 manylinux x86_64.
  2. Copia el codigo de la Lambda (ocr, captura, almacen, nomina, leer, detectar, recortar) y
     ..\integra-backend\src\core\capturas.py como capturas_equipo.py (validador del equipo).
  3. Comprueba que estan capturas_equipo.py y python_ulid-4.0.1.dist-info, y que no van
     rapidfuzz, pydantic, tests, .env, json ni imagenes en la raiz.
  4. Comprime con zipfile de Python (rutas con "/" y permisos 0644) en postits_ocr_lambda.zip.
  5. Falla si el contenido descomprimido llega a 250 MiB.

  No despliega nada ni usa credenciales. Handler: ocr.handler (python3.12, x86_64).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File postits-ocr\empaquetar_zip.ps1 `
      -Python C:\ruta\.venv\Scripts\python.exe -Destino C:\ruta\Hackaton\tmp\postits-ocr-dist
#>
param(
    [Parameter(Mandatory = $true)][string]$Python,
    [Parameter(Mandatory = $true)][string]$Destino,
    [switch]$Limpiar
)

$ErrorActionPreference = "Stop"
$Destino = [System.IO.Path]::GetFullPath($Destino)
$permitidos = @(
    ([System.IO.Path]::GetFullPath("c:\Users\crist\OneDrive\Escritorio\Hackaton\tmp") + "\"),
    ([System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "dist")) + "\")
)
$dentro = $false
foreach ($base in $permitidos) {
    if (($Destino + "\").StartsWith([string]$base, [System.StringComparison]::OrdinalIgnoreCase)) { $dentro = $true }
}
if (-not $dentro) { throw "Destino fuera de las carpetas permitidas: $Destino" }
$paquete = Join-Path $Destino "package"
$zip = Join-Path $Destino "postits_ocr_lambda.zip"
$codigo = @("ocr.py", "captura.py", "almacen.py", "nomina.py", "leer.py", "detectar.py", "recortar.py")
$equipo = Join-Path $PSScriptRoot "..\integra-backend\src\core\capturas.py"

foreach ($archivo in $codigo) {
    if (-not (Test-Path (Join-Path $PSScriptRoot $archivo))) { throw "Falta $archivo en $PSScriptRoot" }
}
if (-not (Test-Path $equipo)) { throw "Falta $equipo" }
if (Test-Path $paquete) { Remove-Item -Recurse -Force $paquete }
if (Test-Path $zip) { Remove-Item -Force $zip }
New-Item -ItemType Directory -Force -Path $paquete | Out-Null

& $Python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt") --target $paquete `
    --implementation cp --python-version 3.12 --only-binary=:all: `
    --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 `
    --disable-pip-version-check --no-compile --no-cache-dir --quiet
if ($LASTEXITCODE -ne 0) { throw "pip install termino con codigo $LASTEXITCODE" }

foreach ($archivo in $codigo) { Copy-Item (Join-Path $PSScriptRoot $archivo) $paquete }
Copy-Item $equipo (Join-Path $paquete "capturas_equipo.py")
Write-Host ("capturas_equipo.py SHA-256: {0}" -f (Get-FileHash (Join-Path $paquete "capturas_equipo.py")).Hash)

if (-not (Test-Path (Join-Path $paquete "python_ulid-4.0.1.dist-info\METADATA"))) { throw "Falta python_ulid-4.0.1.dist-info" }
if (Get-ChildItem $paquete -Directory | Where-Object { $_.Name -like "rapidfuzz*" -or $_.Name -like "pydantic*" }) {
    throw "El paquete no debe llevar rapidfuzz ni pydantic"
}
$prohibidos = Get-ChildItem $paquete -File | Where-Object { $_.Name -eq ".env" -or $_.Extension -in @(".json", ".jpg", ".jpeg", ".png", ".heic") }
if ($prohibidos -or (Test-Path (Join-Path $paquete "tests"))) { throw "La raiz del paquete tiene archivos prohibidos" }

$comprimir = @'
import os, sys, zipfile
origen, destino = sys.argv[1], sys.argv[2]
total = 0
with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for raiz, carpetas, archivos in os.walk(origen):
        carpetas.sort()
        for nombre in sorted(archivos):
            ruta = os.path.join(raiz, nombre)
            relativa = os.path.relpath(ruta, origen).replace(os.sep, "/")
            info = zipfile.ZipInfo.from_file(ruta, relativa)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(ruta, "rb") as f:
                datos = f.read()
            total += len(datos)
            z.writestr(info, datos)
print(total)
'@
$script = Join-Path $Destino "_comprimir.py"
Set-Content -Path $script -Value $comprimir -Encoding ASCII
$descomprimido = [int64](& $Python $script $paquete $zip)
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el zip" }
Remove-Item $script

$mibZip = (Get-Item $zip).Length / 1048576
$mibTotal = $descomprimido / 1048576
Write-Host ("Zip: {0} ({1:N1} MiB comprimido, {2:N1} MiB descomprimido)" -f $zip, $mibZip, $mibTotal)
Write-Host ("SHA-256 zip: {0}" -f (Get-FileHash $zip).Hash)
if ($descomprimido -ge 262144000) { throw "Se pasa del limite de 250 MiB descomprimido" }
if ($mibTotal -ge 240) { Write-Host "AVISO: mas de 240 MiB descomprimido" }

if ($Limpiar) {
    Remove-Item -Recurse -Force $paquete
    Write-Host "package borrado (-Limpiar)."
}
