#pragma once

#include <array>
#include <string>
#include <tuple>

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
