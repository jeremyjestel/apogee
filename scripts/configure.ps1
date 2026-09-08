$ErrorActionPreference = "Stop"

$vcpkgRoot = "C:\vcpkg"
$toolchainFile = Join-Path $vcpkgRoot "scripts\buildsystems\vcpkg.cmake"

if (-not (Test-Path -LiteralPath $toolchainFile)) {
    throw "vcpkg toolchain not found at $toolchainFile"
}

if (-not $env:CONDA_PREFIX) {
    throw "CONDA_PREFIX is not set. Activate the apogee conda environment first."
}

# --fresh clears cached paths, including a vcpkg installation that has moved.
cmake --fresh -S . -B build `
    "-DCMAKE_PREFIX_PATH=$env:CONDA_PREFIX" `
    "-DCMAKE_TOOLCHAIN_FILE=$toolchainFile"
