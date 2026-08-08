#pragma once

#include <vector>

#include "params.hpp"

struct State
{
    double time_s;
    double x;
};

struct Result
{
    std::vector<State> history;
    std::vector<double> ranges_m;
    std::vector<double> snr_db;
};

Result run_simulation(const Params& params);
