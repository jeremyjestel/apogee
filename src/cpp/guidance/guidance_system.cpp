#include "guidance/guidance_system.hpp"

#include "core/entity.hpp"
#include "guidance/models/prop_nav.hpp"

namespace apogee
{
	void guidance_commands(std::vector<Entity> &entities, std::mt19937 &)
	{
		for (auto &entity : entities)
		{
			entity.guidance.accel_command.setZero();
			if ((entity.type == "missile" || entity.type == "interceptor") &&
				entity.guidance.target_index && *entity.guidance.target_index < entities.size())
			{
				entity.guidance.accel_command = prop_nav(entity, entities[*entity.guidance.target_index]);
			}
		}
	}
}
