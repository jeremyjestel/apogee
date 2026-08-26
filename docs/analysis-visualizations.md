# Adding analysis visualizations

Analysis code publishes semantic data to `Result`; it does not construct Rerun
views. The Python `ViewCatalog` validates each item once, then drives both result
logging and tab creation. Using an existing result type therefore requires no
Python visualization changes.

## Choose the data shape

| Type | Use it for | Rerun presentation |
| --- | --- | --- |
| `Curve1D` | A static Y-versus-X result such as SNR versus range | Labeled 2D plot |
| `Grid2D` | A scalar field such as range versus pulse or Doppler | Labeled heatmap and colorbar |
| `Snapshot` | Related scalar values captured at one point in the run | Markdown value table |

`ScalarSeries` and `VectorSeries3` remain appropriate for sampled timelines and
3D data. Do not represent a static curve or a state table with a synthetic time
axis; use `Curve1D` or `Snapshot` instead.

## Minimal producer workflow

1. Compute the analysis in C++.
2. Append one semantic item to the matching `Result` collection.
3. Rebuild the extension and run normally.

For example, a self-contained curve needs only:

```cpp
result.curves.push_back(Curve1D{
    .entity_id = radar_entity_id,
    .system = "radar",
    .key = "detection_probability",
    .name = "Detection Probability",
    .x_axis = Axis{
        .key = "snr_db",
        .name = "SNR",
        .unit = "dB",
        .kind = "continuous",
        .values = std::move(snr_db)
    },
    .value_unit = "%",
    .values = std::move(probability_percent),
    .presentation = Presentation{
        .group = "Detection",
        .order = 40
    }
});
```

The existing SNR producer in `src/cpp/analysis/radar_range.cpp` is a complete
`Curve1D` example. The radar state snapshot in `src/cpp/run_sim.cpp` and the
range-pulse conversion in `src/cpp/systems/range_doppler_map.cpp` show the other
two shapes.

For a `Snapshot`, put each labeled value in a `Metric` and append the snapshot to
`result.snapshots`. For a `Grid2D`, store values in row-major order and maintain
these invariants:

```text
values.size() == rows * columns
x_axis.values.size() == columns
y_axis.values.size() == rows
```

Set `has_display_range`, `display_min`, and `display_max` only when the heatmap
needs a fixed color scale; otherwise its scale is inferred from the values.

## Naming and automatic layout

- `entity_id` selects the owner tab. Use `0` for a global analysis.
- `system` groups the data path by producing subsystem.
- `key` is the stable, machine-facing product identifier.
- `name` and units are display metadata.
- `presentation.order` optionally orders products across all result types.
- `presentation.group` optionally creates one additional nested tab level.

The combination of owner, `system`, and `key` must be unique. A nonempty analysis
item automatically appears at:

```text
Analysis → <Entity display name | Global> → <Product name>
```

Each product receives a full-size tab. The catalog chooses the correct view and
the adapter chooses the correct logger from the semantic type, so neither the
blueprint nor the adapter needs product-specific conditionals.

Leave `Presentation` at its defaults when the catalog's stable type order is
sufficient. Order `0` means automatic placement after explicitly ordered
products. Use sparse nonzero values such as 10, 20, and 30 so later products fit
between them. Products with the same nonempty group are collected into a nested
tab set; the group is ordered by its first product.

## Rendered and machine-readable data

Static analysis products are recorded below one stable base path:

```text
/analysis/entities/<owner>/<system>/<key>/plot
/analysis/entities/<owner>/<system>/<key>/data
```

`/plot` contains the rendered chart, heatmap, or table used by the tab. Static
charts and heatmaps are stored as lossless PNGs to keep large recordings
compact. `/data` contains a native Rerun tensor; its axis and metadata children
retain physical coordinates, labels, and units. Telemetry stays in Rerun's
native timeline form and receives the same queryable metadata. Keep calculations
and full-precision values in the semantic result object; presentation-only
choices belong in the renderer. This separation allows future exports,
alternate renderers, and inspection without recomputing the analysis.

Time axes may use `s`, `ms`, `us`, or `ns`; the adapter normalizes them to
seconds for Rerun while preserving the declared unit in raw metadata. Sequence
axes must contain integer values. Grid coordinate axes must be strictly
monotonic.

Only introduce a new result type when the data cannot be expressed faithfully as
a curve, grid, snapshot, scalar timeline, or 3D series. A genuinely new shape
requires a C++ DTO and binding, one product reader in `view_catalog.py`, and one
logger in `rerun_adapter.py`; the generic blueprint does not change. Individual
products of an existing shape require none of those Python changes.
