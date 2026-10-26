#pragma once

#include <string>
#include <unordered_map>
#include <variant>
#include <vector>

#include "core/entity.hpp"
#include "core/result.hpp"

namespace apogee
{
	// Records the data described by entities and their attached components.
	class Logger
	{
	  public:
		Logger(const std::vector<Entity> &entities, Result &result);
		void log(const std::vector<Entity> &entities, double time_s);

	  private:
		struct Field
		{
			int entity_id;
			std::string system, key, name, unit, frame, group;
		};
		using Value = std::variant<double, Vec3, std::string, ArraySample>;
		struct Sample
		{
			Field field;
			Value value;
		};
		struct Series
		{
			std::size_t kind, index;
		};

		static std::vector<Sample> capture(const std::vector<Entity> &entities);
		static std::string identity(const Field &field);
		void register_entities(const std::vector<Entity> &entities);
		void register_fields(const std::vector<Sample> &samples);

		Result &result_;
		std::size_t simulation_time_axis_;
		std::unordered_map<int, std::size_t> entities_;
		std::unordered_map<std::string, Series> series_;
	};

} // namespace apogee
