#pragma once

#include "core/data_fields.hpp"
#include "math/types.hpp"

namespace apogee
{
	struct KinematicStateECI
	{
		Vec3 pos_m = Vec3::Zero();
		Vec3 vel_mps = Vec3::Zero();
		Vec3 accel_mps2 = Vec3::Zero();

		static constexpr auto data_fields()
		{
			return std::tuple{ data_field("position", &KinematicStateECI::pos_m, "Position", "m", "eci"),
				data_field("velocity", &KinematicStateECI::vel_mps, "Velocity", "m/s", "eci"),
				data_field("acceleration", &KinematicStateECI::accel_mps2, "Acceleration", "m/s^2", "eci"),
				data_field("speed", [](const KinematicStateECI &state) { return state.vel_mps.norm(); }, "Speed", "m/s") };
		}
	};

	enum class MotionType {
		EarthFixed,
		FreeFlight
	};

	// Coordinate transforms derive this state from the authoritative ECI state.
	struct KinematicStateECEF
	{
		Vec3 pos_m = Vec3::Zero();
		Vec3 vel_mps = Vec3::Zero();
		Vec3 accel_mps2 = Vec3::Zero();

		static constexpr auto data_fields()
		{
			return std::tuple{ data_field("position", &KinematicStateECEF::pos_m, "Position", "m", "ecef"),
				data_field("velocity", &KinematicStateECEF::vel_mps, "Velocity", "m/s", "ecef"),
				data_field("acceleration", &KinematicStateECEF::accel_mps2, "Acceleration", "m/s^2", "ecef"),
				data_field("speed", [](const KinematicStateECEF &state) { return state.vel_mps.norm(); }, "Speed", "m/s") };
		}
	};

}
