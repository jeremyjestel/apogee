#include "radar_system.hpp"
#include "range_doppler_map.hpp"

void radar_update(Entity& radar,
                  Entity& target)
{
   

    range_doppler_map(radar, target);

    // other options here will be cfar, association, tracking, etc
    //Full radar signal processing chain here
    

}
