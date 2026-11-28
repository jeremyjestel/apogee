#pragma once

#include <string>

#include "math/types.hpp"

namespace apogee
{
	enum class MeasurementKind
	{
		RangeAzimuthElevation,
		AzimuthElevation
	};

	// A sensor observation submitted to the owning entity's shared estimator.
	// It contains no ground-truth target ID or preassigned track ID.
	struct Detection
	{
		// Unique sensor identity within the observing entity, e.g. "radar/front".
		std::string sensor_id;
		double time_s = 0.0;
		MeasurementKind kind = MeasurementKind::RangeAzimuthElevation;

		// RangeAzimuthElevation: [range_m, azimuth_rad, elevation_rad], size 3.
		// AzimuthElevation: [azimuth_rad, elevation_rad], size 2 (e.g. EO/IR).
		// Angles use atan2(y, x) and atan2(z, hypot(x, y)) in the sensor frame.
		VecX value;
		// R belongs to this observation; its dimensions match value.size().
		// Entries use the corresponding measurement units, including cross terms.
		MatX covariance;

		// Sensor pose at measurement time. Rotation maps sensor vectors into ECI.
		Vec3 sensor_position_m = Vec3::Zero();
		Mat3 sensor_to_eci = Mat3::Identity();
	};
}
