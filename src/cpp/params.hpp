#pragma once
struct Params {
#define FIELD(name, type, def) type name = def;
#include "params_fields.inc"
#undef FIELD
};