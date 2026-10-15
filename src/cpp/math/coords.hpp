#pragma once

#include <cmath>
#include <stdexcept>

#include "core/constants.hpp"
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
		return ecef2eci(lla2ecef(latitude_deg, longitude_deg, altitude_m), sim_time_s);
	}

	inline Vec3 eci2lla(const Vec3 &eci, double sim_time_s)
	{
		return ecef2lla(eci2ecef(eci, sim_time_s));
	}
}
