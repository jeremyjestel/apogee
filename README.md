# APOGEE

APOGEE is a fixed-scenario missile-defense simulation with four entities:

- Blue ground radar
- Blue satellite
- Red missile
- Blue interceptor

The simulation uses a global Earth-centered inertial (ECI) Cartesian frame and
a fixed timestep. C++ owns parameters, simulation state, systems, analyses, and
result generation. Python provides the parameter window and sends completed
results to Rerun.

## Current features

- Editable parameters generated from the C++ parameter schema
- Position, velocity, acceleration, and speed histories for all four entities
- Simple fixed-step kinematic motion
- Radar SNR-versus-range analysis
- Rerun scenario, telemetry, continuous-analysis, 3D-analysis, and grid views
- Range-Doppler processing under active development

## Architecture

```text
params.hpp
    ↓
run_sim.cpp → entities, components, and systems
    ↓
Result → scalar, vector, and grid data
    ↓
Python visualization adapter
    ↓
Rerun Viewer
```

The four entities are created explicitly in `run_sim.cpp`. Every entity owns a
`KinematicState`; the blue radar additionally owns a `RadarModule`. There is no
dynamic entity registry or `World` abstraction.

`src/cpp/params.hpp` is the source of truth for parameter types, defaults,
display names, units, Python bindings, and parameter-window fields.

## Setup

```powershell
conda env create -f environment.yml
conda activate apogee
cmake -S . -B build
cmake --build build --config Release
```

After changing C++ code, rebuild before running Python.

## Run

```powershell
python src/python/main.py
```

The parameter window hides while the Rerun Viewer is open and returns when the
viewer closes.

## Debug build

```powershell
$env:APOGEE_BUILD_CONFIG = "Debug"
cmake --build build --config Debug
python src/python/main.py
```

Clear the environment variable or set it to `Release` to use the Release build.

## Tests

```powershell
cmake --build build --config Release
python -m pytest -q
```

## Source layout

```text
src/cpp/core/              Shared data structures
src/cpp/systems/           Timestep-based simulation systems
src/cpp/analysis/          Non-timestep analyses
src/cpp/params.hpp         Parameter schema and defaults
src/cpp/run_sim.cpp        Fixed scenario orchestration
src/python/                Parameter UI and build loader
src/python/visualization/  Rerun conversion and layout
tests/                     End-to-end feature tests
dev_notes/                 Short, non-authoritative development notes
```
