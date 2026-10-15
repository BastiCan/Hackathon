# Carga las variables de integra-backend/.env en la sesion ACTUAL de PowerShell,
# para que aws y sam las usen. No imprime valores: solo los nombres cargados.
#
# Uso (con el punto inicial, para que afecte la sesion actual):
#   . .\scripts\cargar_env.ps1

$ErrorActionPreference = "Stop"

# .env esta en la raiz del proyecto (un nivel sobre scripts/).
$raiz = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $raiz ".env"

if (-not (Test-Path $envFile)) {
    Write-Host "No se encontro $envFile. Copia .env.example a .env y rellenalo."
    return
}

$cargadas = @()

foreach ($linea in Get-Content $envFile) {
    $texto = $linea.Trim()
    # Saltar vacias y comentarios.
    if ($texto -eq "" -or $texto.StartsWith("#")) { continue }

    $idx = $texto.IndexOf("=")
    if ($idx -lt 1) { continue }

    $nombre = $texto.Substring(0, $idx).Trim()
    $valor = $texto.Substring($idx + 1).Trim()

    # Quitar comillas envolventes si las hubiera.
    if ($valor.Length -ge 2 -and
        (($valor.StartsWith('"') -and $valor.EndsWith('"')) -or
         ($valor.StartsWith("'") -and $valor.EndsWith("'")))) {
        $valor = $valor.Substring(1, $valor.Length - 2)
    }

    # Saltar claves sin valor (p. ej. las que aun no rellenas).
    if ($valor -eq "") { continue }

    Set-Item -Path "Env:$nombre" -Value $valor
    $cargadas += $nombre
}

if ($cargadas.Count -gt 0) {
    Write-Host "Variables cargadas:" ($cargadas -join ", ")
} else {
    Write-Host "No se cargo ninguna variable (revisa que .env tenga valores)."
}
