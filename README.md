# APOGEE

APOGEE is a C++ and Python missile-defense simulation for modeling interception scenarios. Rerun.io provides the main visual interface for inspecting each simulation. 

## Done so far

- Built a C++ simulation  with an orbiting satellite, incoming missile, a pursuing interceptor, a tracking radar.
- Added fixed-step motion histories for position, velocity, acceleration, and speed.
- Added a Python/PySide parameter interface generated from the C++ parameter schema.
- Added Save Scenario and Load Scenario buttons to reuse parameter sets as JSON files.
- Added a scenario builder with entity add/remove controls, collapsible parameters, editable names, teams and types, and pursuit target selection.
- Integrated Rerun.io as the simulation UI.
- Added an interactive 3D view of the satellite, incoming missile, interceptor, and tracking radar.
- Added timeline controls for replaying completed simulations and inspecting each timestep.
- Added synchronized plots for position, velocity, acceleration, speed, and other telemetry.
- Added reusable Rerun paths and blueprints to keep scene elements and telemetry organized.
- Added radar analysis for signal-to-noise ratio, range-Doppler maps, and radar-state metrics.
- Added automated tests for the parameter interface and analysis visualizations.

## Entity activity

Every entity has `active = true` by default. Set its **Active** parameter to `false`
in the parameter window to start it disabled. Scenario save/load preserves this
setting; older scenarios default to active.

In Python, set `params.entity("red_missile").active = False`, or use
`apogee.set_parameter(params, "red_missile.active", False)` before running.

In C++ simulation or playground code, use `entities[index].active = false` when
your collision, damage, or disable logic decides to deactivate an entity. Set it
back to `true` to resume updates. The entry stays in the entity vector, so target
indices remain valid. Inactive entities freeze their kinematic state, clear their
guidance/control outputs on the next system update, and skip sensor processing.
Radar omits inactive targets, and guidance ignores inactive selected targets.
The `entity/active` history records changes as 1 (active) or 0 (inactive).

This flag represents both destroyed and disabled; it does not automatically
detect collisions or distinguish the reason an entity became inactive. Direct
model calls such as `prop_nav()` still evaluate their inputs; the entity systems
enforce activity checks.

## Planned

- Determine whether each interceptor engagement succeeds and explain the main contributing factors.
- Add realistic missile trajectories, 6-DOF vehicle dynamics, proportional-navigation guidance, and autopilot control.
- Add radar measurement errors, CFAR detection, tracking, and extended Kalman filtering.
- Add seekers, sensor fusion, data association, and datalink latency.
- Add radar propagation, electronic-warfare, and clutter.
- Add Monte Carlo analysis, trajectory optimization, and support for multiple systems on each team.
- Expand the Rerun.io UI with sensor, guidance, engagement, and Monte Carlo visualizations.
