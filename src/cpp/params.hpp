#pragma once

#include <array>
#include <cmath>
#include <stdexcept>
#include <string>
#include <tuple>

#include "core/constants.hpp"
#include "core/kinematic_state.hpp"

// A field descriptor connects one editable C++ member to its UI name and unit.
template <typename Owner, typename Value>
struct ParameterField
{
    const char* key;
    Value Owner::* member;
    const char* name;
    const char* unit;
};

// This helper keeps each field declaration short while preserving its member type.
template <typename Owner, typename Value>
constexpr ParameterField<Owner, Value> parameter(
    const char* key,
    Value Owner::* member,
    const char* name,
    const char* unit
)
{
    return {key, member, name, unit};
}

struct SimulationParams
{
    double dt_s = 0.0;
    double duration_s = 0.0;

    // The binding layer iterates this tuple to expose every editable simulation input.
    static constexpr auto fields()
    {
        return std::tuple{
            parameter("dt_s", &SimulationParams::dt_s, "Time step", "s"),
            parameter(
                "duration_s",
                &SimulationParams::duration_s,
                "Duration",
                "s"
            )
        };
    }
};

struct RadarParams
{
    // These are the editable radar inputs copied from the scenario before each run.
    double frequency_hz = 0.0;
    double power_dbw = 0.0;
    double tx_gain_db = 0.0;
    double rx_gain_db = 0.0;
    double noise_figure_db = 0.0;
    double bandwidth_hz = 0.0;
    double system_loss_db = 0.0;
    double pw_us = 0.0;
    double pri_us = 0.0;
    int pulse_num = 16;

    // These derived values are calculated once in the fresh runtime RadarModule.
    double frequency_ghz = 0.0;
    double wavelength_m = 0.0;
    double power_w = 0.0;
    double tx_gain_lin = 0.0;
    double rx_gain_lin = 0.0;
    double noise_figure_lin = 0.0;
    double system_loss_lin = 0.0;
    double sampling_rate_hz = 0.0;
    double pw_s = 0.0;
    double pri_s = 0.0;
    double mdr_m = 0.0;
    double mur_m = 0.0;
    double wavenumber = 0.0;

    // Only the independent inputs belong in the parameter window.
    static constexpr auto fields()
    {
        return std::tuple{
            parameter(
                "frequency_hz",
                &RadarParams::frequency_hz,
                "Frequency",
                "Hz"
            ),
            parameter(
                "power_dbw",
                &RadarParams::power_dbw,
                "Transmit power",
                "dBW"
            ),
            parameter(
                "tx_gain_db",
                &RadarParams::tx_gain_db,
                "Transmit gain",
                "dB"
            ),
            parameter(
                "rx_gain_db",
                &RadarParams::rx_gain_db,
                "Receive gain",
                "dB"
            ),
            parameter(
                "noise_figure_db",
                &RadarParams::noise_figure_db,
                "Noise figure",
                "dB"
            ),
            parameter(
                "bandwidth_hz",
                &RadarParams::bandwidth_hz,
                "Bandwidth",
                "Hz"
            ),
            parameter(
                "system_loss_db",
                &RadarParams::system_loss_db,
                "System loss",
                "dB"
            ),
            parameter(
                "pulse_width_us",
                &RadarParams::pw_us,
                "Pulse width",
                "us"
            ),
            parameter(
                "pri_us",
                &RadarParams::pri_us,
                "Pulse repetition interval",
                "us"
            )
        };
    }
};

struct SatelliteParams
{
    double orbital_altitude_m = 0.0;
    double orbit_direction = 1.0;
    double inclination_deg = 0.0;
    double ascending_node_deg = 0.0;
    double orbital_phase_deg = 90.0;

    KinematicState initial_kinematics() const
    {
        if (orbital_altitude_m < 0.0)
        {
            throw std::invalid_argument(
                "Satellite orbital altitude must be non-negative."
            );
        }
        if (orbit_direction != 1.0 && orbit_direction != -1.0)
        {
            throw std::invalid_argument(
                "Satellite orbit direction must be +1 or -1."
            );
        }

        const double radius_m =
            constants::earth_mean_radius_m + orbital_altitude_m;
        const double speed_mps = std::sqrt(
            constants::earth_mu_m3_s2 / radius_m
        );
        const double acceleration_mps2 =
            constants::earth_mu_m3_s2 / (radius_m * radius_m);
        const double inclination_rad = inclination_deg * constants::pi / 180.0;
        const double ascending_node_rad =
            ascending_node_deg * constants::pi / 180.0;
        const double orbital_phase_rad =
            orbital_phase_deg * constants::pi / 180.0;
        const double cos_i = std::cos(inclination_rad);
        const double sin_i = std::sin(inclination_rad);
        const double cos_node = std::cos(ascending_node_rad);
        const double sin_node = std::sin(ascending_node_rad);
        const double cos_phase = std::cos(orbital_phase_rad);
        const double sin_phase = std::sin(orbital_phase_rad);

        const Vec3 position{
            radius_m * (cos_node * cos_phase - sin_node * sin_phase * cos_i),
            radius_m * (sin_node * cos_phase + cos_node * sin_phase * cos_i),
            radius_m * sin_phase * sin_i
        };
        const Vec3 velocity{
            orbit_direction * speed_mps
                * (-cos_node * sin_phase - sin_node * cos_phase * cos_i),
            orbit_direction * speed_mps
                * (-sin_node * sin_phase + cos_node * cos_phase * cos_i),
            orbit_direction * speed_mps * cos_phase * sin_i
        };

        return KinematicState{
            position,
            velocity,
            position * (-acceleration_mps2 / radius_m)
        };
    }

    static constexpr auto fields()
    {
        return std::tuple{
            parameter(
                "orbital_altitude_m",
                &SatelliteParams::orbital_altitude_m,
                "Orbital altitude",
                "m"
            ),
            parameter(
                "orbit_direction",
                &SatelliteParams::orbit_direction,
                "Orbit direction (+1 with Earth, -1 against)",
                ""
            ),
            parameter(
                "inclination_deg",
                &SatelliteParams::inclination_deg,
                "Inclination",
                "deg"
            ),
            parameter(
                "ascending_node_deg",
                &SatelliteParams::ascending_node_deg,
                "Ascending-node longitude",
                "deg"
            ),
            parameter(
                "orbital_phase_deg",
                &SatelliteParams::orbital_phase_deg,
                "Orbital phase",
                "deg"
            )
        };
    }
};

struct GroundParams
{
    double latitude_deg = 0.0;
    double longitude_deg = 0.0;
    double altitude_m = 0.0;

    KinematicState initial_kinematics() const
    {
        if (latitude_deg < -90.0 || latitude_deg > 90.0)
        {
            throw std::invalid_argument(
                "Ground latitude must be between -90 and 90 degrees."
            );
        }

        const double latitude_rad = latitude_deg * constants::pi / 180.0;
        const double longitude_rad = longitude_deg * constants::pi / 180.0;
        const double radius_m = constants::earth_mean_radius_m + altitude_m;
        if (radius_m <= 0.0)
        {
            throw std::invalid_argument("Ground radius must be positive.");
        }

        const double x = radius_m * std::cos(latitude_rad) * std::cos(longitude_rad);
        const double y = radius_m * std::cos(latitude_rad) * std::sin(longitude_rad);
        const double z = radius_m * std::sin(latitude_rad);
        const double omega = constants::earth_rotation_rate_rad_s;

        return KinematicState{
            Vec3{x, y, z},
            Vec3{-omega * y, omega * x, 0.0},
            Vec3{-omega * omega * x, -omega * omega * y, 0.0}
        };
    }

    static constexpr auto fields()
    {
        return std::tuple{
            parameter("latitude_deg", &GroundParams::latitude_deg, "Latitude", "deg"),
            parameter("longitude_deg", &GroundParams::longitude_deg, "Longitude", "deg"),
            parameter("altitude_m", &GroundParams::altitude_m, "Altitude", "m")
        };
    }
};

struct InitialPursuitParams
{
    double latitude_deg = 0.0;
    double longitude_deg = 0.0;
    double altitude_m = 0.0;
    double speed_mps = 0.0;
    std::string target_key;

    KinematicState initial_kinematics() const
    {
        if (latitude_deg < -90.0 || latitude_deg > 90.0)
        {
            throw std::invalid_argument(
                "Initial pursuit latitude must be between -90 and 90 degrees."
            );
        }
        if (speed_mps < 0.0)
        {
            throw std::invalid_argument(
                "Initial pursuit speed must be non-negative."
            );
        }

        const double latitude_rad = latitude_deg * constants::pi / 180.0;
        const double longitude_rad = longitude_deg * constants::pi / 180.0;
        const double radius_m = constants::earth_mean_radius_m + altitude_m;
        if (radius_m <= 0.0)
        {
            throw std::invalid_argument(
                "Initial pursuit radius must be positive."
            );
        }

        return KinematicState{
            Vec3{
                radius_m * std::cos(latitude_rad) * std::cos(longitude_rad),
                radius_m * std::cos(latitude_rad) * std::sin(longitude_rad),
                radius_m * std::sin(latitude_rad)
            },
            Vec3{},
            Vec3{}
        };
    }

    static constexpr auto fields()
    {
        return std::tuple{
            parameter("latitude_deg", &InitialPursuitParams::latitude_deg, "Latitude", "deg"),
            parameter("longitude_deg", &InitialPursuitParams::longitude_deg, "Longitude", "deg"),
            parameter("altitude_m", &InitialPursuitParams::altitude_m, "Altitude", "m"),
            parameter("speed_mps", &InitialPursuitParams::speed_mps, "Speed", "m/s")
        };
    }
};

struct RadarAnalysisParams
{
    double max_range_m = 0.0;
    double range_samples = 0.0;

    // The binding layer uses this list to generate the radar-analysis controls.
    static constexpr auto fields()
    {
        return std::tuple{
            parameter(
                "max_range_m",
                &RadarAnalysisParams::max_range_m,
                "Maximum range",
                "m"
            ),
            parameter(
                "range_samples",
                &RadarAnalysisParams::range_samples,
                "Range samples",
                ""
            )
        };
    }
};

// A flattened specification gives Python enough metadata to render one input row.
struct ParameterSpec
{
    std::string group;
    std::string path;
    std::string name;
    std::string unit;
};

// Two member pointers locate one scalar inside a Vec3 within KinematicState.
struct KinematicParameterField
{
    const char* path;
    const char* name;
    const char* unit;
    Vec3 KinematicState::* vector_member;
    double Vec3::* component_member;
};

// This shared table exposes all position, velocity, and acceleration components.
inline constexpr std::array<KinematicParameterField, 9>
    KINEMATIC_PARAMETER_FIELDS{
        KinematicParameterField{
            "pos_m.x", "Position X", "m", &KinematicState::pos_m, &Vec3::x
        },
        KinematicParameterField{
            "pos_m.y", "Position Y", "m", &KinematicState::pos_m, &Vec3::y
        },
        KinematicParameterField{
            "pos_m.z", "Position Z", "m", &KinematicState::pos_m, &Vec3::z
        },
        KinematicParameterField{
            "vel_mps.x",
            "Velocity X",
            "m/s",
            &KinematicState::vel_mps,
            &Vec3::x
        },
        KinematicParameterField{
            "vel_mps.y",
            "Velocity Y",
            "m/s",
            &KinematicState::vel_mps,
            &Vec3::y
        },
        KinematicParameterField{
            "vel_mps.z",
            "Velocity Z",
            "m/s",
            &KinematicState::vel_mps,
            &Vec3::z
        },
        KinematicParameterField{
            "accel_mps2.x",
            "Acceleration X",
            "m/s^2",
            &KinematicState::accel_mps2,
            &Vec3::x
        },
        KinematicParameterField{
            "accel_mps2.y",
            "Acceleration Y",
            "m/s^2",
            &KinematicState::accel_mps2,
            &Vec3::y
        },
        KinematicParameterField{
            "accel_mps2.z",
            "Acceleration Z",
            "m/s^2",
            &KinematicState::accel_mps2,
            &Vec3::z
        }
    };
