# APOGEE

APOGEE is a C++ missile-defense simulation with a lightweight Python
visualization application. The current scenario contains a blue ground radar,
blue satellite, red missile, and blue interceptor in an Earth-centered inertial
frame.

## Architecture

```text
PySide parameter form
        ↓
ScenarioParams → C++ simulation and preprocessing → Result
                                                  ├─ scene + timeline telemetry
                                                  │          ↓
                                                  │    Rerun Viewer
                                                  └─ analysis products
                                                             ↓
                                                   PySide + Matplotlib
```

The simulation always completes before either viewer is populated. There is no
live simulation protocol, temporary analysis bundle, recording file, or second
analysis process.

C++ owns parameters, calculations, and visualization-neutral results. Python
only adapts a completed `Result`:

- Rerun receives the 3D scene and scalar/vector timeline telemetry.
- The Analysis tab renders curves, time-indexed grids, and metric tables.

Both adapters discover products from their semantic result collections, so a
new calculation using an existing shape needs no viewer-specific wiring. See
[Adding analysis visualizations](docs/analysis-visualizations.md).

## Current features

- Parameter form generated from the C++ schema
- Fixed-step position, velocity, acceleration, and speed histories
- Rerun scene playback and timeline telemetry
- SNR-versus-range curve
- Time-indexed range-Doppler heatmap
- Time-indexed radar state table with singleton PW and PRI values

## Setup

```powershell
conda env create -f environment.yml
conda activate apogee
cmake -S . -B build -DCMAKE_PREFIX_PATH="$env:CONDA_PREFIX"
cmake --build build --config Release
```

To update an existing environment:

```powershell
conda env update -f environment.yml --prune
```

## Run

```powershell
python src/python/main.py
```

The PySide application contains Parameters and Analysis tabs. A completed run
replaces the Analysis workspace and opens a detached Rerun scene/telemetry
viewer. Additional runs can be started without restarting the application.

## Tests

```powershell
cmake --build build --config Release
python -m pytest -q
```

## Source layout

```text
src/cpp/core/             Simulation and result data structures
src/cpp/scenarios/        Scenario defaults
src/cpp/systems/          Timestep calculations
src/cpp/analysis/         Post-run calculations
src/cpp/math/             Reusable numerical functions
src/cpp/run_sim.cpp       Simulation orchestration
src/python/parameter_window.py  Unified PySide application
src/python/analysis/      Analysis normalization and renderers
src/python/visualization/ Rerun scene and telemetry adapter
tests/                    Contract and integration tests
```
