#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "params.hpp"
#include "run_sim.hpp"
#include "components/kinematic_state.hpp"
#include "parameter/result.hpp"

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

    py::class_<SimulationParams>(m, "SimulationParams")
        .def(py::init<>())
        .def_readwrite("dt_s", &SimulationParams::dt_s)
        .def_readwrite("duration_s", &SimulationParams::duration_s)
        .def_readwrite("coordinate_frame", &SimulationParams::coordinate_frame);

    py::class_<BlueRadarParams>(m, "BlueRadarParams")
        .def(py::init<>())
        .def_readwrite("initial_kinematics", &BlueRadarParams::initial_kinematics)
        .def_readwrite("frequency_hz", &BlueRadarParams::frequency_hz)
        .def_readwrite("wavelength_m", &BlueRadarParams::wavelength_m)
        .def_readwrite("power_dbw", &BlueRadarParams::power_dbw)
        .def_readwrite("tx_gain_db", &BlueRadarParams::tx_gain_db)
        .def_readwrite("rx_gain_db", &BlueRadarParams::rx_gain_db)
        .def_readwrite("RCS_dbsm", &BlueRadarParams::RCS_dbsm)
        .def_readwrite("noise_figure_db", &BlueRadarParams::noise_figure_db)
        .def_readwrite("bandwidth_hz", &BlueRadarParams::bandwidth_hz)
        .def_readwrite("system_loss_db", &BlueRadarParams::system_loss_db)
        .def_readwrite("max_range_m", &BlueRadarParams::max_range_m)
        .def_readwrite("range_step_m", &BlueRadarParams::range_step_m);

    py::class_<BlueSatelliteParams>(m, "BlueSatelliteParams")
        .def(py::init<>())
        .def_readwrite("initial_kinematics", &BlueSatelliteParams::initial_kinematics);

    py::class_<RedMissileParams>(m, "RedMissileParams")
        .def(py::init<>())
        .def_readwrite("initial_kinematics", &RedMissileParams::initial_kinematics)
        .def_readwrite("mass_kg", &RedMissileParams::mass_kg)
        .def_readwrite("speed_mps", &RedMissileParams::speed_mps)
        .def_readwrite("drag_coefficient", &RedMissileParams::drag_coefficient);

    py::class_<BlueInterceptorParams>(m, "BlueInterceptorParams")
        .def(py::init<>())
        .def_readwrite("initial_kinematics", &BlueInterceptorParams::initial_kinematics)
        .def_readwrite("mass_kg", &BlueInterceptorParams::mass_kg)
        .def_readwrite("thrust_n", &BlueInterceptorParams::thrust_n)
        .def_readwrite("max_g", &BlueInterceptorParams::max_g);

    py::class_<Params>(m, "Params")
        .def(py::init<>())
        .def_readwrite("simulation", &Params::simulation)
        .def_readwrite("blue_radar", &Params::blue_radar)
        .def_readwrite("blue_satellite", &Params::blue_satellite)
        .def_readwrite("red_missile", &Params::red_missile)
        .def_readwrite("blue_interceptor", &Params::blue_interceptor);

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
