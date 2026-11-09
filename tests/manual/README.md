# Entity function playground

Edit `make_test_entities()` in `entity_playground.cpp` to set positions, velocities,
gains, and control state. Positions use ECI meters; the sample `lla2eci` calls
convert latitude, longitude, and altitude at simulation time zero. Target indices
refer to the returned vector's order. Add function calls in `main()` as needed.

Build and run from the repository root:

```bat
cmake --build build --config Debug --target apogee_entity_playground
build\Debug\apogee_entity_playground.exe prop_nav
```

Available arguments: `prop_nav` (default), `point_nav`, `guidance`, `controls`,
`motion`, and `pipeline`. Each invocation creates fresh entities and prints
before/after states. `point_nav` moves the satellite beyond the horizon;
`controls` supplies a sample acceleration command. The other examples use the
states from `make_test_entities()` directly.

`prop_nav` and `point_nav` call the models directly. `guidance` includes model
selection and gravity compensation. `pipeline` runs guidance, controls, and
motion together; edit `dt_s` and `steps` in `main()` to run multiple steps.

In VS Code, select **APOGEE: Debug entity playground**. Change its `args` in
`.vscode/launch.json` to select a function and set breakpoints in the playground
or the called C++ functions. This launch configuration builds the playground first.

The playground is intentionally excluded from CTest: it is a place for editable
experiments, separate from the automated regression tests.

Set an entity's `active` member to `false` to disable it during system or pipeline
calls. Direct `prop_nav` and `point_nav` model calls calculate outputs regardless
of that flag. The printed states include `active`.
