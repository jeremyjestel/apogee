#pragma once
#include <vector>

namespace apogee {

    struct Entity;

    void motion_step(std::vector<Entity> &entities, double dt);

}