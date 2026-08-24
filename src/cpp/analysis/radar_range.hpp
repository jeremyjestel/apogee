#pragma once

#include "core/result.hpp"
#include "params.hpp"

// Append the radar's static SNR-versus-range analysis to a simulation result.
void radar_range_analysis(
    const RadarParams& radar,
    double target_radar_cross_section_dbsm,
    const RadarAnalysisParams& analysis,
    int entity_id,
    Result& result
);
