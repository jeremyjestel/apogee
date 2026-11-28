#include "sensors/sensor_system.hpp"
#include <vector>
#include "core/entity.hpp"
#include "sensors/radar/radar_system.hpp"


namespace apogee {

    void sense(std::vector<Entity> &entities, double dt, std::mt19937& rng){

            // Sensor systems publish detections to each entity's common belief inbox.
            // Association and track management belong to estimation, across all sensors.
        radar_system(entities, rng);
        // gps(entities, dt);
    }

}
