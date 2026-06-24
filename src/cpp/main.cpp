#pragma once
#include <vector>

struct Params
{
    double dt_s = 0.1;
    double duration_s = 10.0;
    double velocity = 100.0;
};

struct State
{
    double time_s;
    double x;
};

struct Result
{
    std::vector<State> history;
};

inline Result run_sim(const Params& p)
{
    Result r;

    double t = 0.0;
    double x = 0.0;

    while (t <= p.duration_s)
    {
        r.history.push_back({t, x});

        x += p.velocity * p.dt_s;
        t += p.dt_s;
    }

    return r;
}