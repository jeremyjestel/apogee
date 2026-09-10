# APOGEE

APOGEE is a C++ and Python missile-defense simulation for modeling interception scenarios. Rerun.io provides the main visual interface for inspecting each simulation.

## Done so far

- Built a C++ simulation  with an orbiting satellite, incoming missile, a pursuing interceptor, a tracking radar.
- Added fixed-step motion histories for position, velocity, acceleration, and speed.
- Added a Python/PySide parameter interface generated from the C++ parameter schema.
- Integrated Rerun.io as the simulation UI.
- Added an interactive 3D view of the satellite, incoming missile, interceptor, and tracking radar.
- Added timeline controls for replaying completed simulations and inspecting each timestep.
- Added synchronized plots for position, velocity, acceleration, speed, and other telemetry.
- Added reusable Rerun paths and blueprints to keep scene elements and telemetry organized.
- Added radar analysis for signal-to-noise ratio, range-Doppler maps, and radar-state metrics.
- Added automated tests for the parameter interface and analysis visualizations.

## Planned

- Determine whether each interceptor engagement succeeds and explain the main contributing factors.
- Add realistic missile trajectories, 6-DOF vehicle dynamics, proportional-navigation guidance, and autopilot control.
- Add radar measurement errors, CFAR detection, tracking, and extended Kalman filtering.
- Add seekers, sensor fusion, data association, and datalink latency.
- Add radar propagation, electronic-warfare, and clutter.
- Add Monte Carlo analysis, trajectory optimization, and support for multiple systems on each team.
- Expand the Rerun.io UI with sensor, guidance, engagement, and Monte Carlo visualizations.
