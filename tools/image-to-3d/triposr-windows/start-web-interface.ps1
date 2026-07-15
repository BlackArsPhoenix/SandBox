<#
.SYNOPSIS
Запускает официальный локальный веб-интерфейс TripoSR.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# region Constants

$OfficialRepositoryName = "TripoSR"
$VirtualEnvironmentName = ".venv"
$CacheDirectoryName = ".cache"
$LocalInterfaceUrl = "http://127.0.0.1:7860"

# endregion

$ProjectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$OfficialRepositoryDirectory = Join-Path (Join-Path $ProjectDirectory "vendor") $OfficialRepositoryName
$VirtualEnvironmentPython = Join-Path $ProjectDirectory "$VirtualEnvironmentName\Scripts\python.exe"
$WebApplicationPath = Join-Path $OfficialRepositoryDirectory "gradio_app.py"
$CacheDirectory = Join-Path $ProjectDirectory $CacheDirectoryName

if (-not (Test-Path $VirtualEnvironmentPython)) {
    throw "Локальное окружение не найдено. Сначала выполните .\setup.ps1."
}

if (-not (Test-Path $WebApplicationPath)) {
    throw "Официальный веб-интерфейс не найден. Сначала выполните .\setup.ps1."
}

$env:HF_HOME = Join-Path $CacheDirectory "huggingface"
$env:TORCH_HOME = Join-Path $CacheDirectory "torch"
$env:PIP_CACHE_DIR = Join-Path $CacheDirectory "pip"

Write-Host "Запуск локального интерфейса: $LocalInterfaceUrl" -ForegroundColor Cyan
Write-Host "Не закрывайте это окно PowerShell во время работы." -ForegroundColor DarkGray

Push-Location $OfficialRepositoryDirectory
try {
    & $VirtualEnvironmentPython "gradio_app.py"
    if ($LASTEXITCODE -ne 0) {
        throw "Веб-интерфейс завершился с кодом $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
