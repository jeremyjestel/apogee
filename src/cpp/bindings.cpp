#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "params.hpp"
#include "run_simulation.hpp"

namespace py = pybind11;

PYBIND11_MODULE(apogee, m)
{
    m.doc() = "Python bindings for the Apogee simulation";

    py::class_<RadarParams>(m, "RadarParams")
        .def(py::init<>())
        .def_readwrite("frequency_hz", &RadarParams::frequency_hz)
        .def_readwrite("wavelength_m", &RadarParams::wavelength_m)
        .def_readwrite("power_dbw", &RadarParams::power_dbw)
        .def_readwrite("tx_gain_db", &RadarParams::tx_gain_db)
        .def_readwrite("rx_gain_db", &RadarParams::rx_gain_db)
        .def_readwrite("RCS_dbsm", &RadarParams::RCS_dbsm)
        .def_readwrite("noise_figure_db", &RadarParams::noise_figure_db)
        .def_readwrite("bandwidth_hz", &RadarParams::bandwidth_hz)
        .def_readwrite("system_loss_db", &RadarParams::system_loss_db)
        .def_readwrite("max_range_m", &RadarParams::max_range_m);
        .def_readwrite("range_step_m", &RadarParams::range_step_m);

    py::class_<InterceptorParams>(m, "InterceptorParams")
        .def(py::init<>())
        .def_readwrite("mass_kg", &InterceptorParams::mass_kg)
        .def_readwrite("thrust_n", &InterceptorParams::thrust_n)
        .def_readwrite("max_g", &InterceptorParams::max_g);

    py::class_<MissileParams>(m, "MissileParams")
        .def(py::init<>())
        .def_readwrite("mass_kg", &MissileParams::mass_kg)
        .def_readwrite("speed_mps", &MissileParams::speed_mps)
        .def_readwrite("drag_coefficient", &MissileParams::drag_coefficient);

    py::class_<SimulationParams>(m, "SimulationParams")
        .def(py::init<>())
        .def_readwrite("dt_s", &SimulationParams::dt_s)
        .def_readwrite("duration_s", &SimulationParams::duration_s);

    py::class_<Params>(m, "Params")
        .def(py::init<>())
        .def_readwrite("simulation", &Params::simulation)
        .def_readwrite("radar", &Params::radar)
        .def_readwrite("interceptor", &Params::interceptor)
        .def_readwrite("missile", &Params::missile);

    py::class_<State>(m, "State")
        .def_readonly("time_s", &State::time_s)
        .def_readonly("x", &State::x);

    py::class_<Result>(m, "Result")
        .def_readonly("history", &Result::history)
        .def_readonly("ranges_m", &Result::ranges_m)
        .def_readonly("snr_db", &Result::snr_db);

    m.def(
        "run_sim",
        &run_simulation,
        py::arg("params"),
        "Run the simulation with the given parameters."
    );
}
