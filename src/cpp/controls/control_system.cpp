#include "controls/control_system.hpp"

#include <cmath>

#include "core/entity.hpp"

namespace apogee
{
	void controls_update(std::vector<Entity> &entities, double dt_s)
	{
		for (auto &entity : entities)
		{
			auto &control = entity.controls;
			const double alpha = control.time_constant_s > 0.0 ? -std::expm1(-dt_s / control.time_constant_s) : 1.0;
			control.accel_actual += alpha * (entity.guidance.accel_command - control.accel_actual);
		}
	}
}
