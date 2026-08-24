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
};


// A row-major scalar field. x_axis has columns entries and y_axis has rows.
struct Grid2D
{
    int entity_id = 0;
    std::string system;
    std::string key;
    std::string name;
    Axis x_axis;
    Axis y_axis;
    std::string value_unit;
    std::size_t rows = 0;
    std::size_t columns = 0;
    std::vector<double> values;
    bool has_display_range = false;
    double display_min = 0.0;
    double display_max = 0.0;
};

// Result is the complete, visualization-neutral output returned by a simulation run.
struct Result
{
    std::vector<EntityDescriptor> entities;
    std::vector<Axis> axes;
    std::vector<ScalarSeries> scalars;
    std::vector<VectorSeries3> vectors;
    std::vector<Grid2D> grids;
};
