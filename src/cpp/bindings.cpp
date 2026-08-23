#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "params.hpp"
#include "run_sim.hpp"
#include "core/kinematic_state.hpp"
#include "core/result.hpp"

namespace py = pybind11;

PYBIND11_MODULE(apogee, m)
{
    m.doc() = "Python bindings for the Apogee simulation";

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

#define APOGEE_BIND_PARAMETER(OWNER, KIND, TYPE, MEMBER, INITIAL, NAME, UNIT) \
    OWNER##_binding.def_readwrite(#MEMBER, &OWNER::MEMBER);

#define APOGEE_BIND_PARAMETER_GROUP(ROOT, OWNER, GROUP, PARAMETERS)         \
    py::class_<OWNER> OWNER##_binding{m, #OWNER};                           \
    OWNER##_binding.def(py::init<>());                                      \
    PARAMETERS(APOGEE_BIND_PARAMETER, OWNER)

    APOGEE_PARAMETER_GROUPS(APOGEE_BIND_PARAMETER_GROUP)

#undef APOGEE_BIND_PARAMETER_GROUP
#undef APOGEE_BIND_PARAMETER

    py::class_<Params> params_binding{m, "Params"};
    params_binding.def(py::init<>());

#define APOGEE_BIND_GROUP(ROOT, TYPE, GROUP, PARAMETERS)                    \
    params_binding.def_readwrite(#ROOT, &Params::ROOT);

    APOGEE_PARAMETER_GROUPS(APOGEE_BIND_GROUP)

#undef APOGEE_BIND_GROUP

    py::class_<ParameterSpec>(m, "ParameterSpec")
        .def_readonly("group", &ParameterSpec::group)
        .def_readonly("path", &ParameterSpec::path)
        .def_readonly("name", &ParameterSpec::name)
        .def_readonly("unit", &ParameterSpec::unit);

    m.def(
        "parameter_specs",
        &parameter_specs,
        "Return the parameter names, units, groups, and attribute paths."
    );

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

    m.def(
        "run_sim",
        &run_sim,
        py::arg("params"),
        "Run the simulation with the given parameters."
    );
}
