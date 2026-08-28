# Adding analysis visualizations

Calculations publish semantic data to C++ `Result`. They never construct Qt,
Matplotlib, or Rerun objects.

## Choose one of three shapes

| Result type | Use it for | Presentation |
| --- | --- | --- |
| `Curve1D` | Static Y-versus-X results | Matplotlib line plot |
| `GridSeries2D` | One or more time-indexed 2D scalar fields | Heatmap with time controls |
| `MetricTable` | Related scalar metrics, constant or time-indexed | Qt table with time controls |

Timeline scene data uses `ScalarSeries` or `VectorSeries3` instead and is sent
to Rerun automatically.

## Adding a calculation

1. Perform the calculation in C++.
2. Append its result to `result.curves`, `result.grid_series`, or
   `result.metric_tables`.
3. Rebuild and run.

Python's analysis catalog normalizes all products in those collections. The
renderer registry selects the existing view from the product shape. No path,
tab, serialization, or Rerun changes are required.

Every product supplies:

- `entity_id`: owner, or `0` for global analysis
- `system`: subsystem grouping
- `key`: stable machine identity
- `name`: user-facing title
- `presentation.group`: optional navigator subgroup
- `presentation.order`: optional display order

The tuple `(entity_id, system, key)` must be unique.

## Shape contracts

### Curve1D

```text
values.size() == x_axis.values.size()
```

Use it for a completed parameter sweep such as SNR versus range. Do not add a
synthetic time axis to a static curve.

### GridSeries2D

Values contain consecutive row-major frames:

```text
values.size() == time_axis.values.size() * rows * columns
x_axis.values.size() == columns
y_axis.values.size() == rows
```

A static grid is one frame. Always use one series rather than one product per
timestep; the navigator remains compact and the renderer updates one mesh.

### MetricTable

Each `MetricSeries.values` contains either:

- one constant value for the complete run, or
- one value per `MetricTable.time_axis` sample.

This allows a single state table to combine time-varying target range/SNR with
constant parameters such as PW and PRI.

## Adding a genuinely new shape

Only introduce another result type when these three cannot represent the data
faithfully. The extension points are deliberately small:

1. Define and bind the C++ DTO.
2. Add one normalizer in `analysis/catalog.py`.
3. Add one widget factory to `RENDERERS` in `analysis/renderers.py`.

The navigator and unified application shell require no changes. Rerun requires
changes only for genuine scene or timeline telemetry.
