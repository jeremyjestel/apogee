#pragma once
#include <random>
#include <vector>

namespace apogee {

    struct Entity;

    void sense(std::vector<Entity> &entities, double dt, std::mt19937& rng);

}
