#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <algorithm>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

#include "core/entity_definition.hpp"
#include "core/kinematic_state.hpp"
#include "core/result.hpp"
#include "core/scenario_params.hpp"
#include "params.hpp"
#include "run_sim.hpp"
#include "scenarios/default/default_scenario.hpp"

namespace py = pybind11;

namespace
{
// Expand a parameter struct's descriptor tuple into writable Python fields.
template <typename Type>
void bind_parameter_fields(py::class_<Type>& binding)
{
    std::apply(
        [&](const auto&... field)
        {
            (binding.def_readwrite(field.key, field.member), ...);
        },
        Type::fields()
    );
}

// Register one reusable parameter type with its default constructor and fields.
template <typename Type>
void bind_parameter_class(py::module_& module, const char* name)
{
    py::class_<Type> binding{module, name};
    binding.def(py::init<>());
    bind_parameter_fields(binding);
}

// Visit every described scalar while carrying its UI group and dotted path.
template <typename Type, typename Visitor>
void visit_parameter_fields(
    Type& values,
    const std::string& group,
    const std::string& prefix,
    Visitor& visitor
)
{
    std::apply(
        [&](const auto&... field)
        {
            (visitor(
                ParameterSpec{
                    group,
                    prefix + "." + field.key,
                    field.name,
                    field.unit
                },
                values.*(field.member)
            ), ...);
        },
        Type::fields()
    );
}

// Flatten the three Vec3 members into the nine editable kinematic values.
template <typename Visitor>
void visit_kinematics(
    KinematicState& state,
    const std::string& group,
    const std::string& prefix,
    Visitor& visitor
)
{
    for (const KinematicParameterField& field : KINEMATIC_PARAMETER_FIELDS)
    {
        double& value =
            (state.*(field.vector_member)).*(field.component_member);

        visitor(
            ParameterSpec{
                group,
                prefix + "." + field.path,
                field.name,
                field.unit
            },
            value
        );
    }
}

// Walk the complete scenario in the same order shown by the parameter window.
template <typename Visitor>
void visit_parameters(ScenarioParams& params, Visitor&& visitor)
{
    auto& callback = visitor;

    visit_parameter_fields(
        params.simulation,
        "Simulation",
        "simulation",
        callback
    );
    visit_parameter_fields(
        params.radar_analysis,
        "Radar Analysis",
        "radar_analysis",
        callback
    );

    for (EntityDefinition& entity : params.entities)
    {
        visit_kinematics(
            entity.initial_kinematics,
            entity.display_name,
            entity.key + ".initial_kinematics",
            callback
        );

        // Only expose radar fields for definitions that actually own a radar.
        if (entity.radar)
        {
            visit_parameter_fields(
                *entity.radar,
                entity.display_name,
                entity.key + ".radar",
                callback
            );
        }

        visit_parameter_fields(
            entity,
            entity.display_name,
            entity.key,
            callback
        );
    }
}

// Build UI metadata from a fresh default scenario so defaults stay in C++.
std::vector<ParameterSpec> make_parameter_specs()
{
    ScenarioParams params = make_default_scenario();
    std::vector<ParameterSpec> specs;

    visit_parameters(
        params,
        [&](const ParameterSpec& spec, double&)
        {
            specs.push_back(spec);
        }
    );

    return specs;
}

// Resolve a dotted UI path through the shared parameter visitor.
double get_parameter(ScenarioParams& params, const std::string& path)
{
    double value = 0.0;
    bool found = false;

    visit_parameters(
        params,
        [&](const ParameterSpec& spec, double& parameter_value)
        {
            if (spec.path == path)
            {
                value = parameter_value;
                found = true;
            }
        }
    );

    if (!found)
    {
        throw std::invalid_argument("Unknown parameter path: " + path);
    }

    return value;
}

// Update a dotted UI path through the same traversal used for metadata.
void set_parameter(
    ScenarioParams& params,
    const std::string& path,
    double value
)
{
    bool found = false;

    visit_parameters(
        params,
        [&](const ParameterSpec& spec, double& parameter_value)
        {
            if (spec.path == path)
            {
                parameter_value = value;
                found = true;
            }
        }
    );

    if (!found)
    {
        throw std::invalid_argument("Unknown parameter path: " + path);
    }
}

// Return the actual vector element so Python edits the stored definition.
EntityDefinition& find_entity_definition(
    ScenarioParams& params,
    const std::string& key
)
{
    const auto match = std::find_if(
        params.entities.begin(),
        params.entities.end(),
        [&](const EntityDefinition& entity)
        {
            return entity.key == key;
        }
    );

    if (match == params.entities.end())
    {
        throw std::invalid_argument("Unknown entity key: " + key);
    }

    return *match;
}
}

PYBIND11_MODULE(apogee, m)
{
    m.doc() = "Python bindings for the Apogee simulation";

    // Expose the reusable vector and kinematic state value types first.
    py::class_<Vec3>(m, "Vec3")
        .def(py::init<>())
        .def_readwrite("x", &Vec3::x)
        .def_readwrite("y", &Vec3::y)
        .def_readwrite("z", &Vec3::z);

    py::class_<KinematicState>(m, "KinematicState")
        .def(py::init<>())
        .def_readwrite("pos_m", &KinematicState::pos_m)
        .def_readwrite("vel_mps", &KinematicState::vel_mps)
        .def_readwrite("accel_mps2", &KinematicState::accel_mps2);

    // Bind generic parameter types without creating entity-specific classes.
    bind_parameter_class<SimulationParams>(m, "SimulationParams");
    bind_parameter_class<RadarParams>(m, "RadarParams");
    bind_parameter_class<RadarAnalysisParams>(m, "RadarAnalysisParams");

    // Keep entity identity read-only while allowing its configurable data to change.
    py::class_<EntityDefinition>(m, "EntityDefinition")
        .def_readonly("id", &EntityDefinition::id)
        .def_readonly("key", &EntityDefinition::key)
        .def_readonly("display_name", &EntityDefinition::display_name)
        .def_readonly("type", &EntityDefinition::type)
        .def_readonly("team", &EntityDefinition::team)
        .def_readwrite(
            "initial_kinematics",
            &EntityDefinition::initial_kinematics
        )
        // Return the contained optional by reference instead of a Python copy.
        .def_property_readonly(
            "radar",
            [](EntityDefinition& entity) -> RadarParams*
            {
                return entity.radar ? &*entity.radar : nullptr;
            },
            py::return_value_policy::reference_internal
        )
        .def_readwrite(
            "radar_signature_dbsm",
            &EntityDefinition::radar_signature_dbsm
        );

    // Construct Python Params from the four-entity default scenario each run.
    py::class_<ScenarioParams>(m, "Params")
        .def(py::init([]()
        {
            return make_default_scenario();
        }))
        .def_readwrite("simulation", &ScenarioParams::simulation)
        .def_readwrite("radar_analysis", &ScenarioParams::radar_analysis)
        .def(
            "entity",
            &find_entity_definition,
            py::return_value_policy::reference_internal,
            py::arg("key")
        );

    // ParameterSpec supplies labels and units without duplicating them in Python.
    py::class_<ParameterSpec>(m, "ParameterSpec")
        .def_readonly("group", &ParameterSpec::group)
        .def_readonly("path", &ParameterSpec::path)
        .def_readonly("name", &ParameterSpec::name)
        .def_readonly("unit", &ParameterSpec::unit);

    m.def(
        "parameter_specs",
        &make_parameter_specs,
        "Return the parameter names, units, groups, and attribute paths."
    );
    m.def(
        "get_parameter",
        &get_parameter,
        py::arg("params"),
        py::arg("path"),
        "Return one editable parameter by path."
    );
    m.def(
        "set_parameter",
        &set_parameter,
        py::arg("params"),
        py::arg("path"),
        py::arg("value"),
        "Set one editable parameter by path."
    );

    // Bind the result DTOs so Python can pass simulation output to Rerun.
    py::class_<EntityDescriptor>(m, "EntityDescriptor")
        .def(py::init<>())
        .def_readwrite("id", &EntityDescriptor::id)
        .def_readwrite("key", &EntityDescriptor::key)
        .def_readwrite("display_name", &EntityDescriptor::display_name)
        .def_readwrite("type", &EntityDescriptor::type)
        .def_readwrite("team", &EntityDescriptor::team);

    py::class_<Axis>(m, "Axis")
        .def(py::init<>())
        .def_readwrite("key", &Axis::key)
        .def_readwrite("name", &Axis::name)
        .def_readwrite("unit", &Axis::unit)
        .def_readwrite("kind", &Axis::kind)
        .def_readwrite("values", &Axis::values);

    py::class_<ScalarSeries>(m, "ScalarSeries")
        .def(py::init<>())
        .def_readwrite("entity_id", &ScalarSeries::entity_id)
        .def_readwrite("system", &ScalarSeries::system)
        .def_readwrite("key", &ScalarSeries::key)
        .def_readwrite("name", &ScalarSeries::name)
        .def_readwrite("unit", &ScalarSeries::unit)
        .def_readwrite("axis_key", &ScalarSeries::axis_key)
        .def_readwrite("values", &ScalarSeries::values);

    py::class_<VectorSeries3>(m, "VectorSeries3")
        .def(py::init<>())
        .def_readwrite("entity_id", &VectorSeries3::entity_id)
        .def_readwrite("system", &VectorSeries3::system)
        .def_readwrite("key", &VectorSeries3::key)
        .def_readwrite("name", &VectorSeries3::name)
        .def_readwrite("unit", &VectorSeries3::unit)
        .def_readwrite("frame", &VectorSeries3::frame)
        .def_readwrite("axis_key", &VectorSeries3::axis_key)
        .def_readwrite("values", &VectorSeries3::values);

    py::class_<Grid2D>(m, "Grid2D")
        .def(py::init<>())
        .def_readwrite("entity_id", &Grid2D::entity_id)
        .def_readwrite("system", &Grid2D::system)
        .def_readwrite("key", &Grid2D::key)
        .def_readwrite("name", &Grid2D::name)
        .def_readwrite("x_axis", &Grid2D::x_axis)
        .def_readwrite("y_axis", &Grid2D::y_axis)
        .def_readwrite("value_unit", &Grid2D::value_unit)
        .def_readwrite("rows", &Grid2D::rows)
        .def_readwrite("columns", &Grid2D::columns)
        .def_readwrite("values", &Grid2D::values)
        .def_readwrite("has_display_range", &Grid2D::has_display_range)
        .def_readwrite("display_min", &Grid2D::display_min)
        .def_readwrite("display_max", &Grid2D::display_max);

    py::class_<Result>(m, "Result")
        .def(py::init<>())
        .def_readwrite("entities", &Result::entities)
        .def_readwrite("axes", &Result::axes)
        .def_readwrite("scalars", &Result::scalars)
        .def_readwrite("vectors", &Result::vectors)
        .def_readwrite("grids", &Result::grids);

    // Expose the simulation as the single C++ execution entry point.
    m.def(
        "run_sim",
        &run_sim,
        py::arg("params"),
        "Run the simulation with the given parameters."
    );
}
