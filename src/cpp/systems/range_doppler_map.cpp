#include "systems/range_doppler_map.hpp"

#include "math/distance.hpp"

// Update radar measurements after both entities have completed their motion step.
void range_doppler_map(
    RadarModule& radar,
    const KinematicState& radar_kinematics,
    const KinematicState& target_kinematics
)
{
     //This will be called each time step, independent variable is range in this case.
    // This does assume motion has occurred already
    // Returns the range doppler map the radar sees when tracking the missile, assumes max gain
    // Range is changing state, so recompute it from the current positions.
    radar.state.range_to_target_m = get_3d_distance(
        radar_kinematics.pos_m,
        target_kinematics.pos_m
    );

    
}
