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
        .def_readwrite("duration_s", &SimulationParams::duration_s);

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

    py::class_<DataSeries>(m, "DataSeries")
        .def(py::init<>())
        .def_readwrite("name", &DataSeries::name)
        .def_readwrite("unit", &DataSeries::unit)
        .def_readwrite("values", &DataSeries::values);

    py::class_<SimulationDataSeries2D>(m, "SimulationDataSeries2D")
        .def(py::init<>())
        .def_readwrite("entity_name", &SimulationDataSeries2D::entity_name)
        .def_readwrite("name", &SimulationDataSeries2D::name)
        .def_readwrite("unit", &SimulationDataSeries2D::unit)
        .def_readwrite("values", &SimulationDataSeries2D::values);

    py::class_<VectorDataSeries>(m, "VectorDataSeries")
        .def(py::init<>())
        .def_readwrite("entity_name", &VectorDataSeries::entity_name)
        .def_readwrite("name", &VectorDataSeries::name)
        .def_readwrite("unit", &VectorDataSeries::unit)
        .def_readwrite("x", &VectorDataSeries::x)
        .def_readwrite("y", &VectorDataSeries::y)
        .def_readwrite("z", &VectorDataSeries::z);

    py::class_<SimulationData2D>(m, "SimulationData2D")
        .def(py::init<>())
        .def_readwrite("name", &SimulationData2D::name)
        .def_readwrite("times_s", &SimulationData2D::times_s)
        .def_readwrite("outputs", &SimulationData2D::outputs);

    py::class_<SimulationData3D>(m, "SimulationData3D")
        .def(py::init<>())
        .def_readwrite("name", &SimulationData3D::name)
        .def_readwrite("times_s", &SimulationData3D::times_s)
        .def_readwrite("outputs", &SimulationData3D::outputs);

    py::class_<Analysis2D>(m, "Analysis2D")
        .def(py::init<>())
        .def_readwrite("name", &Analysis2D::name)
        .def_readwrite("x", &Analysis2D::x)
        .def_readwrite("y", &Analysis2D::y);

    py::class_<Analysis3D>(m, "Analysis3D")
        .def(py::init<>())
        .def_readwrite("name", &Analysis3D::name)
        .def_readwrite("x", &Analysis3D::x)
        .def_readwrite("y", &Analysis3D::y)
        .def_readwrite("z", &Analysis3D::z);

    py::class_<Result>(m, "Result")
        .def(py::init<>())
        .def_readwrite("simulation_2d", &Result::simulation_2d)
        .def_readwrite("simulation_3d", &Result::simulation_3d)
        .def_readwrite("analysis_2d", &Result::analysis_2d)
        .def_readwrite("analysis_3d", &Result::analysis_3d);

    m.def(
        "run_sim",
        &run_sim,
        py::arg("params"),
        "Run the simulation with the given parameters."
    );
}
