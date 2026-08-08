#pragma once

#include <utility>
#include <vector>

#include "params.hpp"


std::pair<std::vector<double>, std::vector<double>> compute_rre(const RadarParams& radar);
