#pragma once

// Shared physical and unit constants used throughout the simulation.
namespace constants
{
inline constexpr double pi = 3.14159265358979323;    
inline constexpr double speed_of_light_mps = 299'792'458.0;
inline constexpr double boltzmann_constant_j_per_k = 1.380649e-23;
inline constexpr double reference_noise_temperature_k = 290.0;
inline constexpr double earth_mean_radius_m = 6'371'000.0;

inline constexpr double meters_per_kilometer = 1'000.0;
inline constexpr double hertz_per_gigahertz = 1'000'000'000.0;
inline constexpr double microseconds_per_second = 1'000'000.0;
inline constexpr double radar_sampling_rate_multiplier = 3.0;

inline constexpr char eci_frame[] = "eci";
}
