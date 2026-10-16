#include <array>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

#include "run_sim.hpp"
#include "math/coords.hpp"
#include "logging/logging.hpp"
#include "scenarios/default_scenario.hpp"
#include "motion/models/ground_motion.hpp"
#include "motion/models/motion_system.hpp"
#include "sensors/radar/models/range_doppler_map.hpp"

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
		check(result.entities.size() == 4 && result.vectors.size() == 12 && result.scalars.size() == 4,
			"Default scenario result layout changed.");
		check(result.axes.size() == 1 && result.axes.front().values == std::vector<double>{ 0.0, 0.1 },
			"Simulation sampling convention changed.");
		check(result.metric_tables.size() == 1 && result.curves.size() == 1,
			"Default radar analysis products changed.");

		auto ground = params.entities.front().ground->initial_kinematics();
		check(position(result, 1).values.front() == ground.pos_m,
			"Initial positions must be logged before motion.");
		advance_ground(ground, params.simulation.dt_s);
		check(position(result, 1).values.at(1) == ground.pos_m,
			"Ground motion sequence changed.");

		const auto &table = result.metric_tables.front();
		check(table.time_axis.values == result.axes.front().values && table.metrics.size() == 5,
			"Radar metric table layout changed.");
		check(table.metrics[3].values == std::vector<double>{ params.entities.front().radar->pw_us } &&
				table.metrics[4].values == std::vector<double>{ params.entities.front().radar->pri_us },
			"Constant radar metrics must remain singletons.");
		auto target = KinematicStateECI{ position(result, 3).values.front(),
			result.vectors.at(7).values.front(), Vec3::Zero() };
		advance_kinematics(target, params.simulation.dt_s);
		check(table.metrics.front().values.front() == (ground.pos_m - target.pos_m).norm(),
			"Radar measurements must retain their original post-motion update order.");

		const Result repeated = run_sim(params);
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
		check(run_sim(params).axes.front().values.empty(), "Zero-duration simulation contract changed.");
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
		check(result.entities.size() == 2 && result.vectors.size() == 6 &&
				result.scalars.size() == 2 && result.axes.front().values.empty(),
			"Logger must create empty histories before the first step.");
		check(result.entities.front().id == 41 && result.entities.front().key == "first" &&
				result.entities.front().display_name == "First" &&
				result.entities.front().type == "missile" && result.entities.front().team == "blue",
			"Logger must preserve entity descriptors.");
		logger.log(entities, 0.0);

		entities[0].kinematics = KinematicStateECI{
			Vec3{ 4.0, 5.0, 6.0 }, Vec3{ 0.0, 0.0, 12.0 }, Vec3{ 0.0, 1.0, 0.0 } };
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
		check(result.vectors[1].values.back() == entities[0].kinematics.vel_mps &&
				result.vectors[2].values.back() == entities[0].kinematics.accel_mps2 &&
				result.scalars[0].values == std::vector<double>{ 5.0, 12.0 } &&
				result.scalars[1].values == std::vector<double>{ 5.0, 5.0 },
			"Logger must capture current velocity, acceleration, and speed.");
	}

	void test_seeded_radar_contract()
	{
		auto params = *make_default_scenario().entities.front().radar;
		params.bandwidth_hz = 10'000.0;
		params.pw_us = 100.0;
		params.pri_us = 1'000.0;
		RadarModule first(params, 1234);
		RadarModule second(params, 1234);
		KinematicStateECI observer;
		KinematicStateECI target;
		target.pos_m.x() = 100'000.0;
		const auto product = range_doppler_map(first, observer, target, 0.0);
		const auto repeated = range_doppler_map(second, observer, target, 0.0);
		check(product.has_value() && repeated.has_value(), "Detectable target produced no product.");
		check(product->samples.rows() == 16 && product->samples.cols() == 27,
			"Range-pulse sample dimensions changed.");
		check(product->samples == repeated->samples, "Seeded radar outputs must be repeatable.");
		const auto grid = make_noisy_range_doppler_series(*product, first.p, 1, 0.5);
		check(grid.rows == 27 && grid.columns == 16 && grid.values.size() == 27 * 16 &&
				grid.time_axis.values == std::vector<double>{ 0.5 },
			"Range-pulse display orientation or timeline changed.");
	}
}

int main()
{
	try
	{
		test_coordinate_conversions();
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
