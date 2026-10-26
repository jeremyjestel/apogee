#include "sensors/sensor_system.hpp"
#include <vector>
#include "core/entity.hpp"
#include "sensors/radar/radar_system.hpp"


namespace apogee {

    void sense(std::vector<Entity> &entities, double dt, std::mt19937& rng){

            // Loop each sensor type applicable for this entity
            // Question is whether to do a list of the applicable sensors looped through, or check if all types exist
        radar_system(entities, rng);
        // gps(entities, dt);
    }

}
