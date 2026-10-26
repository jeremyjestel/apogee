#pragma once

#include <vector>

#include "core/entity.hpp"

namespace apogee{
    void process_returns(const KinematicStateECI &radar_pos,
        RadarComponent &radar,
        const std::vector<Entity> &targets);
}

