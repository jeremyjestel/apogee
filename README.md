# APOGEE

APOGEE: Multi-Domain Simulation Framework

### Root

- [CMakeLists.txt](C:/Users/jerem/OneDrive/Documents/apogee/CMakeLists.txt) configures the C++20 `apogee` Python extension and lists the C++ files compiled into it.
- [environment.yml](C:/Users/jerem/OneDrive/Documents/apogee/environment.yml) defines the Conda environment and required Python, C++, testing, and visualization dependencies.
- [README.md](C:/Users/jerem/OneDrive/Documents/apogee/README.md) provides the project’s public introduction, although it is currently incomplete.
- [.gitignore](C:/Users/jerem/OneDrive/Documents/apogee/.gitignore) prevents build products, recordings, IDE settings, and Python caches from being committed.

### C++ simulation

- [params.hpp](C:/Users/jerem/OneDrive/Documents/apogee/src/cpp/params.hpp) defines all simulation, radar, satellite, missile, and interceptor input parameters and their default initial states.
- [run_sim.hpp](C:/Users/jerem/OneDrive/Documents/apogee/src/cpp/run_sim.hpp) declares the main C++ simulation function.
- [run_sim.cpp](C:/Users/jerem/OneDrive/Documents/apogee/src/cpp/run_sim.cpp) creates the entities, runs the timestep loop, invokes systems and analyses, and returns the completed `Result`.
- [bindings.cpp](C:/Users/jerem/OneDrive/Documents/apogee/src/cpp/bindings.cpp) exposes the C++ parameter, state, result, and simulation types to Python through pybind11.
- [logging.hpp](C:/Users/jerem/OneDrive/Documents/apogee/src/cpp/logging.hpp) declares the functions that initialize and append entity state data to a result.
- [logging.cpp](C:/Users/jerem/OneDrive/Documents/apogee/src/cpp/logging.cpp) creates entity result series and records position, velocity, acceleration, and speed at every timestep.

### C++ core and data types

- [entity.hpp](C:/Users/jerem/OneDrive/Documents/apogee/src/cpp/core/entity.hpp) defines an internal simulation entity with its identity, classification, team, and kinematic state.
- [kinematic_state.hpp](C:/Users/jerem/OneDrive/Documents/apogee/src/cpp/core/kinematic_state.hpp) groups an entity’s position, velocity, and acceleration vectors.
- [vec3.hpp](C:/Users/jerem/OneDrive/Documents/apogee/src/cpp/core/vec3.hpp) defines the reusable three-component Cartesian vector type.
- [result.hpp](C:/Users/jerem/OneDrive/Documents/apogee/src/cpp/core/result.hpp) defines the renderer-neutral entities, axes, scalar series, vector series, grids, and overall simulation result.

### C++ systems

- [motion_system.hpp](C:/Users/jerem/OneDrive/Documents/apogee/src/cpp/systems/motion_system.hpp) declares the function that advances an entity’s kinematic state.
- [motion_system.cpp](C:/Users/jerem/OneDrive/Documents/apogee/src/cpp/systems/motion_system.cpp) updates position from velocity and velocity from acceleration over a timestep.

### C++ analyses

- [radar_range.hpp](C:/Users/jerem/OneDrive/Documents/apogee/src/cpp/analysis/radar_range.hpp) declares the radar SNR-versus-range analysis function.
- [radar_range.cpp](C:/Users/jerem/OneDrive/Documents/apogee/src/cpp/analysis/radar_range.cpp) calculates SNR samples over range and appends the resulting axis and scalar series to `Result`.

### Python execution

- [main.py](C:/Users/jerem/OneDrive/Documents/apogee/src/python/main.py) creates parameters, runs the bound C++ simulation, and sends the result to Rerun.
- [params.py](C:/Users/jerem/OneDrive/Documents/apogee/src/python/params.py) constructs the default bound parameter object and applies scenario-specific Python overrides.
- [add_build_to_path.py](C:/Users/jerem/OneDrive/Documents/apogee/src/python/add_build_to_path.py) finds the selected compiled extension and rejects missing, incompatible, or stale C++ builds.
- [plot_result.py](C:/Users/jerem/OneDrive/Documents/apogee/src/python/plot_result.py) preserves the old `plot_result` import while redirecting it to the unified Rerun visualization pipeline.
- [rerun_integration.py](C:/Users/jerem/OneDrive/Documents/apogee/src/python/rerun_integration.py) preserves the older `show_in_rerun` import as another compatibility alias.

### Python visualization

- [visualization/\_\_init\_\_.py](C:/Users/jerem/OneDrive/Documents/apogee/src/python/visualization/__init__.py) exports the public `log_result`, `show_result`, and `save_result` visualization functions.
- [rerun_adapter.py](C:/Users/jerem/OneDrive/Documents/apogee/src/python/visualization/rerun_adapter.py) converts entities, trajectories, telemetry, analyses, and grids into Rerun data.
- [rerun_blueprint.py](C:/Users/jerem/OneDrive/Documents/apogee/src/python/visualization/rerun_blueprint.py) dynamically creates the Scenario, Telemetry, and per-entity Analysis tabs in the Rerun UI.
- [rerun_paths.py](C:/Users/jerem/OneDrive/Documents/apogee/src/python/visualization/rerun_paths.py) generates stable Rerun entity paths from entity, system, and quantity keys.
- [chart_renderer.py](C:/Users/jerem/OneDrive/Documents/apogee/src/python/visualization/chart_renderer.py) renders continuous XY analyses as labeled scientific chart images with independently scaled axes.

### Tests

- [tests/conftest.py](C:/Users/jerem/OneDrive/Documents/apogee/tests/conftest.py) configures pytest to load the current Release build of the C++ extension.
- [test_result_visualization.py](C:/Users/jerem/OneDrive/Documents/apogee/tests/test_result_visualization.py) tests the fixed simulation output, chart rendering, Rerun serialization, grids, 3D analyses, and `.rrd` saving.

### Formal documentation

- [architecture.md](C:/Users/jerem/OneDrive/Documents/apogee/docs/architecture.md) describes the intended coordinate system, units, time model, state ownership, language responsibilities, and logging architecture.
- [docs.txt](C:/Users/jerem/OneDrive/Documents/apogee/docs/docs.txt) is a placeholder explaining that the folder will contain simulation documentation.

### Development notes

- [c++.txt](C:/Users/jerem/OneDrive/Documents/apogee/dev_notes/c++.txt) records C++ naming, organization, typing, build, and struct-versus-class conventions.
- [development.txt](C:/Users/jerem/OneDrive/Documents/apogee/dev_notes/development.txt) records the intended repository and documentation workflow.
- [plots.txt](C:/Users/jerem/OneDrive/Documents/apogee/dev_notes/plots.txt) describes the goal of producing a compact post-run analysis dashboard.
- [priorities.txt](C:/Users/jerem/OneDrive/Documents/apogee/dev_notes/priorities.txt) lists the long-term technical features planned for APOGEE.
- [scope.txt](C:/Users/jerem/OneDrive/Documents/apogee/dev_notes/scope.txt) describes the intended missile-defense scenario, participants, victory conditions, and initial feature depth.
- [simulation.txt](C:/Users/jerem/OneDrive/Documents/apogee/dev_notes/simulation.txt) records the initial simulation simplifications, ECI coordinate approach, entity states, and analysis-versus-simulation distinction.
- [stack.txt](C:/Users/jerem/OneDrive/Documents/apogee/dev_notes/stack.txt) records the intended Python, C++, machine-learning, storage, build, and UI technology stack.
- [visualization.txt](C:/Users/jerem/OneDrive/Documents/apogee/dev_notes/visualization.txt) contains the older visualization plan that separated Matplotlib analysis from Rerun motion and is now partly outdated.
- [working.txt](C:/Users/jerem/OneDrive/Documents/apogee/dev_notes/working.txt) contains short-term working notes about Rerun trajectories and coordinate-frame conversions.
