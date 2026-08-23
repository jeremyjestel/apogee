#include "range_doppler_map.hpp"
#include <cmath>
#include "core/distance.hpp"

//This will be called each time step, independent variable is range in this case.
// This does assume motion has occurred already
//Returns the range doppler map the radar sees when tracking the missile, assumes max gain
void range_doppler_map(Entity& radar,
                       Entity& target)
{
    double range_to_target = get_3d_distance(radar.kinematics.pos_m, target.kinematics.pos_m);

    
    
}
