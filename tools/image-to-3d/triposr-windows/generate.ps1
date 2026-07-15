<#
.SYNOPSIS
Создаёт локальную 3D-модель из одного изображения через TripoSR.

.PARAMETER ImagePath
Путь к исходному PNG, JPEG или WEBP.

.PARAMETER OutputDirectory
Каталог для изображения, модели и дополнительных материалов.

.PARAMETER ModelSaveFormat
Формат исходной модели TripoSR.

.PARAMETER MarchingCubesResolution
Разрешение извлечения поверхности; большее значение повышает детализацию и расход памяти.

.PARAMETER ForegroundRatio
Доля кадра, занимаемая объектом после удаления фона.

.PARAMETER BakeTexture
Создаёт отдельную текстуру вместо вершинных цветов.

.PARAMETER TextureResolution
Разрешение создаваемой текстуры.

.PARAMETER KeepBackground
Отключает автоматическое удаление фона.

.PARAMETER ExportStl
Дополнительно создаёт STL для печати.

.PARAMETER TargetHeightMillimeters
Масштабирует STL до указанной высоты; ноль сохраняет исходный размер.

.PARAMETER VoxelPitchMillimeters
Перестраивает STL в замкнутую воксельную сетку; ноль отключает перестроение.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ImagePath,

    [string]$OutputDirectory = ".\outputs\latest",

    [ValidateSet("obj", "glb")]
    [string]$ModelSaveFormat = "obj",

    [ValidateRange(128, 512)]
    [int]$MarchingCubesResolution = 256,

    [ValidateRange(0.5, 1.0)]
    [double]$ForegroundRatio = 0.85,

    [switch]$BakeTexture,

    [ValidateSet(1024, 2048, 4096)]
    [int]$TextureResolution = 2048,

    [switch]$KeepBackground,

    [switch]$ExportStl,

    [ValidateRange(0.0, 10000.0)]
    [double]$TargetHeightMillimeters = 0.0,

    [ValidateRange(0.0, 10.0)]
    [double]$VoxelPitchMillimeters = 0.0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# region Constants

$OfficialRepositoryName = "TripoSR"
$VirtualEnvironmentName = ".venv"
$CacheDirectoryName = ".cache"
$ResultIndexDirectoryName = "0"
$ResultBaseName = "mesh"

# endregion

$ProjectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$OfficialRepositoryDirectory = Join-Path (Join-Path $ProjectDirectory "vendor") $OfficialRepositoryName
$VirtualEnvironmentPython = Join-Path $ProjectDirectory "$VirtualEnvironmentName\Scripts\python.exe"
$GeneratorPath = Join-Path $OfficialRepositoryDirectory "run.py"
$ConverterScriptPath = Join-Path $ProjectDirectory "convert-to-stl.ps1"
$CacheDirectory = Join-Path $ProjectDirectory $CacheDirectoryName

if (-not (Test-Path $VirtualEnvironmentPython)) {
    throw "Локальное окружение не найдено. Сначала выполните .\setup.ps1."
}

if (-not (Test-Path $GeneratorPath)) {
    throw "Официальный TripoSR не найден. Сначала выполните .\setup.ps1."
}

$ResolvedImagePath = (Resolve-Path -LiteralPath $ImagePath).Path
if ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
    $AbsoluteOutputDirectory = $OutputDirectory
}
else {
    $AbsoluteOutputDirectory = Join-Path $ProjectDirectory $OutputDirectory
}

New-Item -ItemType Directory -Force -Path $AbsoluteOutputDirectory | Out-Null
$AbsoluteOutputDirectory = (Resolve-Path -LiteralPath $AbsoluteOutputDirectory).Path

$env:HF_HOME = Join-Path $CacheDirectory "huggingface"
$env:TORCH_HOME = Join-Path $CacheDirectory "torch"
$env:PIP_CACHE_DIR = Join-Path $CacheDirectory "pip"

$InvariantCulture = [System.Globalization.CultureInfo]::InvariantCulture
$GeneratorArguments = @(
    "run.py",
    $ResolvedImagePath,
    "--output-dir",
    $AbsoluteOutputDirectory,
    "--model-save-format",
    $ModelSaveFormat,
    "--mc-resolution",
    $MarchingCubesResolution.ToString($InvariantCulture),
    "--foreground-ratio",
    $ForegroundRatio.ToString($InvariantCulture)
)

if ($BakeTexture) {
    $GeneratorArguments += @(
        "--bake-texture",
        "--texture-resolution",
        $TextureResolution.ToString($InvariantCulture)
    )
}

if ($KeepBackground) {
    $GeneratorArguments += "--no-remove-bg"
}

Write-Host "Запуск TripoSR..." -ForegroundColor Cyan
Write-Host "Первый запуск дополнительно скачивает открытые веса модели." -ForegroundColor DarkGray

Push-Location $OfficialRepositoryDirectory
try {
    & $VirtualEnvironmentPython @GeneratorArguments
    if ($LASTEXITCODE -ne 0) {
        throw "TripoSR завершился с кодом $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

$GeneratedMeshPath = Join-Path `
    (Join-Path $AbsoluteOutputDirectory $ResultIndexDirectoryName) `
    "$ResultBaseName.$ModelSaveFormat"

if (-not (Test-Path $GeneratedMeshPath)) {
    throw "TripoSR завершился без ожидаемого файла: $GeneratedMeshPath"
}

Write-Host "Исходная 3D-модель: $GeneratedMeshPath" -ForegroundColor Green

if ($ExportStl) {
    $StlOutputPath = Join-Path `
        (Join-Path $AbsoluteOutputDirectory $ResultIndexDirectoryName) `
        "$ResultBaseName.stl"

    $ConverterArguments = @{
        InputMeshPath          = $GeneratedMeshPath
        OutputStlPath          = $StlOutputPath
        TargetHeightMillimeters = $TargetHeightMillimeters
        VoxelPitchMillimeters   = $VoxelPitchMillimeters
    }
    & $ConverterScriptPath @ConverterArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Экспорт STL завершился с кодом $LASTEXITCODE."
    }
}
