#pragma once

#include <cmath>
#include <stdexcept>

#include "math/constants.hpp"
#include "motion/kinematic_state.hpp"
#include "math/types.hpp"

namespace apogee
{
	// Spherical Earth; ECEF and ECI axes coincide at sim_time_s=0. Positions are in meters.
	// LLA vectors contain {latitude_deg, longitude_deg, altitude_m}.
	inline Vec3 lla2ecef(
		double latitude_deg, double longitude_deg, double altitude_m)
	{
		const double latitude_rad = latitude_deg * constants::pi / 180.0;
		const double longitude_rad = longitude_deg * constants::pi / 180.0;
		const double radius_m = altitude_m + constants::earth_radius_m;

		const Vec3 ecef = { radius_m * std::cos(latitude_rad) * std::cos(longitude_rad),
			radius_m * std::cos(latitude_rad) * std::sin(longitude_rad),
			radius_m * std::sin(latitude_rad) };
		return ecef;
	}

	inline Vec3 ecef2lla(const Vec3 &ecef)
	{
		const double horizontal_radius_m = std::hypot(ecef.x(), ecef.y());
		const double radius_m = std::hypot(horizontal_radius_m, ecef.z());
		if (radius_m == 0.0)
		{
			throw std::invalid_argument("Latitude and longitude are undefined at Earth's center.");
		}

		const Vec3 lla = {
			std::atan2(ecef.z(), horizontal_radius_m) * 180.0 / constants::pi,
			std::atan2(ecef.y(), ecef.x()) * 180.0 / constants::pi,
			radius_m - constants::earth_radius_m };
		return lla;
	}

	inline Vec3 ecef2eci(const Vec3 &ecef, double sim_time_s)
	{
		const double angle_rad = constants::earth_rotation_rate_rad_s * sim_time_s;
		const double cosine = std::cos(angle_rad);
		const double sine = std::sin(angle_rad);

		const Vec3 eci = { cosine * ecef.x() - sine * ecef.y(),
			sine * ecef.x() + cosine * ecef.y(), ecef.z() };
		return eci;
	}

	inline Vec3 eci2ecef(const Vec3 &eci, double sim_time_s)
	{
		const double angle_rad = constants::earth_rotation_rate_rad_s * sim_time_s;
		const double cosine = std::cos(angle_rad);
		const double sine = std::sin(angle_rad);

		const Vec3 ecef = { cosine * eci.x() + sine * eci.y(),
			-sine * eci.x() + cosine * eci.y(), eci.z() };
		return ecef;
	}

	inline Vec3 lla2eci(
		double latitude_deg, double longitude_deg, double altitude_m, double sim_time_s)
	{
		const Vec3 ecef = lla2ecef(latitude_deg, longitude_deg, altitude_m);
		const Vec3 eci = ecef2eci(ecef, sim_time_s);
		return eci;
	}

	inline Vec3 eci2lla(const Vec3 &eci, double sim_time_s)
	{
		const Vec3 ecef = eci2ecef(eci, sim_time_s);
		const Vec3 lla = ecef2lla(ecef);
		return lla;
	}

	inline double deg2rad(double angle_deg)
	{
		return angle_deg * constants::pi / 180.0;
	}

	inline double rad2deg(double angle_rad)
	{
		return angle_rad * 180.0 / constants::pi;
	}

	inline Vec3 lla2ecef(const Vec3 &lla)
	{
		return lla2ecef(lla.x(), lla.y(), lla.z());
	}

	// Local positions use an Earth-fixed LLA origin; rotation matrices act on vectors only.
	inline Mat3 ecef2enu_rotation(double latitude_deg, double longitude_deg)
	{
		const double latitude_rad = deg2rad(latitude_deg);
		const double longitude_rad = deg2rad(longitude_deg);
		const double sin_lat = std::sin(latitude_rad);
		const double cos_lat = std::cos(latitude_rad);
		const double sin_lon = std::sin(longitude_rad);
		const double cos_lon = std::cos(longitude_rad);

		Mat3 rotation;
		rotation << -sin_lon, cos_lon, 0.0,
			-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat,
			cos_lat * cos_lon, cos_lat * sin_lon, sin_lat;
		return rotation;
	}

	inline Vec3 enu2ned(const Vec3 &enu)
	{
		return Vec3{ enu.y(), enu.x(), -enu.z() };
	}

	inline Vec3 ned2enu(const Vec3 &ned)
	{
		return Vec3{ ned.y(), ned.x(), -ned.z() };
	}

	inline Mat3 ecef2ned_rotation(double latitude_deg, double longitude_deg)
	{
		const Mat3 enu_rotation = ecef2enu_rotation(latitude_deg, longitude_deg);
		Mat3 rotation;
		rotation.row(0) = enu_rotation.row(1);
		rotation.row(1) = enu_rotation.row(0);
		rotation.row(2) = -enu_rotation.row(2);
		return rotation;
	}

	inline Vec3 ecef2enu(const Vec3 &ecef, const Vec3 &origin_lla)
	{
		const Mat3 rotation = ecef2enu_rotation(origin_lla.x(), origin_lla.y());
		const Vec3 offset_ecef = ecef - lla2ecef(origin_lla);
		const Vec3 enu = rotation * offset_ecef;
		return enu;
	}

	inline Vec3 enu2ecef(const Vec3 &enu, const Vec3 &origin_lla)
	{
		const Vec3 origin_ecef = lla2ecef(origin_lla);
		const Mat3 rotation = ecef2enu_rotation(origin_lla.x(), origin_lla.y());
		const Vec3 ecef = origin_ecef + rotation.transpose() * enu;
		return ecef;
	}

	inline Vec3 ecef2ned(const Vec3 &ecef, const Vec3 &origin_lla)
	{
		const Vec3 enu = ecef2enu(ecef, origin_lla);
		const Vec3 ned = enu2ned(enu);
		return ned;
	}

	inline Vec3 ned2ecef(const Vec3 &ned, const Vec3 &origin_lla)
	{
		const Vec3 enu = ned2enu(ned);
		const Vec3 ecef = enu2ecef(enu, origin_lla);
		return ecef;
	}

	inline Vec3 eci2ned(const Vec3 &eci, const Vec3 &origin_lla, double sim_time_s)
	{
		const Vec3 ecef = eci2ecef(eci, sim_time_s);
		const Vec3 ned = ecef2ned(ecef, origin_lla);
		return ned;
	}

	inline Vec3 ned2eci(const Vec3 &ned, const Vec3 &origin_lla, double sim_time_s)
	{
		const Vec3 ecef = ned2ecef(ned, origin_lla);
		const Vec3 eci = ecef2eci(ecef, sim_time_s);
		return eci;
	}

	// RAE = {range_m, azimuth_deg, elevation_deg}; azimuth is clockwise from North, elevation up.
	inline Vec3 ned2rae(const Vec3 &ned)
	{
		const double horizontal_range_m = std::hypot(ned.x(), ned.y());
		const double range_m = std::hypot(horizontal_range_m, ned.z());
		if (range_m == 0.0)
		{
			return Vec3::Zero();
		}
		double azimuth_deg = rad2deg(std::atan2(ned.y(), ned.x()));
		if (azimuth_deg < 0.0)
		{
			azimuth_deg += 360.0;
		}
		const double elevation_deg = rad2deg(std::atan2(-ned.z(), horizontal_range_m));
		const Vec3 rae{ range_m, azimuth_deg, elevation_deg };
		return rae;
	}

	inline Vec3 rae2ned(double range_m, double azimuth_deg, double elevation_deg)
	{
		if (range_m < 0.0)
		{
			throw std::invalid_argument("Range must be non-negative.");
		}
		const double azimuth_rad = deg2rad(azimuth_deg);
		const double elevation_rad = deg2rad(elevation_deg);
		const double horizontal_range_m = range_m * std::cos(elevation_rad);
		const Vec3 ned{ horizontal_range_m * std::cos(azimuth_rad),
			horizontal_range_m * std::sin(azimuth_rad), -range_m * std::sin(elevation_rad) };
		return ned;
	}

	inline Vec3 rae2ned(const Vec3 &rae)
	{
		return rae2ned(rae.x(), rae.y(), rae.z());
	}

	inline Vec3 enu2rae(const Vec3 &enu)
	{
		const Vec3 ned = enu2ned(enu);
		const Vec3 rae = ned2rae(ned);
		return rae;
	}

	inline Vec3 rae2enu(double range_m, double azimuth_deg, double elevation_deg)
	{
		const Vec3 ned = rae2ned(range_m, azimuth_deg, elevation_deg);
		const Vec3 enu = ned2enu(ned);
		return enu;
	}

	inline Vec3 rae2enu(const Vec3 &rae)
	{
		return rae2enu(rae.x(), rae.y(), rae.z());
	}

	namespace detail
	{
		inline Quat unit_quaternion(const Quat &rotation)
		{
			const double norm = rotation.norm();
			if (!std::isfinite(norm) || norm <= 0.0)
			{
				throw std::invalid_argument("Attitude quaternion must be finite and nonzero.");
			}
			return rotation.normalized();
		}
	}

	// RPY is in degrees, with body-to-NED rotation Rz(yaw) * Ry(pitch) * Rx(roll).
	inline Quat rpy2quat(double roll_deg, double pitch_deg, double yaw_deg)
	{
		const Eigen::AngleAxisd yaw(deg2rad(yaw_deg), Vec3::UnitZ());
		const Eigen::AngleAxisd pitch(deg2rad(pitch_deg), Vec3::UnitY());
		const Eigen::AngleAxisd roll(deg2rad(roll_deg), Vec3::UnitX());
		const Quat body_to_ned{ yaw * pitch * roll };
		return body_to_ned;
	}

	inline Vec3 quat2rpy(const Quat &body_to_ned)
	{
		const Mat3 rotation = detail::unit_quaternion(body_to_ned).toRotationMatrix();
		const double horizontal = std::hypot(rotation(0, 0), rotation(1, 0));
		const double pitch_rad = std::atan2(-rotation(2, 0), horizontal);
		const double roll_rad = horizontal > 1e-12
			? std::atan2(rotation(2, 1), rotation(2, 2)) : 0.0;
		const double yaw_rad = horizontal > 1e-12
			? std::atan2(rotation(1, 0), rotation(0, 0))
			: std::atan2(-rotation(0, 1), rotation(1, 1));
		const Vec3 rpy{ rad2deg(roll_rad), rad2deg(pitch_rad), rad2deg(yaw_rad) };
		return rpy;
	}

	// Body helpers rotate FRD vectors only; body_to_ned refers to the supplied local frame.
	inline Vec3 body2ned(const Vec3 &body, const Quat &body_to_ned)
	{
		const Vec3 ned = detail::unit_quaternion(body_to_ned) * body;
		return ned;
	}

	inline Vec3 ned2body(const Vec3 &ned, const Quat &body_to_ned)
	{
		const Vec3 body = detail::unit_quaternion(body_to_ned).conjugate() * ned;
		return body;
	}

	inline Vec3 body2enu(const Vec3 &body, const Quat &body_to_ned)
	{
		const Vec3 ned = body2ned(body, body_to_ned);
		const Vec3 enu = ned2enu(ned);
		return enu;
	}

	inline Vec3 enu2body(const Vec3 &enu, const Quat &body_to_ned)
	{
		const Vec3 ned = enu2ned(enu);
		const Vec3 body = ned2body(ned, body_to_ned);
		return body;
	}

	inline Vec3 body2ecef(const Vec3 &body, const Quat &body_to_ned, const Vec3 &origin_lla)
	{
		const Mat3 rotation = ecef2ned_rotation(origin_lla.x(), origin_lla.y());
		const Vec3 ned = body2ned(body, body_to_ned);
		const Vec3 ecef = rotation.transpose() * ned;
		return ecef;
	}

	inline Vec3 ecef2body(const Vec3 &ecef_vector, const Quat &body_to_ned, const Vec3 &origin_lla)
	{
		const Mat3 rotation = ecef2ned_rotation(origin_lla.x(), origin_lla.y());
		const Vec3 ned = rotation * ecef_vector;
		const Vec3 body = ned2body(ned, body_to_ned);
		return body;
	}

	inline Vec3 body2eci(const Vec3 &body, const Quat &body_to_ned,
		const Vec3 &origin_lla, double sim_time_s)
	{
		const Vec3 ecef = body2ecef(body, body_to_ned, origin_lla);
		const Vec3 eci = ecef2eci(ecef, sim_time_s);
		return eci;
	}

	inline Vec3 eci2body(const Vec3 &eci_vector, const Quat &body_to_ned,
		const Vec3 &origin_lla, double sim_time_s)
	{
		const Vec3 ecef = eci2ecef(eci_vector, sim_time_s);
		const Vec3 body = ecef2body(ecef, body_to_ned, origin_lla);
		return body;
	}

	// Velocities and accelerations are coordinate derivatives in their source frame.
	inline Vec3 eci2ecef_velocity(const Vec3 &position_eci_m, const Vec3 &velocity_eci_mps,
		double sim_time_s)
	{
		const Vec3 omega{ 0.0, 0.0, constants::earth_rotation_rate_rad_s };
		const Vec3 relative_velocity_eci_mps = velocity_eci_mps - omega.cross(position_eci_m);
		const Vec3 velocity_ecef_mps = eci2ecef(relative_velocity_eci_mps, sim_time_s);
		return velocity_ecef_mps;
	}

	inline Vec3 ecef2eci_velocity(const Vec3 &position_ecef_m, const Vec3 &velocity_ecef_mps,
		double sim_time_s)
	{
		const Vec3 omega{ 0.0, 0.0, constants::earth_rotation_rate_rad_s };
		const Vec3 inertial_velocity_ecef_mps = velocity_ecef_mps + omega.cross(position_ecef_m);
		const Vec3 velocity_eci_mps = ecef2eci(inertial_velocity_ecef_mps, sim_time_s);
		return velocity_eci_mps;
	}

	inline Vec3 eci2ecef_acceleration(const Vec3 &position_eci_m, const Vec3 &velocity_eci_mps,
		const Vec3 &acceleration_eci_mps2, double sim_time_s)
	{
		const Vec3 omega{ 0.0, 0.0, constants::earth_rotation_rate_rad_s };
		const Vec3 position_ecef_m = eci2ecef(position_eci_m, sim_time_s);
		const Vec3 velocity_ecef_mps = eci2ecef_velocity(position_eci_m, velocity_eci_mps, sim_time_s);
		const Vec3 coriolis_mps2 = 2.0 * omega.cross(velocity_ecef_mps);
		const Vec3 centripetal_mps2 = omega.cross(omega.cross(position_ecef_m));
		const Vec3 acceleration_ecef_mps2 =
			eci2ecef(acceleration_eci_mps2, sim_time_s) - coriolis_mps2 - centripetal_mps2;
		return acceleration_ecef_mps2;
	}

	inline Vec3 ecef2eci_acceleration(const Vec3 &position_ecef_m, const Vec3 &velocity_ecef_mps,
		const Vec3 &acceleration_ecef_mps2, double sim_time_s)
	{
		const Vec3 omega{ 0.0, 0.0, constants::earth_rotation_rate_rad_s };
		const Vec3 coriolis_mps2 = 2.0 * omega.cross(velocity_ecef_mps);
		const Vec3 centripetal_mps2 = omega.cross(omega.cross(position_ecef_m));
		const Vec3 inertial_acceleration_ecef_mps2 =
			acceleration_ecef_mps2 + coriolis_mps2 + centripetal_mps2;
		const Vec3 acceleration_eci_mps2 = ecef2eci(inertial_acceleration_ecef_mps2, sim_time_s);
		return acceleration_eci_mps2;
	}

	inline KinematicStateECEF eci2ecef(const KinematicStateECI &state, double sim_time_s)
	{
		const Vec3 ecef_pos_m = eci2ecef(state.pos_m, sim_time_s);
		const Vec3 ecef_vel_mps = eci2ecef_velocity(state.pos_m, state.vel_mps, sim_time_s);
		const Vec3 ecef_accel_mps2 =
			eci2ecef_acceleration(state.pos_m, state.vel_mps, state.accel_mps2, sim_time_s);
		const KinematicStateECEF ecef{ ecef_pos_m, ecef_vel_mps, ecef_accel_mps2 };
		return ecef;
	}

	inline KinematicStateECI ecef2eci(const KinematicStateECEF &state, double sim_time_s)
	{
		const Vec3 eci_pos_m = ecef2eci(state.pos_m, sim_time_s);
		const Vec3 eci_vel_mps = ecef2eci_velocity(state.pos_m, state.vel_mps, sim_time_s);
		const Vec3 eci_accel_mps2 =
			ecef2eci_acceleration(state.pos_m, state.vel_mps, state.accel_mps2, sim_time_s);
		const KinematicStateECI eci{ eci_pos_m, eci_vel_mps, eci_accel_mps2 };
		return eci;
	}
}
