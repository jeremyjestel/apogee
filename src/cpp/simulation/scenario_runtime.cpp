#include "simulation/scenario_runtime.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>

#include "motion/motion_system.hpp"

namespace apogee
{
	namespace
	{
		Entity instantiate(const EntityDefinition &definition)
		{
			Entity entity{ .id = definition.id,
				.key = definition.key,
				.display_name = definition.display_name,
				.type = definition.type,
				.team = definition.team,
				.kinematics = definition.ground		 ? definition.ground->initial_kinematics()
							  : definition.satellite ? definition.satellite->initial_kinematics()
							  : definition.initial_pursuit
								  ? definition.initial_pursuit->initial_kinematics()
								  : definition.initial_kinematics,
				.motion_type = definition.motion_type,
				.mass = definition.mass,
				.drag_coeff = definition.drag_coeff,
				.area_m2 = definition.area_m2,
				.radar_signature_dbsm = definition.radar_signature_dbsm };
			if (definition.radar)
			{
				entity.radars.push_back(
					RadarComponent{ .params = finalize_radar_params(*definition.radar) });
			}
			return entity;
		}

	}

	Entity &require_entity(std::vector<Entity> &entities, const std::string &key)
	{
		const auto match = std::find_if(entities.begin(),
			entities.end(),
			[&](const Entity &entity) { return entity.key == key; });
		if (match == entities.end())
		{
			throw std::invalid_argument("Scenario is missing entity: " + key);
		}
		return *match;
	}

	std::vector<Entity> instantiate_entities(const ScenarioParams &params)
	{
		std::vector<Entity> entities;
		entities.reserve(params.entities.size());
		for (const EntityDefinition &definition : params.entities)
		{
			entities.push_back(instantiate(definition));
		}
		return entities;
	}

	void initialize_pursuits(const ScenarioParams &params, std::vector<Entity> &entities)
	{
		for (std::size_t index = 0; index < params.entities.size(); ++index)
		{
			const EntityDefinition &definition = params.entities[index];
			if (!definition.initial_pursuit)
			{
				continue;
			}

			Entity &entity = entities[index];
			const Entity &target = require_entity(entities, definition.initial_pursuit->target_key);
			const double dx = target.kinematics.pos_m.x() - entity.kinematics.pos_m.x();
			const double dy = target.kinematics.pos_m.y() - entity.kinematics.pos_m.y();
			const double dz = target.kinematics.pos_m.z() - entity.kinematics.pos_m.z();
			const double distance_m = std::hypot(dx, dy, dz);
			if (distance_m == 0.0)
			{
				throw std::invalid_argument(
					"Initial pursuit entity and target cannot share a position.");
			}

			const double scale = definition.initial_pursuit->speed_mps / distance_m;
			entity.kinematics.vel_mps = Vec3{ dx * scale, dy * scale, dz * scale };
			entity.kinematics.accel_mps2 = Vec3::Zero();
		}
	}

	void advance_entities(std::vector<Entity> &entities, double dt_s)
	{
		motion_step(entities, dt_s);
	}
}
