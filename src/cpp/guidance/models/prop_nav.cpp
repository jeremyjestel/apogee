#include "guidance/models/prop_nav.hpp"

#include <cmath>

#include "core/entity.hpp"

namespace apogee
{
	Vec3 prop_nav(const Entity &entity, const Entity &target)
	{
		const Vec3 relative_position = target.kinematics.pos_m - entity.kinematics.pos_m;
		const double range_squared = relative_position.squaredNorm();
		if (range_squared == 0.0) return Vec3::Zero();

		const Vec3 relative_velocity = target.kinematics.vel_mps - entity.kinematics.vel_mps;
		const Vec3 r_hat = relative_position / std::sqrt(range_squared);
		const double closing_velocity = -relative_velocity.dot(r_hat);
		const Vec3 angular_rate = relative_position.cross(relative_velocity) / range_squared;
        double N = 3.0;
		return N * closing_velocity * angular_rate.cross(r_hat);
	}
}
