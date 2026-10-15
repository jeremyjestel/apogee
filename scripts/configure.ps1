param(
    [string] $VcpkgRoot = $env:VCPKG_ROOT,
    [switch] $Fresh
)

$ErrorActionPreference = "Stop"

if (-not $env:CONDA_PREFIX) {
    throw "CONDA_PREFIX is not set. Activate the apogee conda environment first."
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$cmakeArguments = @(
    "-S", $projectRoot,
    "-B", (Join-Path $projectRoot "build"),
    "-DCMAKE_PREFIX_PATH=$env:CONDA_PREFIX",
    "-DPython_EXECUTABLE=$(Join-Path $env:CONDA_PREFIX 'python.exe')"
)

# Conda supplies Eigen and pybind11; retain support for an existing vcpkg setup.
if (-not $VcpkgRoot -and (Test-Path -LiteralPath "C:\vcpkg\scripts\buildsystems\vcpkg.cmake")) {
    $VcpkgRoot = "C:\vcpkg"
}
if ($VcpkgRoot) {
    $toolchainFile = Join-Path $VcpkgRoot "scripts\buildsystems\vcpkg.cmake"
    if (-not (Test-Path -LiteralPath $toolchainFile)) {
        throw "vcpkg toolchain not found at $toolchainFile"
    }
    $cmakeArguments += "-DCMAKE_TOOLCHAIN_FILE=$toolchainFile"
}
if ($Fresh) {
    # Clear cached dependency paths only when explicitly requested.
    $cmakeArguments += "--fresh"
}

cmake @cmakeArguments
if ($LASTEXITCODE -ne 0) {
    throw "CMake configuration failed with exit code $LASTEXITCODE."
}
