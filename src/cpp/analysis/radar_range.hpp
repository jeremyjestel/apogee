#pragma once

#include "core/result.hpp"
#include "params.hpp"

void append_radar_range_analysis(const BlueRadarParams& radar,
                                 int entity_id,
                                 Result& result);
