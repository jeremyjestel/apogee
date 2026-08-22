#pragma once

#include "params.hpp"
#include "core/result.hpp"

void append_radar_range_analysis(
    const BlueRadarParams& radar,
    int entity_id,
    Result& result
);
