#pragma once
#include "math/types.hpp"

namespace apogee
{
	struct KinematicStateECI
	{
		Vec3 pos_m = Vec3::Zero();
		Vec3 vel_mps = Vec3::Zero();
		Vec3 accel_mps2 = Vec3::Zero();
	};
}
