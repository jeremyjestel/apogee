#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

#include "logging/logging.hpp"

namespace
{
	using namespace apogee;

	void check(bool condition, const std::string &message)
	{
		if (!condition)
		{
			throw std::runtime_error(message);
		}
	}

	template <typename Series>
	const Series &find(const std::vector<Series> &series,
		int entity_id, const std::string &system, const std::string &key)
	{
		const auto item = std::find_if(series.begin(), series.end(), [&](const Series &value)
			{ return value.entity_id == entity_id && value.system == system && value.key == key; });
		check(item != series.end(), "Missing series: " + system + "/" + key);
		return *item;
	}

	template <typename Function>
	void check_invalid(Function function, const std::string &message)
	{
		try
		{
			function();
		}
		catch (const std::invalid_argument &)
		{
			return;
		}
		throw std::runtime_error(message);
	}

	Entity entity(int id)
	{
		Entity value;
		value.id = id;
		value.key = "entity_" + std::to_string(id);
		value.display_name = "Entity " + std::to_string(id);
		value.kinematics.pos_m = Vec3{ static_cast<double>(id), 2.0, 3.0 };
		value.kinematics.vel_mps = Vec3{ 3.0, 4.0, 0.0 };
		return value;
	}

	RadarComponent radar(const std::string &name, double range)
	{
		RadarComponent value;
		value.name = name;
		value.params.frequency_hz = 9.0e9;
		value.params.pulse_num = 7;
		value.state.target_range_m = range;
		value.pointing_vec = Vec3{ 0.0, 1.0, 0.0 };
		return value;
	}

	void test_entity_component_histories()
	{
		std::vector<Entity> entities{ entity(10), entity(20) };
		entities[0].radars = { radar("search", 100.0), radar("track", 200.0) };
		entities[0].motion_type = MotionType::EarthFixed;
		entities[0].mass = 12.5;
		entities[0].radars[0].state.enabled = false;
		entities[0].radars[0].state.range_pulse_map.resize(2, 2);
		entities[0].radars[0].state.range_pulse_map << Complex{ 1.0, 2.0 }, Complex{ 3.0, 4.0 },
			Complex{ 5.0, 6.0 }, Complex{ 7.0, 8.0 };
		// Target references must preserve identity rather than recursively logging snapshots.
		entities[0].radars[0].targets = { entities[1] };
		entities[0].radars[0].targets[0].radars = { radar("nested", 123.0) };

		Result result;
		Logger logger(entities, result);
		check(result.axes.size() == 1 && result.axes[0].values.empty(),
			"Constructing the logger must register schema without recording a timestep.");
		logger.log(entities, 0.0);

		check(find(result.scalars, 10, "entity", "mass").values[0] == 12.5,
			"Entity-wide scalar attributes must be recorded.");
		check(find(result.scalars, 10, "entity", "motion_type").values[0] ==
			static_cast<double>(MotionType::EarthFixed), "Enum state must retain its numeric value.");
		check(find(result.scalars, 10, "kinematics", "speed").values[0] == 5.0,
			"Derived speed must remain available alongside the kinematic vectors.");
		check(find(result.scalars, 10, "radars", "name:search/params/frequency_hz").values[0] == 9.0e9 &&
			find(result.scalars, 10, "radars", "name:search/params/pulse_num").values[0] == 7.0 &&
			find(result.scalars, 10, "radars", "name:search/state/enabled").values[0] == 0.0,
			"Nested parameters, integral fields, and booleans must be recorded.");
		check(find(result.vectors, 10, "radars", "name:search/pointing_vec").values[0] == Vec3::UnitY(),
			"Component vectors must be recorded without being treated as entity positions.");
		const auto &matrix = find(result.arrays, 10, "radars", "name:search/state/range_pulse_map").values[0];
		check(matrix && matrix->rows == 2 && matrix->columns == 2 &&
			matrix->values == std::vector<Complex>{ {1, 2}, {3, 4}, {5, 6}, {7, 8} },
			"Complex matrices must retain row-major values and their own shape.");
		const auto &targets = find(result.arrays, 10, "radars", "name:search/targets").values[0];
		check(targets && targets->rows == 1 && targets->columns == 1 && targets->values[0] == Complex{ 20, 0 },
			"Target collections must log IDs only.");
		check(std::none_of(result.scalars.begin(), result.scalars.end(), [](const ScalarSeries &series)
			{ return series.key.find("nested") != std::string::npos; }),
			"Logging target references must not expand copied entity state.");

		std::swap(entities[0], entities[1]);
		Entity &owner = entities[1];
		std::swap(owner.radars[0], owner.radars[1]);
		owner.radars[0].state.target_range_m = 201.0;
		owner.radars[1].state.target_range_m = 101.0;
		owner.radars[1].state.enabled = true;
		owner.radars[1].state.range_pulse_map.resize(1, 3);
		owner.radars[1].state.range_pulse_map << Complex{ 9, -1 }, Complex{ 10, -2 }, Complex{ 11, -3 };
		owner.radars[1].targets.clear();
		owner.display_name = "Renamed entity";
		logger.log(entities, 0.5);
		check(find(result.scalars, 10, "radars", "name:search/state/target_range_m").values ==
			std::vector<double>{ 100.0, 101.0 } &&
			find(result.scalars, 10, "radars", "name:track/state/target_range_m").values ==
			std::vector<double>{ 200.0, 201.0 }, "Entity and named-component order must not change series identity.");
		const auto &resized = find(result.arrays, 10, "radars", "name:search/state/range_pulse_map").values[1];
		check(resized && resized->rows == 1 && resized->columns == 3 && resized->values[2] == Complex{ 11, -3 },
			"Each timestep must preserve its matrix dimensions and imaginary values.");
		const auto &empty_targets = find(result.arrays, 10, "radars", "name:search/targets").values[1];
		check(empty_targets && empty_targets->rows == 0 && empty_targets->columns == 1 && empty_targets->values.empty(),
			"An empty collection is a present empty sample.");
		check(find(result.texts, 10, "entity", "display_name").values[1] == "Renamed entity",
			"Text attributes must be sampled rather than kept only as initial metadata.");

		owner.radars[1].state.range_pulse_map.resize(0, 0);
		owner.radars.push_back(radar("late", 300.0));
		entities.push_back(entity(30));
		logger.log(entities, 1.0);
		const auto &late = find(result.scalars, 10, "radars", "name:late/state/target_range_m").values;
		check(late.size() == 3 && std::isnan(late[0]) && std::isnan(late[1]) && late[2] == 300.0,
			"Components introduced during a run must backfill earlier timesteps.");
		const auto &late_entity = find(result.vectors, 30, "kinematics", "position").values;
		check(late_entity.size() == 3 && late_entity[0].array().isNaN().all() && late_entity[2].x() == 30.0,
			"New entity histories must align with the global simulation axis.");
		const auto &empty_matrix = find(result.arrays, 10, "radars", "name:search/state/range_pulse_map").values[2];
		check(empty_matrix && empty_matrix->rows == 0 && empty_matrix->columns == 0 && empty_matrix->values.empty(),
			"An empty matrix must remain distinct from an absent component.");

		entities.erase(entities.begin() + 1);
		logger.log(entities, 1.5);
		check(std::isnan(find(result.scalars, 10, "entity", "mass").values[3]) &&
			find(result.vectors, 10, "kinematics", "position").values[3].array().isNaN().all() &&
			!find(result.texts, 10, "entity", "display_name").values[3] &&
			!find(result.arrays, 10, "radars", "name:search/state/range_pulse_map").values[3],
			"Removed entities must leave missing samples in every data representation.");
		check(result.axes[0].values == std::vector<double>{ 0, 0.5, 1, 1.5 },
			"Every logged snapshot must share one global simulation timeline.");
		const auto aligned = [&](const auto &series)
			{ return std::all_of(series.begin(), series.end(), [](const auto &value) { return value.values.size() == 4; }); };
		check(aligned(result.scalars) && aligned(result.vectors) && aligned(result.texts) && aligned(result.arrays),
			"All registered histories must have exactly one sample per timestep.");
	}

	void test_component_presence_and_names()
	{
		std::vector<Entity> entities{ entity(1) };
		entities[0].radars = { radar("a/b.%:", 10.0), radar("", 20.0), radar("", 30.0) };
		Result result;
		Logger logger(entities, result);
		logger.log(entities, 0.0);
		check(find(result.scalars, 1, "radars", "name:a%2Fb%2E%25%3A/state/target_range_m").values[0] == 10.0,
			"Component names must escape reserved path characters without losing identity.");
		check(find(result.scalars, 1, "radars", "index:1/state/target_range_m").values[0] == 20.0 &&
			find(result.scalars, 1, "radars", "index:2/state/target_range_m").values[0] == 30.0,
			"Unnamed components must have distinct slot identities.");
		entities[0].radars.clear();
		logger.log(entities, 1.0);
		check(std::isnan(find(result.scalars, 1, "radars", "index:1/state/target_range_m").values[1]) &&
			!find(result.texts, 1, "radars", "index:1/name").values[1] &&
			!find(result.arrays, 1, "radars", "index:1/targets").values[1] &&
			find(result.vectors, 1, "kinematics", "position").values[1].x() == 1.0,
			"Removing components must leave missing component samples while the owner continues.");
		entities[0].radars.push_back(radar("a/b.%:", 11.0));
		logger.log(entities, 2.0);
		const auto &resumed = find(result.scalars, 1, "radars", "name:a%2Fb%2E%25%3A/state/target_range_m").values;
		check(resumed.size() == 3 && resumed[0] == 10.0 && std::isnan(resumed[1]) && resumed[2] == 11.0,
			"A returning named component must continue its original history.");
	}

	void test_invalid_identities_and_times()
	{
		Result duplicate_result;
		check_invalid([&] { Logger duplicate({ entity(1), entity(1) }, duplicate_result); },
			"Duplicate entity IDs must be rejected.");
		Entity duplicate_names = entity(1);
		duplicate_names.radars = { radar("same", 1.0), radar("same", 2.0) };
		Result component_result;
		check_invalid([&] { Logger duplicate({ duplicate_names }, component_result); },
			"Duplicate named components must be rejected.");

		std::vector<Entity> entities{ entity(1) };
		Result result;
		Logger logger(entities, result);
		logger.log(entities, 0.0);
		check_invalid([&] { logger.log({ entity(1), entity(1) }, 1.0); },
			"Duplicate IDs introduced later must be rejected.");
		check_invalid([&] { logger.log({ duplicate_names }, 1.0); },
			"Duplicate component names introduced later must be rejected.");
		check_invalid([&] { logger.log(entities, std::numeric_limits<double>::quiet_NaN()); },
			"The simulation timeline must reject non-finite sample times.");
		check_invalid([&] { logger.log(entities, 0.0); },
			"Duplicate sample times must be rejected.");
		check_invalid([&] { logger.log(entities, -1.0); },
			"The simulation timeline must remain increasing.");
		check(result.axes[0].values.size() == 1, "Rejected snapshots must not append partial timesteps.");
		logger.log(entities, 1.0);
		check(result.axes[0].values.size() == 2, "Valid logging must resume after a rejected snapshot.");
	}

	void test_rejected_entity_registration()
	{
		Entity collision = entity(3);
		collision.key = entity(1).key;
		Result invalid_initial_result;
		check_invalid([&] { Logger duplicate({ entity(1), collision }, invalid_initial_result); },
			"Duplicate entity keys must be rejected during construction.");
		check(invalid_initial_result.entities.empty() && invalid_initial_result.axes.empty() &&
			invalid_initial_result.scalars.empty() && invalid_initial_result.vectors.empty() &&
			invalid_initial_result.texts.empty() && invalid_initial_result.arrays.empty(),
			"A rejected constructor must leave the empty result unchanged.");

		Result result;
		Logger logger({ entity(1) }, result);
		logger.log({ entity(1) }, 0.0);
		check_invalid([&] { logger.log({ entity(1), entity(2), collision }, 1.0); },
			"A new entity key must not collide with an existing entity key.");
		check(result.entities.size() == 1 && result.entities[0].id == 1 &&
			result.axes[0].values == std::vector<double>{ 0.0 },
			"A rejected snapshot must not register earlier new entities or append time.");
		logger.log({ entity(1), entity(2) }, 1.0);
		const auto &position = find(result.vectors, 2, "kinematics", "position").values;
		check(result.entities.size() == 2 && result.axes[0].values == std::vector<double>{ 0.0, 1.0 } &&
			position.size() == 2 && position[0].array().isNaN().all() && position[1].x() == 2.0,
			"Retrying a valid entity registration must backfill earlier samples and align the new sample.");
	}
}

int main()
{
	try
	{
		test_entity_component_histories();
		test_component_presence_and_names();
		test_invalid_identities_and_times();
		test_rejected_entity_registration();
		std::cout << "C++ logging checks passed.\n";
		return 0;
	}
	catch (const std::exception &error)
	{
		std::cerr << error.what() << '\n';
		return 1;
	}
}
