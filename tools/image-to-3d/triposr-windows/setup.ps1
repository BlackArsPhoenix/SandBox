<#
.SYNOPSIS
Устанавливает локальный TripoSR и зависимости для Windows 10.

.PARAMETER TorchChannel
Канал сборки PyTorch: CUDA 12.8, CUDA 12.6 или процессор.

.PARAMETER PythonVersion
Версия Python, доступная через стандартный Windows launcher.

.PARAMETER UpdateSource
Обновляет уже скачанный официальный исходный код без удаления локальных файлов.
#>

[CmdletBinding()]
param(
    [ValidateSet("cu128", "cu126", "cpu")]
    [string]$TorchChannel = "cu128",

    [ValidateSet("3.10", "3.11")]
    [string]$PythonVersion = "3.11",

    [switch]$UpdateSource
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# region Constants

$OfficialRepositoryUrl = "https://github.com/VAST-AI-Research/TripoSR.git"
$OfficialRepositoryName = "TripoSR"
$VirtualEnvironmentName = ".venv"
$CacheDirectoryName = ".cache"
$RequiredPythonMajorMinor = $PythonVersion
$TorchIndexByChannel = @{
    "cu128" = "https://download.pytorch.org/whl/cu128"
    "cu126" = "https://download.pytorch.org/whl/cu126"
    "cpu"   = "https://download.pytorch.org/whl/cpu"
}

# endregion

$ProjectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$VendorDirectory = Join-Path $ProjectDirectory "vendor"
$OfficialRepositoryDirectory = Join-Path $VendorDirectory $OfficialRepositoryName
$VirtualEnvironmentDirectory = Join-Path $ProjectDirectory $VirtualEnvironmentName
$VirtualEnvironmentPython = Join-Path $VirtualEnvironmentDirectory "Scripts\python.exe"
$CacheDirectory = Join-Path $ProjectDirectory $CacheDirectoryName
$TorchIndexUrl = $TorchIndexByChannel[$TorchChannel]

function Assert-CommandAvailable {
    <#
    .SYNOPSIS
    Проверяет наличие программы в системном пути.

    .PARAMETER CommandName
    Имя проверяемой программы.

    .PARAMETER InstallationHint
    Подсказка по установке отсутствующей программы.
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$CommandName,

        [Parameter(Mandatory = $true)]
        [string]$InstallationHint
    )

    if ($null -eq (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "Не найдена программа '$CommandName'. $InstallationHint"
    }
}

function Assert-NativeCommandSucceeded {
    <#
    .SYNOPSIS
    Останавливает установку после ошибки внешней программы.

    .PARAMETER FailureMessage
    Сообщение с описанием неудавшегося действия.
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    if ($LASTEXITCODE -ne 0) {
        throw "$FailureMessage Код завершения: $LASTEXITCODE."
    }
}

if ($env:OS -ne "Windows_NT") {
    throw "Этот установщик предназначен для Windows 10 или Windows 11."
}

Assert-CommandAvailable `
    -CommandName "git" `
    -InstallationHint "Установите Git for Windows: https://git-scm.com/download/win"
Assert-CommandAvailable `
    -CommandName "py" `
    -InstallationHint "Установите 64-битный Python $RequiredPythonMajorMinor: https://www.python.org/downloads/windows/"

if ($TorchChannel -ne "cpu") {
    Assert-CommandAvailable `
        -CommandName "nvidia-smi" `
        -InstallationHint "Установите актуальный драйвер NVIDIA: https://www.nvidia.com/Download/index.aspx"
    Write-Host "Найдена видеокарта NVIDIA:" -ForegroundColor Cyan
    & nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    Assert-NativeCommandSucceeded -FailureMessage "Не удалось прочитать сведения о видеокарте."
}

& py "-$RequiredPythonMajorMinor" -c "import sys; print(sys.version)"
Assert-NativeCommandSucceeded `
    -FailureMessage "Python $RequiredPythonMajorMinor не найден через Windows launcher."

New-Item -ItemType Directory -Force -Path $VendorDirectory | Out-Null
New-Item -ItemType Directory -Force -Path $CacheDirectory | Out-Null

if (-not (Test-Path $OfficialRepositoryDirectory)) {
    Write-Host "Скачивание официального TripoSR..." -ForegroundColor Cyan
    & git clone --depth 1 $OfficialRepositoryUrl $OfficialRepositoryDirectory
    Assert-NativeCommandSucceeded -FailureMessage "Не удалось скачать официальный TripoSR."
}
elseif ($UpdateSource) {
    Write-Host "Обновление официального TripoSR..." -ForegroundColor Cyan
    & git -C $OfficialRepositoryDirectory pull --ff-only
    Assert-NativeCommandSucceeded -FailureMessage "Не удалось обновить официальный TripoSR."
}
else {
    Write-Host "Официальный TripoSR уже скачан; обновление пропущено." -ForegroundColor DarkGray
}

if (-not (Test-Path $VirtualEnvironmentPython)) {
    Write-Host "Создание изолированного Python-окружения..." -ForegroundColor Cyan
    & py "-$RequiredPythonMajorMinor" -m venv $VirtualEnvironmentDirectory
    Assert-NativeCommandSucceeded -FailureMessage "Не удалось создать Python-окружение."
}

$env:HF_HOME = Join-Path $CacheDirectory "huggingface"
$env:TORCH_HOME = Join-Path $CacheDirectory "torch"
$env:PIP_CACHE_DIR = Join-Path $CacheDirectory "pip"

Write-Host "Обновление инструментов установки Python..." -ForegroundColor Cyan
& $VirtualEnvironmentPython -m pip install --upgrade pip setuptools wheel
Assert-NativeCommandSucceeded -FailureMessage "Не удалось обновить инструменты установки Python."

Write-Host "Установка PyTorch из канала '$TorchChannel'..." -ForegroundColor Cyan
& $VirtualEnvironmentPython -m pip install --upgrade torch torchvision --index-url $TorchIndexUrl
Assert-NativeCommandSucceeded -FailureMessage "Не удалось установить PyTorch."

$OfficialRequirementsPath = Join-Path $OfficialRepositoryDirectory "requirements.txt"
Write-Host "Установка официальных зависимостей TripoSR..." -ForegroundColor Cyan
& $VirtualEnvironmentPython -m pip install -r $OfficialRequirementsPath
Assert-NativeCommandSucceeded -FailureMessage "Не удалось установить зависимости TripoSR."

Write-Host "Установка инструментов проверки и экспорта STL..." -ForegroundColor Cyan
& $VirtualEnvironmentPython -m pip install --upgrade trimesh scikit-image manifold3d
Assert-NativeCommandSucceeded -FailureMessage "Не удалось установить инструменты экспорта STL."

& $VirtualEnvironmentPython -m pip check
Assert-NativeCommandSucceeded -FailureMessage "Обнаружены несовместимые Python-зависимости."

$GpuRequiredLiteral = if ($TorchChannel -eq "cpu") { "False" } else { "True" }
$ValidationCode = @"
import torch

gpu_required = $GpuRequiredLiteral
gpu_available = torch.cuda.is_available()
print(f"PyTorch: {torch.__version__}")
print(f"CUDA доступна: {gpu_available}")
if gpu_available:
    print(f"Видеокарта: {torch.cuda.get_device_name(0)}")
if gpu_required and not gpu_available:
    raise SystemExit("PyTorch установлен, но CUDA недоступна.")
"@

& $VirtualEnvironmentPython -c $ValidationCode
Assert-NativeCommandSucceeded -FailureMessage "Проверка PyTorch завершилась ошибкой."

Write-Host ""
Write-Host "Установка завершена." -ForegroundColor Green
Write-Host "Следующий шаг:"
Write-Host '.\generate.ps1 -ImagePath "C:\путь\к\изображению.png" -ExportStl -TargetHeightMillimeters 64'
