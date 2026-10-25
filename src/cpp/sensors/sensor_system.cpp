#pragma once
#include <vector>
#include "core/entity.hpp"
#include "core/constants.hpp"
#include "motion/models/gravity.hpp"


namespace apogee {

    inline void sense(std::vector<Entity> &entities, double dt, std::mt19937& rng){

            // Loop each sensor type applicable for this entity
            // Question is whether to do a list of the applicable sensors looped through, or check if all types exist
        radar_system(entities, dt);
        gps(entities, dt);
    }

}
