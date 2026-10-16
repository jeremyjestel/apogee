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

	enum class MotionType {
		EarthFixed,
		FreeFlight
	};

	// struct KinematicStateECEF  //Should make this a dervied function call so only updating ECI, also wouldnt vel and accel be the same
	// {
	// 	Vec3 pos_m = Vec3::Zero();
	// 	Vec3 vel_mps = Vec3::Zero();
	// 	Vec3 accel_mps2 = Vec3::Zero();
	
}
