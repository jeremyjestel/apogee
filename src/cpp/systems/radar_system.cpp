#include "systems/radar_system.hpp"

#include "systems/range_doppler_map.hpp"

void radar_update(Entity& radar,
                  const Entity& target)
{
    // Entities without a radar component have no radar processing to perform.
    if (!radar.radar)
    {
        return;
    }

    // Pass only the owned module and the two kinematic states to processing.
    range_doppler_map(
        *radar.radar,
        radar.kinematics,
        target.kinematics
    );

    // Future CFAR, association, and tracking stages belong in this chain.
}
