#pragma once

#include <Eigen/Dense>

#include <optional>

#include "core/kinematic_state.hpp"
#include "core/radar_module.hpp"
#include "core/result.hpp"

// Domain output from the current noisy range-pulse processing stage.
struct RangePulseProduct
{
    Eigen::MatrixXcd samples;
};

// Update the radar module from the current radar and target kinematics.
std::optional<RangePulseProduct> range_doppler_map(
    RadarModule& radar,
    const KinematicState& radar_kinematics,
    const KinematicState& target_kinematics,
    double target_rcs_dbsm
);

// Convert one completed domain product into a one-frame analysis series.
GridSeries2D make_noisy_range_doppler_series(
    const RangePulseProduct& product,
    const RadarParams& radar,
    int radar_entity_id,
    double time_s
);
