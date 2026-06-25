// bindings.cpp
#include <pybind11/pybind11.h>
#include "params.hpp"

// forward from params_conversion.cpp
Params params_from_dict(const py::dict&);

namespace py = pybind11;

static std::string run_ack_from_mapping(py::object mapping) {
    py::dict d;
    if (py::isinstance<py::dict>(mapping)) d = mapping.cast<py::dict>();
    else if (py::hasattr(mapping, "__dict__")) d = mapping.attr("__dict__").cast<py::dict>();
    else throw std::runtime_error("Expected mapping or object with __dict__");

    Params p = params_from_dict(d);
    return run_ack(p); // call your C++ run_ack implementation
}

PYBIND11_MODULE(apogee, m) {
    m.def("run_ack", &run_ack_from_mapping, "Run ack from a mapping or dataclass");
    // optional: expose Params to Python if you want
    py::class_<Params>(m, "Params").def(py::init<>());
}