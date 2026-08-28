#pragma once

#include <cstddef>
#include <string>
#include <vector>

#include "core/vec3.hpp"

// EntityDescriptor preserves identity and presentation metadata beside result data.
struct EntityDescriptor
{
    int id = 0;
    std::string key;
    std::string display_name;
    std::string type;
    std::string team;
};

// Axis stores samples interpreted as time, sequence indices, or analysis coordinates.
struct Axis
{
    std::string key;
    std::string name;
    std::string unit;
    std::string kind;
    std::vector<double> values;
};

// Optional placement hints keep product ordering/grouping out of the Python UI.
// New fields can be added here without changing every analysis result type.
struct Presentation
{
    std::string group;
    int order = 0;
};

// A scalar series stores one physical value per sample on a referenced axis.
struct ScalarSeries
{
    int entity_id = 0;
    std::string system;
    std::string key;
    std::string name;
    std::string unit;
    std::string axis_key;
    std::vector<double> values;
    Presentation presentation;
};

// A static one-dimensional analysis curve owns its coordinate axis directly.
struct Curve1D
{
    int entity_id = 0;
    std::string system;
    std::string key;
    std::string name;
    Axis x_axis;
    std::string value_unit;
    std::vector<double> values;
    Presentation presentation;
};

// A metric series is either aligned with its table's time axis or is a
// singleton value that remains constant for the complete run.
struct MetricSeries
{
    std::string key;
    std::string name;
    std::string unit;
    std::vector<double> values;
};

// A metric table groups related scalar values under one optional timeline.
struct MetricTable
{
    int entity_id = 0;
    std::string system;
    std::string key;
    std::string name;
    Axis time_axis;
    std::vector<MetricSeries> metrics;
    Presentation presentation;
};

// A vector series keeps XYZ values together so they can be drawn as a 3D path.
struct VectorSeries3
{
    int entity_id = 0;
    std::string system;
    std::string key;
    std::string name;
    std::string unit;
    std::string frame;
    std::string axis_key;
    std::vector<Vec3> values;
    Presentation presentation;
};

// A time-indexed row-major scalar field. Each frame contains rows * columns
// values, with x_axis addressing columns and y_axis addressing rows. A static
// grid is represented by one frame rather than a separate result type.
struct GridSeries2D
{
    int entity_id = 0;
    std::string system;
    std::string key;
    std::string name;
    Axis time_axis;
    Axis x_axis;
    Axis y_axis;
    std::string value_unit;
    std::size_t rows = 0;
    std::size_t columns = 0;
    std::vector<double> values;
    bool has_display_range = false;
    double display_min = 0.0;
    double display_max = 0.0;
    Presentation presentation;
};

// Result is the complete, visualization-neutral output returned by a simulation run.
struct Result
{
    std::vector<EntityDescriptor> entities;
    std::vector<Axis> axes;
    std::vector<ScalarSeries> scalars;
    std::vector<Curve1D> curves;
    std::vector<MetricTable> metric_tables;
    std::vector<VectorSeries3> vectors;
    std::vector<GridSeries2D> grid_series;
};
