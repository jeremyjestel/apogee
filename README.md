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
Generic parameter and component structs
    +
Default scenario entity definitions
    ↓
ScenarioParams → runtime entities → systems and analyses
    ↓
Result → scalar, vector, and grid data
    ↓
Python visualization adapter
    ↓
Rerun Viewer
```

The headers `src/cpp/params.hpp` and those under `src/cpp/core/` define
reusable, entity-agnostic data shapes such as `SimulationParams`, `RadarParams`,
and `EntityDefinition`. The files under `src/cpp/scenarios/default/` contain the
actual values for the blue radar, blue satellite, red missile, and blue
interceptor, then assemble them into one `ScenarioParams` object.

`run_sim.cpp` converts each definition into a runtime `Entity`. Every entity has
a `KinematicState` and a scalar radar signature; only the blue radar definition
contains a `RadarParams` component. Systems update the runtime state, while
analyses add separate result series. The fixed scenario does not need a
registry or `World` abstraction.

Each run creates a fresh `RadarModule`, recalculates its derived parameter
values, and stores the resulting `RadarParams` snapshot as `const`. Systems can
therefore use ordinary fields such as `pulse_width_s` without changing
parameters during the run.

Parameter display names, units, and member metadata stay beside their generic
C++ structs. Python requests `parameter_specs()` to build the form and uses
`get_parameter()` and `set_parameter()` with paths such as
`blue_radar.radar.frequency_hz`. This keeps Python independent of the nested
C++ storage and makes the C++ scenario the single source of default values.

To add another value to an existing component, add the member and its
`parameter(...)` metadata to the generic parameter struct, then set the desired
instance value in the relevant scenario entity file. The parameter window picks
up the field automatically for each entity that owns that component.

## Setup

```powershell
conda env create -f environment.yml
conda activate apogee
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE="$PWD/vcpkg/scripts/buildsystems/vcpkg.cmake"
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
src/cpp/scenarios/default/ Four fixed entity definitions and scenario assembly
src/cpp/systems/           Timestep-based simulation systems
src/cpp/analysis/          Non-timestep analyses
src/cpp/math/              Small reusable math helpers
src/cpp/params.hpp         Generic parameter structs and field metadata
src/cpp/run_sim.cpp        Scenario instantiation and simulation orchestration
src/python/                Parameter UI and build loader
src/python/visualization/  Rerun conversion and layout
tests/                     End-to-end feature tests
```
