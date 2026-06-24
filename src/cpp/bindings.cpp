#include <pybind11/pybind11.h>
#include <string>

namespace py = pybind11;

// simple struct just for transport
struct Params {
    double dt;
    double t_end;
};

std::string run_ack(const Params& p) {
    return "ACK: received params (dt=" +
           std::to_string(p.dt) +
           ", t_end=" +
           std::to_string(p.t_end) + ")";
}

PYBIND11_MODULE(apogee, m) {
    py::class_<Params>(m, "Params")
        .def(py::init<>())
        .def_readwrite("dt", &Params::dt)
        .def_readwrite("t_end", &Params::t_end);

    m.def("run_ack", &run_ack);
}