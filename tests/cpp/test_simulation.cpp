#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

#include "run_sim.hpp"
#include "controls/control_system.hpp"
#include "guidance/guidance_system.hpp"
#include "guidance/models/prop_nav.hpp"
#include "math/coords.hpp"
#include "logging/logging.hpp"
#include "scenarios/default_scenario.hpp"
#include "motion/models/ground_motion.hpp"
#include "motion/motion_system.hpp"
#include "sensors/radar/models/radar_processing.hpp"
#include "sensors/radar/models/radar_returns.hpp"
#include "simulation/scenario_runtime.hpp"

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
	const Series &find(const std::vector<Series> &series, int entity_id,
		const std::string &system, const std::string &key)
	{
		const auto item = std::find_if(series.begin(), series.end(), [&](const Series &value)
			{ return value.entity_id == entity_id && value.system == system && value.key == key; });
		check(item != series.end(), "Missing series: " + system + "/" + key);
		return *item;
	}

	const VectorSeries3 &position(const Result &result, int entity_id)
	{
		for (const auto &series : result.vectors)
		{
			if (series.entity_id == entity_id && series.key == "position")
			{
				return series;
			}
		}
		throw std::runtime_error("Missing position series.");
	}

	void test_coordinate_conversions()
	{
		const double radius_m = constants::earth_radius_m;
		const double quarter_turn_s = constants::pi / (2.0 * constants::earth_rotation_rate_rad_s);
		const double tolerance = 1e-6;
		check((lla2ecef(0.0, 0.0, 0.0) - Vec3{ radius_m, 0.0, 0.0 }).norm() < tolerance,
			"Zero latitude/longitude must lie on ECEF +X.");
		check((lla2ecef(0.0, 90.0, 0.0) - Vec3{ 0.0, radius_m, 0.0 }).norm() < tolerance,
			"East longitude must point toward ECEF +Y.");
		check((ecef2lla(Vec3{ 0.0, 0.0, radius_m + 100.0 }) -
			Vec3{ 90.0, 0.0, 100.0 }).norm() < tolerance,
			"The north pole must return latitude 90, longitude zero, and altitude above the surface.");
		check((ecef2eci(Vec3{ radius_m, 0.0, 0.0 }, quarter_turn_s) -
			Vec3{ 0.0, radius_m, 0.0 }).norm() < tolerance,
			"Earth-fixed +X must rotate toward inertial +Y.");
		check((eci2ecef(Vec3{ radius_m, 0.0, 0.0 }, quarter_turn_s) -
			Vec3{ 0.0, -radius_m, 0.0 }).norm() < tolerance,
			"Inertial +X must rotate toward Earth-fixed -Y.");
		check((lla2eci(0.0, 0.0, 100.0, quarter_turn_s) -
			Vec3{ 0.0, radius_m + 100.0, 0.0 }).norm() < tolerance,
			"LLA-to-ECI must include elapsed Earth rotation.");
		check((eci2lla(Vec3{ 0.0, radius_m + 100.0, 0.0 }, quarter_turn_s) -
			Vec3{ 0.0, 0.0, 100.0 }).norm() < tolerance,
			"ECI-to-LLA must remove elapsed Earth rotation.");

		const std::array<Vec3, 5> locations{ Vec3{ 38.5, -76.2, 1'000.0 },
			Vec3{ -42.0, 179.9, -250.0 }, Vec3{ 0.0, -180.0, 0.0 },
			Vec3{ 90.0, 0.0, 10.0 }, Vec3{ -90.0, 0.0, 10'000.0 } };
		for (const Vec3 &lla : locations)
		{
			const Vec3 ecef = lla2ecef(lla.x(), lla.y(), lla.z());
			check((ecef2lla(ecef) - lla).norm() < tolerance,
				"ECEF/LLA round trip changed the location.");
			check((ecef2eci(ecef, 0.0) - ecef).norm() < tolerance &&
				(eci2ecef(ecef, 0.0) - ecef).norm() < tolerance,
				"ECEF and ECI axes must align at simulation start.");
			for (double time_s : { 0.0, 12'345.6, -86'400.0 })
			{
				const Vec3 eci = lla2eci(lla.x(), lla.y(), lla.z(), time_s);
				check((eci2ecef(eci, time_s) - ecef).norm() < tolerance,
					"ECEF/ECI round trip changed the position.");
				check((eci2lla(eci, time_s) - lla).norm() < tolerance,
					"ECI/LLA round trip changed the location.");
			}
		}

		bool rejected_center = false;
		try
		{
			ecef2lla(Vec3::Zero());
		}
		catch (const std::invalid_argument &)
		{
			rejected_center = true;
		}
		check(rejected_center, "Earth's center has no defined latitude/longitude.");
	}

	void test_simulation_contract()
	{
		auto params = make_default_scenario();
		params.simulation.duration_s = 0.2;
		const Result result = run_sim(params);
		check(result.entities.size() == 4,
			"Default scenario must retain all four entities.");
		check(result.axes.size() == 1 && result.axes.front().values == std::vector<double>{ 0.0, 0.1, 0.2 },
			"Simulation sampling convention changed.");
		const auto &raw = find(result.arrays, 1, "radars", "index:0/state/range_pulse_map");
		const auto &processed = find(result.arrays, 1, "radars", "index:0/state/range_doppler_map");
		check(raw.values.size() == 3 && processed.values.size() == 3 &&
			raw.values[0]->rows == processed.values[0]->rows &&
			raw.values[0]->columns * 4 == processed.values[0]->columns &&
			processed.values[0]->columns == 64,
			"Radar raw and processed complex maps must share the simulation timeline and layout.");

		auto ground = params.entities.front().ground->initial_kinematics();
		check(position(result, 1).values.front() == ground.pos_m,
			"Initial positions must be logged before motion.");
		advance_ground(ground, params.simulation.dt_s);
		check(position(result, 1).values.at(1) == ground.pos_m,
			"Ground motion sequence changed.");

		for (int entity_id : { 3, 4 })
		{
			const Vec3 command = find(result.vectors, entity_id, "guidance", "accel_command").values.front();
			const Vec3 actual = find(result.vectors, entity_id, "controls", "accel_actual").values.front();
			const auto &velocity = find(result.vectors, entity_id, "kinematics", "velocity").values;
			check(command.norm() > 0.0 &&
				(actual - (1.0 - std::exp(-1.0)) * command).norm() < 1e-9,
				"Simulation steps must run guidance and controls for both pursuit entities.");
			check((velocity[1] - velocity[0] - actual * params.simulation.dt_s).norm() < 1e-9,
				"Motion must apply the control output during the same simulation step.");
		}

		check(find(result.scalars, 1, "radars", "index:0/params/pulse_width_us").values ==
			std::vector<double>(3, params.entities.front().radar->pw_us),
			"Finalized radar parameters must be logged with the component state.");

		const Result repeated = run_sim(params);
		check(raw.values[0]->values ==
			find(repeated.arrays, 1, "radars", raw.key).values[0]->values &&
			processed.values[0]->values ==
			find(repeated.arrays, 1, "radars", processed.key).values[0]->values,
			"Fresh simulations must reproduce seeded radar returns and processing.");
		for (const auto &series : result.vectors)
		{
			for (const auto &other : repeated.vectors)
			{
				if (series.entity_id == other.entity_id && series.key == other.key)
				{
					check(series.values == other.values, "Runtime state leaked between simulations.");
				}
			}
		}
		params.simulation.duration_s = 0.0;
		check(run_sim(params).axes.front().values == std::vector<double>{ 0.0 },
			"Zero-duration simulation must retain the initial sample.");
	}

	void test_entity_logger()
	{
		std::vector<Entity> entities{
			Entity{ .id = 41, .key = "first", .display_name = "First", .type = "missile",
				.team = "blue", .kinematics = KinematicStateECI{
					Vec3{ 1.0, 2.0, 3.0 }, Vec3{ 3.0, 4.0, 0.0 }, Vec3{ 1.0, 0.0, 0.0 } } },
			Entity{ .id = 7, .key = "second", .display_name = "Second", .type = "satellite",
				.team = "red", .kinematics = KinematicStateECI{
					Vec3{ 10.0, 20.0, 30.0 }, Vec3{ 0.0, 0.0, 5.0 }, Vec3::Zero() } }
		};
		Result result;
		Logger logger(entities, result);
		auto vector_count = [&](const std::string &system)
		{
			return std::count_if(result.vectors.begin(), result.vectors.end(),
				[&](const auto &series) { return series.system == system; });
		};
		check(result.entities.size() == 2 && vector_count("kinematics") == 6 &&
				vector_count("guidance") == 2 && vector_count("controls") == 2 &&
				result.axes.front().values.empty(),
			"Logger must create empty histories before the first step.");
		check(result.entities.front().id == 41 && result.entities.front().key == "first" &&
				result.entities.front().display_name == "First" &&
				result.entities.front().type == "missile" && result.entities.front().team == "blue",
			"Logger must preserve entity descriptors.");
		logger.log(entities, 0.0);

		entities[0].kinematics = KinematicStateECI{
			Vec3{ 4.0, 5.0, 6.0 }, Vec3{ 0.0, 0.0, 12.0 }, Vec3{ 0.0, 1.0, 0.0 } };
		entities[0].guidance.accel_command = Vec3{ 0.0, 2.0, 3.0 };
		entities[0].guidance.guidance_gain = 0.75;
		entities[0].controls.accel_actual = Vec3{ 0.0, 1.0, 1.5 };
		entities[1].kinematics.pos_m = Vec3{ 40.0, 50.0, 60.0 };
		const std::vector<Entity> reordered{ entities[1], entities[0] };
		logger.log(reordered, 0.5);

		check(result.axes.front().values == std::vector<double>{ 0.0, 0.5 },
			"Logger must append one timestamp for the entire entity list.");
		check(position(result, 41).values ==
				std::vector<Vec3>{ Vec3{ 1.0, 2.0, 3.0 }, Vec3{ 4.0, 5.0, 6.0 } } &&
				position(result, 7).values ==
				std::vector<Vec3>{ Vec3{ 10.0, 20.0, 30.0 }, Vec3{ 40.0, 50.0, 60.0 } },
			"Logger must associate current samples with entity IDs when the list is reordered.");
		check(find(result.vectors, 41, "kinematics", "velocity").values.back() == entities[0].kinematics.vel_mps &&
				find(result.vectors, 41, "kinematics", "acceleration").values.back() == entities[0].kinematics.accel_mps2 &&
				find(result.scalars, 41, "kinematics", "speed").values == std::vector<double>{ 5.0, 12.0 } &&
				find(result.scalars, 7, "kinematics", "speed").values == std::vector<double>{ 5.0, 5.0 },
			"Logger must capture current velocity, acceleration, and speed.");
		check(find(result.vectors, 41, "guidance", "accel_command").values.back() ==
				entities[0].guidance.accel_command &&
				find(result.vectors, 41, "controls", "accel_actual").values.back() ==
				entities[0].controls.accel_actual,
			"Logger must capture guidance commands and control outputs.");
		check(find(result.scalars, 41, "guidance", "guidance_gain").values ==
			std::vector<double>{ 0.5, 0.75 }, "Logger must capture the current guidance gain.");
	}

	void test_guidance_and_controls()
	{
		std::vector<Entity> entities(3);
		entities[0].type = "missile";
		entities[0].kinematics.pos_m = Vec3{ constants::earth_radius_m + 100'000.0, 0.0, 0.0 };
		entities[0].kinematics.vel_mps = Vec3{ 10.0, 0.0, 0.0 };
		entities[0].guidance.target_index = 1;
		entities[0].controls.time_constant_s = 0.1;
		entities[1].type = "satellite";
		entities[1].kinematics.pos_m = entities[0].kinematics.pos_m + Vec3{ 100.0, 0.0, 0.0 };
		entities[1].kinematics.vel_mps = Vec3{ 0.0, 2.0, 0.0 };
		entities[1].guidance.target_index = 0;
		entities[1].guidance.accel_command = Vec3::Ones();
		entities[2].type = "interceptor";
		entities[2].kinematics = entities[0].kinematics;
		entities[2].guidance.target_index = 1;
		const Vec3 first_command{ 0.0, 0.6, 0.0 };
		check((prop_nav(entities[0], entities[1]) - first_command).norm() < 1e-12,
			"Proportional navigation must use target-relative velocity.");
		std::mt19937 rng(1234);
		guidance_commands(entities, rng);
		check((entities[0].guidance.accel_command - first_command).norm() < 1e-12 &&
				(entities[2].guidance.accel_command - first_command).norm() < 1e-12 &&
				entities[1].guidance.accel_command.isZero(),
			"Only missiles and interceptors must receive guidance commands.");

		controls_update(entities, 0.1);
		check((entities[0].controls.accel_actual -
				(1.0 - std::exp(-1.0)) * first_command).norm() < 1e-12,
			"Controls must apply the configured first-order acceleration lag.");
		controls_update(entities, 0.1);
		check((entities[0].controls.accel_actual -
				(1.0 - std::exp(-2.0)) * first_command).norm() < 1e-12,
			"Controls must retain actual acceleration between updates.");

		entities[1].kinematics.vel_mps = Vec3{ 0.0, -3.0, 4.0 };
		guidance_commands(entities, rng);
		check((entities[0].guidance.accel_command - Vec3{ 0.0, -0.9, 1.2 }).norm() < 1e-12,
			"Guidance must use the target's current state on every update.");
		entities[0].controls.time_constant_s = 0.0;
		controls_update(entities, 0.1);
		check((entities[0].controls.accel_actual - entities[0].guidance.accel_command).norm() < 1e-12,
			"A zero control time constant must apply the command immediately.");
		entities[1].kinematics.pos_m = entities[0].kinematics.pos_m;
		check(prop_nav(entities[0], entities[1]).isZero(),
			"Coincident target positions must produce a finite zero command.");
		entities[0].guidance.target_index.reset();
		entities[2].guidance.target_index.reset();
		guidance_commands(entities, rng);
		check(entities[0].guidance.accel_command.isZero(),
			"Removing a target must clear the previous guidance command.");
	}

	void test_configured_guidance_targets()
	{
		auto params = make_default_scenario();
		params.entities[2].initial_pursuit->guidance_gain = 0.75;
		auto entities = instantiate_entities(params);
		check(require_entity(entities, "red_missile").guidance.guidance_gain == 0.75,
			"Configured guidance gain must be copied into fresh runtime state.");
		auto target_key = [&](const std::string &key) -> const std::string &
		{
			const Entity &entity = require_entity(entities, key);
			check(entity.guidance.target_index.has_value(), "Missing configured guidance target.");
			return entities.at(*entity.guidance.target_index).key;
		};
		check(target_key("red_missile") == "blue_satellite" &&
				target_key("blue_interceptor") == "red_missile" &&
				!require_entity(entities, "blue_radar").guidance.target_index &&
				!require_entity(entities, "blue_satellite").guidance.target_index,
			"Default guidance targets must belong only to missiles and interceptors.");

		auto added_missile = params.entities[2];
		added_missile.id = 5;
		added_missile.key = "added_missile";
		added_missile.initial_pursuit->target_key = "blue_interceptor";
		auto added_interceptor = params.entities[3];
		added_interceptor.id = 6;
		added_interceptor.key = "added_interceptor";
		added_interceptor.initial_pursuit->target_key = "added_missile";
		params.entities.push_back(added_missile);
		params.entities.push_back(added_interceptor);
		std::reverse(params.entities.begin(), params.entities.end());
		entities = instantiate_entities(params);
		check(target_key("added_missile") == "blue_interceptor" &&
				target_key("added_interceptor") == "added_missile" &&
				target_key("red_missile") == "blue_satellite" &&
				target_key("blue_interceptor") == "red_missile",
			"Manual targets must resolve by key independently of configuration order.");
		initialize_pursuits(params, entities);
		const Entity &interceptor = require_entity(entities, "added_interceptor");
		const Entity &missile = require_entity(entities, "added_missile");
		check((interceptor.kinematics.vel_mps -
				(missile.kinematics.pos_m - interceptor.kinematics.pos_m).normalized() *
				added_interceptor.initial_pursuit->speed_mps).norm() < 1e-9,
			"Initial pursuit must use the same manually selected guidance target.");

		for (const std::string &invalid_target : { "missing_entity", "added_interceptor" })
		{
			params.entities.front().initial_pursuit->target_key = invalid_target;
			bool rejected = false;
			try { instantiate_entities(params); }
			catch (const std::invalid_argument &) { rejected = true; }
			check(rejected, "Missing and self guidance targets must be rejected.");
		}
	}

	void test_seeded_radar_contract()
	{
		auto params = *make_default_scenario().entities.front().radar;
		params.bandwidth_hz = 10'000.0;
		params.pw_us = 100.0;
		params.pri_us = 1'000.0;
		RadarComponent first{ .params = finalize_radar_params(params) };
		RadarComponent second{ .params = finalize_radar_params(params) };
		std::mt19937 first_rng(1234), second_rng(1234);
		KinematicStateECI observer;
		Entity target;
		target.kinematics.pos_m.x() = 100'000.0;
		generate_returns(observer, first, { target }, first_rng);
		generate_returns(observer, second, { target }, second_rng);
		process_returns(first);
		process_returns(second);
		check(first.state.range_pulse_map.rows() == 27 && first.state.range_pulse_map.cols() == 16,
			"Range-pulse sample dimensions changed.");
		check(first.state.range_pulse_map == second.state.range_pulse_map &&
			first.state.range_doppler_map == second.state.range_doppler_map,
			"Seeded raw and processed radar outputs must be repeatable.");
	}
}

int main()
{
	try
	{
		test_coordinate_conversions();
		test_guidance_and_controls();
		test_configured_guidance_targets();
		test_simulation_contract();
		test_entity_logger();
		test_seeded_radar_contract();
		std::cout << "C++ simulation checks passed.\n";
		return 0;
	}
	catch (const std::exception &error)
	{
		std::cerr << error.what() << '\n';
		return 1;
	}
}
