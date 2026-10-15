#include <array>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

#include "math/coords.hpp"

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

	void check_vector(const Vec3 &actual, const Vec3 &expected, double tolerance,
		const std::string &message)
	{
		check((actual - expected).norm() < tolerance, message);
	}

	template <typename Function> void check_invalid(Function function, const std::string &message)
	{
		bool rejected = false;
		try
		{
			function();
		}
		catch (const std::invalid_argument &)
		{
			rejected = true;
		}
		check(rejected, message);
	}

	void test_local_frames()
	{
		const Vec3 origin_lla{ 0.0, 0.0, 150.0 };
		const Vec3 origin_ecef = lla2ecef(origin_lla);
		const Vec3 target = origin_ecef + Vec3{ 30.0, 20.0, 10.0 };
		check_vector(ecef2enu(target, origin_lla), Vec3{ 20.0, 10.0, 30.0 }, 1e-6,
			"ENU axes at the equator/prime meridian are incorrect.");
		check_vector(ecef2ned(target, origin_lla), Vec3{ 10.0, 20.0, -30.0 }, 1e-6,
			"NED axes at the equator/prime meridian are incorrect.");
		check_vector(ecef2ned(origin_ecef, origin_lla), Vec3::Zero(), 1e-6,
			"A local origin must map to zero, including its altitude.");
		check_vector(enu2ned(Vec3{ 1.0, 2.0, 3.0 }), Vec3{ 2.0, 1.0, -3.0 }, 1e-12,
			"ENU-to-NED must swap horizontal axes and reverse the vertical axis.");
		check_vector(ned2enu(Vec3{ 2.0, 1.0, -3.0 }), Vec3{ 1.0, 2.0, 3.0 }, 1e-12,
			"NED-to-ENU must invert the axis convention.");
		check_vector(ecef2ned_rotation(0.0, 0.0) * Vec3::UnitX(), -Vec3::UnitZ(), 1e-12,
			"NED vector rotations must not translate the vector.");

		const Vec3 north_pole{ 90.0, 0.0, 0.0 };
		check_vector(ecef2ned(lla2ecef(north_pole) + Vec3{ 10.0, 20.0, 30.0 }, north_pole),
			Vec3{ -10.0, 20.0, -30.0 }, 1e-6, "Polar local axes are incorrect.");

		const std::array<Vec3, 5> origins{ origin_lla, Vec3{ 45.0, -100.0, 2'000.0 },
			Vec3{ -31.0, 179.5, -100.0 }, north_pole, Vec3{ -90.0, 120.0, 0.0 } };
		const Vec3 local{ 123.0, -456.0, -78.0 };
		for (const Vec3 &origin : origins)
		{
			for (const Mat3 &rotation : { ecef2enu_rotation(origin.x(), origin.y()),
				 ecef2ned_rotation(origin.x(), origin.y()) })
			{
				check((rotation * rotation.transpose() - Mat3::Identity()).norm() < 1e-12 &&
					std::abs(rotation.determinant() - 1.0) < 1e-12,
					"Local frames must be orthonormal and right-handed.");
			}
			check_vector(ecef2enu(enu2ecef(local, origin), origin), local, 1e-6,
				"ENU/ECEF round trip changed the local position.");
			check_vector(ecef2ned(ned2ecef(local, origin), origin), local, 1e-6,
				"NED/ECEF round trip changed the local position.");
			for (double time_s : { 0.0, 1'234.5, -4'000.0 })
			{
				check_vector(eci2ned(ned2eci(local, origin, time_s), origin, time_s), local, 1e-6,
					"NED/ECI round trip changed the local position.");
			}
		}
		const double quarter_turn_s = constants::pi / (2.0 * constants::earth_rotation_rate_rad_s);
		check_vector(ned2eci(Vec3::Zero(), origin_lla, quarter_turn_s),
			Vec3{ 0.0, constants::earth_radius_m + 150.0, 0.0 }, 1e-6,
			"An Earth-fixed local origin must rotate in ECI as time advances.");
	}

	void test_radar_coordinates()
	{
		check_vector(ned2rae(Vec3{ 100.0, 0.0, 0.0 }), Vec3{ 100.0, 0.0, 0.0 }, 1e-12,
			"North must have azimuth zero.");
		check_vector(ned2rae(Vec3{ 0.0, 100.0, 0.0 }), Vec3{ 100.0, 90.0, 0.0 }, 1e-12,
			"East must have azimuth 90 degrees.");
		check_vector(ned2rae(Vec3{ -100.0, 0.0, 0.0 }), Vec3{ 100.0, 180.0, 0.0 }, 1e-12,
			"South must have azimuth 180 degrees.");
		check_vector(ned2rae(Vec3{ 0.0, -100.0, 0.0 }), Vec3{ 100.0, 270.0, 0.0 }, 1e-12,
			"West must have azimuth 270 degrees.");
		check_vector(ned2rae(Vec3{ 0.0, 0.0, -100.0 }), Vec3{ 100.0, 0.0, 90.0 }, 1e-12,
			"Up must have elevation +90 degrees.");
		check_vector(ned2rae(Vec3{ 0.0, 0.0, 100.0 }), Vec3{ 100.0, 0.0, -90.0 }, 1e-12,
			"Down must have elevation -90 degrees.");
		check_vector(ned2rae(Vec3::Zero()), Vec3::Zero(), 1e-12,
			"Zero range uses zero azimuth and elevation.");
		check_vector(rae2ned(2.0, 0.0, 30.0), Vec3{ std::sqrt(3.0), 0.0, -1.0 }, 1e-12,
			"RAE interfaces must accept degrees and positive-up elevation.");
		check_vector(rae2enu(100.0, 90.0, 0.0), Vec3{ 100.0, 0.0, 0.0 }, 1e-12,
			"ENU radar coordinates must retain compass azimuth.");
		for (const Vec3 &local : { Vec3{ 1.0, 2.0, 3.0 }, Vec3{ -7.0, 5.0, -6.0 },
			 Vec3{ 0.0, 0.0, 12.0 }, Vec3::Zero().eval() })
		{
			check_vector(rae2ned(ned2rae(local)), local, 1e-10,
				"NED/RAE round trip changed the displacement.");
			check_vector(rae2enu(enu2rae(local)), local, 1e-10,
				"ENU/RAE round trip changed the displacement.");
		}
		check_invalid([] { rae2ned(-1.0, 0.0, 0.0); }, "Negative radar range must be rejected.");
	}

	void test_body_frames()
	{
		check(std::abs(deg2rad(90.0) - constants::pi / 2.0) < 1e-12 &&
			std::abs(rad2deg(constants::pi) - 180.0) < 1e-12, "Angle unit conversion is incorrect.");
		check_vector(body2ned(Vec3::UnitX(), rpy2quat(0.0, 0.0, 90.0)), Vec3::UnitY(), 1e-12,
			"Positive FRD yaw must turn the nose from North toward East.");
		check_vector(body2ned(Vec3::UnitX(), rpy2quat(0.0, 90.0, 0.0)), -Vec3::UnitZ(), 1e-12,
			"Positive pitch must point the nose up.");
		check_vector(body2ned(Vec3::UnitY(), rpy2quat(90.0, 0.0, 0.0)), Vec3::UnitZ(), 1e-12,
			"Positive roll must point the right wing down.");
		check_vector(body2enu(Vec3::UnitX(), Quat::Identity()), Vec3::UnitY(), 1e-12,
			"A north-aligned FRD body must point along ENU North.");
		check_vector(body2ecef(Vec3::UnitZ(), Quat::Identity(), Vec3::Zero()), -Vec3::UnitX(), 1e-12,
			"Body Down at the equator must point toward Earth's center without translation.");
		const double quarter_turn_s = constants::pi / (2.0 * constants::earth_rotation_rate_rad_s);
		check_vector(body2eci(Vec3::UnitY(), Quat::Identity(), Vec3::Zero(), quarter_turn_s),
			-Vec3::UnitX(), 1e-12, "Body-to-ECI vectors must include Earth rotation.");

		const std::array<Vec3, 5> attitudes{ Vec3::Zero(), Vec3{ 20.0, -30.0, 145.0 },
			Vec3{ 12.0, 90.0, 55.0 }, Vec3{ -12.0, -90.0, 125.0 }, Vec3{ 179.0, 89.9, -179.0 } };
		const Vec3 body{ 1.0, -2.0, 3.0 };
		const Vec3 origin_lla{ 39.0, -75.0, 800.0 };
		for (const Vec3 &rpy : attitudes)
		{
			const Quat attitude = rpy2quat(rpy.x(), rpy.y(), rpy.z());
			const Vec3 recovered_rpy = quat2rpy(attitude);
			const Quat recovered = rpy2quat(recovered_rpy.x(), recovered_rpy.y(), recovered_rpy.z());
			check(attitude.angularDistance(recovered) < 1e-10,
				"RPY/quaternion round trip must preserve orientation, including pitch singularities.");
			check_vector(ned2body(body2ned(body, attitude), attitude), body, 1e-12,
				"FRD/NED round trip changed the body vector.");
			check_vector(enu2body(body2enu(body, attitude), attitude), body, 1e-12,
				"FRD/ENU round trip changed the body vector.");
			check_vector(ecef2body(body2ecef(body, attitude, origin_lla), attitude, origin_lla),
				body, 1e-12, "FRD/ECEF round trip changed the body vector.");
			check_vector(eci2body(body2eci(body, attitude, origin_lla, 1'353.4), attitude,
				origin_lla, 1'353.4), body, 1e-12, "FRD/ECI round trip changed the body vector.");
			Quat scaled = attitude;
			scaled.coeffs() *= 3.7;
			check_vector(body2ned(body, scaled), body2ned(body, attitude), 1e-12,
				"Non-unit attitude input must be normalized before rotating a vector.");
		}
		check_invalid([] { body2ned(Vec3::UnitX(), Quat{ 0.0, 0.0, 0.0, 0.0 }); },
			"A zero quaternion cannot define an attitude.");
	}

	void test_rotating_states()
	{
		const double radius_m = constants::earth_radius_m + 1'200.0;
		const double omega = constants::earth_rotation_rate_rad_s;
		const KinematicStateECEF fixed{ Vec3{ radius_m, 0.0, 200.0 }, Vec3::Zero(), Vec3::Zero() };
		const KinematicStateECI inertial = ecef2eci(fixed, 0.0);
		check_vector(inertial.pos_m, fixed.pos_m, 1e-6, "State positions must agree at time zero.");
		check_vector(inertial.vel_mps, Vec3{ 0.0, omega * radius_m, 0.0 }, 1e-10,
			"An Earth-fixed point must have rotational velocity in ECI.");
		check_vector(inertial.accel_mps2, Vec3{ -omega * omega * radius_m, 0.0, 0.0 }, 1e-12,
			"An Earth-fixed point must have centripetal acceleration in ECI.");
		const KinematicStateECI fixed_inertial{ fixed.pos_m, Vec3::Zero(), Vec3::Zero() };
		const KinematicStateECEF rotating = eci2ecef(fixed_inertial, 0.0);
		check_vector(rotating.vel_mps, Vec3{ 0.0, -omega * radius_m, 0.0 }, 1e-10,
			"An inertially fixed point must move west in ECEF.");
		check_vector(rotating.accel_mps2, Vec3{ -omega * omega * radius_m, 0.0, 0.0 }, 1e-12,
			"An inertially fixed point must trace a circle in ECEF.");

		const KinematicStateECEF eastward{ fixed.pos_m, Vec3{ 0.0, 120.0, 5.0 }, Vec3::Zero() };
		const KinematicStateECI moving = ecef2eci(eastward, 0.0);
		check_vector(moving.vel_mps, Vec3{ 0.0, 120.0 + omega * radius_m, 5.0 }, 1e-10,
			"State velocity must include both source-frame motion and Earth rotation.");
		check_vector(moving.accel_mps2, Vec3{ -omega * omega * radius_m - 2.0 * omega * 120.0,
			0.0, 0.0 }, 1e-12, "State acceleration must include the Coriolis term.");

		const KinematicStateECEF state{ Vec3{ radius_m, 2'000.0, -800.0 },
			Vec3{ 24.0, -10.0, 7.0 }, Vec3{ 1.0, -2.0, 0.3 } };
		for (double time_s : { 0.0, 1'234.0, -8'000.0 })
		{
			const KinematicStateECI eci = ecef2eci(state, time_s);
			const KinematicStateECEF recovered = eci2ecef(eci, time_s);
			check_vector(recovered.pos_m, state.pos_m, 1e-6, "State round trip changed position.");
			check_vector(recovered.vel_mps, state.vel_mps, 1e-9, "State round trip changed velocity.");
			check_vector(recovered.accel_mps2, state.accel_mps2, 1e-11,
				"State round trip changed acceleration.");
		}

		const double time_s = 1'234.0;
		const double delta_s = 0.1;
		const Vec3 before = ecef2eci(state.pos_m - state.vel_mps * delta_s +
			0.5 * state.accel_mps2 * delta_s * delta_s, time_s - delta_s);
		const Vec3 now = ecef2eci(state.pos_m, time_s);
		const Vec3 after = ecef2eci(state.pos_m + state.vel_mps * delta_s +
			0.5 * state.accel_mps2 * delta_s * delta_s, time_s + delta_s);
		const KinematicStateECI converted = ecef2eci(state, time_s);
		check_vector(converted.vel_mps, (after - before) / (2.0 * delta_s), 1e-5,
			"Converted velocity must match the derivative of converted position.");
		check_vector(converted.accel_mps2, (after - 2.0 * now + before) / (delta_s * delta_s), 1e-5,
			"Converted acceleration must match the second derivative of converted position.");
	}
}

int main()
{
	try
	{
		test_local_frames();
		test_radar_coordinates();
		test_body_frames();
		test_rotating_states();
		std::cout << "C++ coordinate checks passed.\n";
		return 0;
	}
	catch (const std::exception &error)
	{
		std::cerr << error.what() << '\n';
		return 1;
	}
}
