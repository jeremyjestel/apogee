#pragma once

#include "core/result.hpp"
#include "params.hpp"

void append_radar_range_analysis(const RadarParams& radar,
                                 double target_radar_cross_section_dbsm,
                                 double max_range_m,
                                 double range_step_m,
                                 int entity_id,
                                 Result& result);
