# Publica el frontend de Huellita en el BucketWeb del stack huellita-web e invalida CloudFront.
# No crea ni cambia infraestructura: eso lo hace "sam deploy" (ver DESPLIEGUE.md).
#
# Uso (PowerShell, desde huellita-web):
#   aws configure export-credentials --profile hackaton --format powershell | Out-String | Invoke-Expression
#   .\scripts\publicar_front.ps1
#
# Necesita: AWS CLI v2 con el perfil hackaton (si usa "aws login", entra primero), npm
# (en este equipo esta en c:\dev\hackaton\.worktrees\.herramientas\bin) y el stack ya desplegado.
# Separador de comandos ";" (nunca "&&"): es PowerShell en Windows.

[CmdletBinding()]
param(
    [string]$Stack = "huellita-web",
    [string]$Perfil = "hackaton",
    [string]$Region = "us-east-1",
    [string]$Npm = ""
)

$ErrorActionPreference = "Stop"

# Los comandos nativos (aws, npm) no lanzan excepcion: hay que mirar $LASTEXITCODE.
function Confirmar([string]$mensaje) {
    if ($LASTEXITCODE -ne 0) { throw $mensaje }
}

# 1. Salidas del stack: UrlApp, BucketWeb e IdDistribucion.
Write-Host "1/4 Leyendo las salidas del stack $Stack ..."
$json = aws cloudformation describe-stacks `
    --stack-name $Stack --profile $Perfil --region $Region `
    --query "Stacks[0].Outputs" --output json
Confirmar "No pude leer el stack $Stack con el perfil $Perfil. Desplegalo primero (ver DESPLIEGUE.md)."

$salidas = @{}
foreach ($salida in ($json | ConvertFrom-Json)) { $salidas[$salida.OutputKey] = $salida.OutputValue }

$urlApp = $salidas["UrlApp"]
$urlApi = $salidas["UrlApiDirecta"]
$bucket = $salidas["BucketWeb"]
$distribucion = $salidas["IdDistribucion"]

if (-not $bucket -or -not $distribucion) {
    throw "El stack no trae BucketWeb e IdDistribucion. Si la cuenta no permite crear CloudFront, usa el plan B de DESPLIEGUE.md."
}
Write-Host "    BucketWeb: $bucket"
Write-Host "    IdDistribucion: $distribucion"

# npm no siempre esta en el PATH en este equipo.
if (-not $Npm) {
    $Npm = (Get-Command npm -ErrorAction SilentlyContinue).Source
    if (-not $Npm) { $Npm = "c:\dev\hackaton\.worktrees\.herramientas\bin\npm.cmd" }
}
if (-not (Test-Path $Npm)) {
    throw "No encuentro npm ($Npm). Pasalo con -Npm o agrega c:\dev\hackaton\.worktrees\.herramientas\bin al PATH."
}

# 2. Build del frontend apuntando al BFF (/api, mismo dominio). La navegacion arranca en
#    Inicio: la Agenda ya no existe (el flag VITE_AGENDA quedo obsoleto tras el merge con main).
$raiz = Split-Path -Parent $PSScriptRoot                               # huellita-web
$front = Join-Path (Split-Path -Parent $raiz) "huellita-formato-mejorado"
if (-not (Test-Path (Join-Path $front "package.json"))) { throw "No encuentro el frontend en $front." }

Push-Location $front
try {
    $env:VITE_DATOS = "http"

    Write-Host "2/4 npm ci en $front ..."
    & $Npm ci
    Confirmar "npm ci fallo."

    Write-Host "    npm run build con VITE_DATOS=http ..."
    & $Npm run build
    Confirmar "npm run build fallo."
    if (-not (Test-Path "dist\index.html")) { throw "El build no dejo dist\index.html." }

    # 3. Dos pasadas de sync. Los archivos de assets/ llevan hash en el nombre, asi que se
    #    cachean para siempre; el resto (index.html, sw.js, registerSW.js, manifest.webmanifest)
    #    va con no-cache para que la PWA se actualice. El --delete de cada pasada solo borra
    #    dentro de lo que esa pasada filtra.
    Write-Host "3/4 Subiendo assets/ con cache inmutable ..."
    aws s3 sync dist "s3://$bucket" --delete `
        --exclude "*" --include "assets/*" `
        --cache-control "public,max-age=31536000,immutable" `
        --profile $Perfil --region $Region
    Confirmar "Fallo la subida de assets/."

    Write-Host "    Subiendo el resto del build con no-cache ..."
    aws s3 sync dist "s3://$bucket" --delete `
        --exclude "assets/*" `
        --cache-control "no-cache" `
        --profile $Perfil --region $Region
    Confirmar "Fallo la subida del resto del build."
}
finally {
    Pop-Location
}

# 4. Vaciar la cache de CloudFront para que la version nueva se vea al instante.
Write-Host "4/4 Invalidando la cache de CloudFront ..."
$invalidacion = aws cloudfront create-invalidation `
    --distribution-id $distribucion --paths "/*" `
    --profile $Perfil --region $Region `
    --query "Invalidation.Id" --output text
Confirmar "Fallo la invalidacion de CloudFront."
Write-Host "    Invalidacion $invalidacion en curso (uno o dos minutos)."

Write-Host ""
Write-Host "Listo. Huellita queda en: $urlApp"
if ($urlApi) { Write-Host "API directa (solo para depurar): $urlApi" }
Write-Host "Verificacion con curl y prueba de humo: ver DESPLIEGUE.md"
