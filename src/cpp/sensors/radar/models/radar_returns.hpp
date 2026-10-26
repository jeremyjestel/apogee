#pragma once

#include <random>
#include <vector>

#include "core/entity.hpp"

namespace apogee{
    void generate_returns(const KinematicStateECI &entity_motion,
        RadarComponent &radar,
        const std::vector<Entity> &targets,
        std::mt19937 &rng);
}

