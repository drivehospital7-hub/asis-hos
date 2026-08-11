param(
    [string]$DbName = "asis_hos",
    [string]$Output
)

$ErrorActionPreference = "Stop"

# ============================================================
# Rutas
# ============================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile   = Join-Path $ScriptDir "..\.env"
$LogFile   = Join-Path $ScriptDir "backup.log"

if ([string]::IsNullOrWhiteSpace($Output)) {
    $fecha = Get-Date -Format "yyyyMMdd_HHmmss"
    $Output = Join-Path $ScriptDir "backup_${DbName}_$fecha.sql"
}

# ============================================================
# Logging
# ============================================================

function Write-Log {
    param([string]$Message)

    $fecha = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    Add-Content -Path $LogFile -Value "[$fecha] $Message"
}

Clear-Content $LogFile -ErrorAction SilentlyContinue

Write-Log "=========================================="
Write-Log "Inicio del backup"
Write-Log "Script: $($MyInvocation.MyCommand.Path)"
Write-Log "Base de datos: $DbName"

try {

    # ========================================================
    # Validar .env
    # ========================================================

    if (!(Test-Path $EnvFile)) {
        throw "No existe el archivo .env: $EnvFile"
    }

    Write-Log "Leyendo .env"

    Get-Content $EnvFile | ForEach-Object {

        if ($_ -match '^\s*([^#=]+)=(.*)$') {

            $nombre = $matches[1].Trim()
            $valor  = $matches[2].Trim()

            Set-Item "Env:$nombre" $valor
        }

    }

    # ========================================================
    # Configuración PostgreSQL
    # ========================================================

    $PgDump = "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"

    if (!(Test-Path $PgDump)) {
        throw "No existe pg_dump.exe: $PgDump"
    }

    $DbHost = if ($env:DB_HOST) { $env:DB_HOST } else { "localhost" }
    $DbPort = if ($env:DB_PORT) { $env:DB_PORT } else { "5433" }
    $DbUser = if ($env:DB_USER) { $env:DB_USER } else { "postgres" }
    $DbPass = if ($env:DB_PASSWORD) { $env:DB_PASSWORD } else { "" }

    $env:PGPASSWORD = $DbPass

    Write-Log "Host........... $DbHost"
    Write-Log "Puerto......... $DbPort"
    Write-Log "Usuario........ $DbUser"
    Write-Log "Archivo destino $Output"

    # ========================================================
    # Ejecutar pg_dump
    # ========================================================

    & $PgDump `
        -h $DbHost `
        -p $DbPort `
        -U $DbUser `
        -d $DbName `
        --exclude-table-data=evidencias `
        --exclude-table-data=resultados_auditoria `
        --file="$Output"

    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump terminó con código $LASTEXITCODE"
    }

    # ========================================================
    # Validar backup
    # ========================================================

    if (!(Test-Path $Output)) {
        throw "No se creó el archivo de respaldo."
    }

    $TamanoMB = [Math]::Round((Get-Item $Output).Length / 1MB,2)

    Write-Log "Backup generado correctamente."
    Write-Log "Tamaño: $TamanoMB MB"

    exit 0

}
catch {

    Write-Log ""
    Write-Log "********** ERROR **********"
    Write-Log $_.Exception.Message

    if ($_.InvocationInfo) {
        Write-Log "Línea: $($_.InvocationInfo.ScriptLineNumber)"
        Write-Log "Comando: $($_.InvocationInfo.Line.Trim())"
    }

    exit 1

}
finally {

    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue

    Write-Log "Fin del proceso."
}