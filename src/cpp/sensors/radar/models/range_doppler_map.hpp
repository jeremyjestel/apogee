#pragma once

#include <Eigen/Dense>

#include <optional>

#include "motion/kinematic_state.hpp"
#include "sensors/radar/radar_state.hpp"
#include "core/result.hpp"

namespace apogee
{
	// Domain output from the current noisy range-pulse processing stage.
	struct RangePulseProduct
	{
		Eigen::MatrixXcd samples;
	};

	// Update the radar module from the current radar and target kinematics.
	std::optional<RangePulseProduct> range_doppler_map(RadarModule &radar,
		const KinematicStateECI &radar_kinematics,
		const KinematicStateECI &target_kinematics,
		double target_rcs_dbsm);

	// Convert one completed domain product into a one-frame analysis series.
	GridSeries2D make_noisy_range_doppler_series(const RangePulseProduct &product,
		const RadarParams &radar,
		int radar_entity_id,
		double time_s);

} // namespace apogee
