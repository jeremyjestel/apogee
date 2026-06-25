#include "params.hpp"
#include <pybind11/pybind11.h>
namespace py = pybind11;

Params params_from_dict(const py::dict& d) {
    Params p;
#define FIELD(name, type, def) \
    if (d.contains(#name)) p.name = d[#name].cast<type>();
#include "params_fields.inc"
#undef FIELD
    return p;
}