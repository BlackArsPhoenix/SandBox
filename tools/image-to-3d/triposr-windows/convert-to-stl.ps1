<#
.SYNOPSIS
Преобразует OBJ или GLB в масштабированный STL и проверяет сетку.

.PARAMETER InputMeshPath
Путь к исходной модели.

.PARAMETER OutputStlPath
Путь для итогового STL.

.PARAMETER TargetHeightMillimeters
Требуемая высота STL; ноль сохраняет исходные координаты.

.PARAMETER VoxelPitchMillimeters
Размер вокселя для создания замкнутой сетки; ноль отключает перестроение.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InputMeshPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputStlPath,

    [ValidateRange(0.0, 10000.0)]
    [double]$TargetHeightMillimeters = 0.0,

    [ValidateRange(0.0, 10.0)]
    [double]$VoxelPitchMillimeters = 0.0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# region Constants

$VirtualEnvironmentName = ".venv"
$ConverterRelativePath = "scripts\convert_mesh_to_stl.py"

# endregion

$ProjectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$VirtualEnvironmentPython = Join-Path $ProjectDirectory "$VirtualEnvironmentName\Scripts\python.exe"
$ConverterPath = Join-Path $ProjectDirectory $ConverterRelativePath

if (-not (Test-Path $VirtualEnvironmentPython)) {
    throw "Локальное окружение не найдено. Сначала выполните .\setup.ps1."
}

$ResolvedInputMeshPath = (Resolve-Path -LiteralPath $InputMeshPath).Path
if ([System.IO.Path]::IsPathRooted($OutputStlPath)) {
    $AbsoluteOutputStlPath = $OutputStlPath
}
else {
    $AbsoluteOutputStlPath = Join-Path $ProjectDirectory $OutputStlPath
}

$OutputParentDirectory = Split-Path -Parent $AbsoluteOutputStlPath
New-Item -ItemType Directory -Force -Path $OutputParentDirectory | Out-Null

$InvariantCulture = [System.Globalization.CultureInfo]::InvariantCulture
$ConverterArguments = @(
    $ConverterPath,
    "--input",
    $ResolvedInputMeshPath,
    "--output",
    $AbsoluteOutputStlPath,
    "--target-height-millimeters",
    $TargetHeightMillimeters.ToString($InvariantCulture),
    "--voxel-pitch-millimeters",
    $VoxelPitchMillimeters.ToString($InvariantCulture)
)

& $VirtualEnvironmentPython @ConverterArguments
if ($LASTEXITCODE -ne 0) {
    throw "Преобразование модели завершилось с кодом $LASTEXITCODE."
}
