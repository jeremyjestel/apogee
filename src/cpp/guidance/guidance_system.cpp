#include "guidance/guidance_system.hpp"
#include "math/geometry/los_occluded.hpp"

#include "math/constants.hpp"
#include "core/entity.hpp"
#include "guidance/models/prop_nav.hpp"
#include "guidance/models/point_nav.hpp"
#include "motion/models/gravity.hpp"

namespace apogee
{
	void guidance_commands(std::vector<Entity> &entities, std::mt19937 &)
	{
		for (auto &entity : entities)
		{
			entity.guidance.accel_command.setZero();
			if (!entity.active)
				continue;
			if ((entity.type == "missile" || entity.type == "interceptor") && entity.guidance.target_index && *entity.guidance.target_index < entities.size())
			{
				const Entity &target = entities[*entity.guidance.target_index];
				if (!target.active)
					continue;
				if (has_line_of_sight(entity.kinematics.pos_m, target.kinematics.pos_m))
				{
					entity.guidance.accel_command = prop_nav(entity, target);
				}
				else
				{
					entity.guidance.accel_command = point_nav(entity, target);
				}
				entity.guidance.accel_command -= gravity(entity.kinematics.pos_m, entity.mass);
			}
		}
	}
}
