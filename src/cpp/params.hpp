#pragma once

#include <string>
#include <vector>

#include "core/kinematic_state.hpp"


// Add parameters to these tables. Each row contains the C++ type, member name,
// default value, display name, and unit used by both C++ and the Python UI.
// VALUE declares one ordinary field; KINEMATICS expands the shared state into
// its nine UI fields. Always wrap INITIAL in parentheses so commas stay inside
// a single macro argument.
// VALUE rows currently support double and std::string. Keep a derived default
// below any earlier member it uses, as wavelength_m does with frequency_hz.
// Example: X(OWNER, VALUE, double, beamwidth_deg, (2.0), "Beamwidth", "deg")
#define APOGEE_SIMULATION_PARAMETERS(X, OWNER)                              \
    X(OWNER, VALUE, double, dt_s, (0.1), "Time step", "s")                 \
    X(OWNER, VALUE, double, duration_s, (10.0), "Duration", "s")           \
    X(OWNER, VALUE, std::string, coordinate_frame, ("eci"),                \
      "Coordinate frame", "")

#define APOGEE_BLUE_RADAR_PARAMETERS(X, OWNER)                              \
    X(OWNER, KINEMATICS, KinematicState, initial_kinematics,                \
      (KinematicState{                                                      \
          Vec3{100.0, 200.0, 300.0},                                       \
          Vec3{1.0, 2.0, 3.0},                                             \
          Vec3{0.1, 0.2, 0.3}                                              \
      }), "", "")                                                         \
    X(OWNER, VALUE, double, frequency_hz, (10e9), "Frequency", "Hz")       \
    X(OWNER, VALUE, double, wavelength_m, (3e8 / frequency_hz),             \
      "Wavelength", "m")                                                  \
    X(OWNER, VALUE, double, power_dbw, (50.0), "Transmit power", "dBW")   \
    X(OWNER, VALUE, double, tx_gain_db, (35.0), "Transmit gain", "dB")    \
    X(OWNER, VALUE, double, rx_gain_db, (20.0), "Receive gain", "dB")     \
    X(OWNER, VALUE, double, RCS_dbsm, (-10.0),                              \
      "Radar cross section", "dBsm")                                      \
    X(OWNER, VALUE, double, noise_figure_db, (3.0),                         \
      "Noise figure", "dB")                                               \
    X(OWNER, VALUE, double, bandwidth_hz, (1e6), "Bandwidth", "Hz")       \
    X(OWNER, VALUE, double, system_loss_db, (3.0), "System loss", "dB")   \
    X(OWNER, VALUE, double, max_range_m, (10000.0),                         \
      "Maximum analysis range", "m")                                      \
    X(OWNER, VALUE, double, range_step_m, (10.0),                           \
      "Analysis range step", "m")                                         \
    X(OWNER, VALUE, double, target_range_m, (5000.0),                       \
      "Target range", "m")                                                \
    X(OWNER, VALUE, double, target_velocity_mps, (100.0),                   \
      "Target velocity", "m/s")                                           \
    X(OWNER, VALUE, double, target_RCS_dbsm, (0.0),                         \
      "Target radar cross section", "dBsm")

#define APOGEE_BLUE_SATELLITE_PARAMETERS(X, OWNER)                          \
    X(OWNER, KINEMATICS, KinematicState, initial_kinematics,                \
      (KinematicState{                                                      \
          Vec3{1000.0, 2000.0, 3000.0},                                    \
          Vec3{10.0, 20.0, 30.0},                                          \
          Vec3{1.0, 2.0, 3.0}                                              \
      }), "", "")

#define APOGEE_RED_MISSILE_PARAMETERS(X, OWNER)                             \
    X(OWNER, KINEMATICS, KinematicState, initial_kinematics,                \
      (KinematicState{                                                      \
          Vec3{-1000.0, -2000.0, 500.0},                                   \
          Vec3{100.0, 50.0, 25.0},                                         \
          Vec3{5.0, -2.0, 1.0}                                             \
      }), "", "")                                                         \
    X(OWNER, VALUE, double, mass_kg, (1000.0), "Mass", "kg")              \
    X(OWNER, VALUE, double, speed_mps, (1200.0), "Speed", "m/s")          \
    X(OWNER, VALUE, double, drag_coefficient, (0.4),                        \
      "Drag coefficient", "")

#define APOGEE_BLUE_INTERCEPTOR_PARAMETERS(X, OWNER)                        \
    X(OWNER, KINEMATICS, KinematicState, initial_kinematics,                \
      (KinematicState{                                                      \
          Vec3{500.0, -500.0, 100.0},                                      \
          Vec3{-25.0, 40.0, 15.0},                                         \
          Vec3{2.0, 3.0, -1.0}                                             \
      }), "", "")                                                         \
    X(OWNER, VALUE, double, mass_kg, (500.0), "Mass", "kg")               \
    X(OWNER, VALUE, double, thrust_n, (20000.0), "Thrust", "N")           \
    X(OWNER, VALUE, double, max_g, (30.0), "Maximum acceleration", "g")


#define APOGEE_PARAMETER_GROUPS(X)                                         \
    X(simulation, SimulationParams, "Simulation",                         \
      APOGEE_SIMULATION_PARAMETERS)                                        \
    X(blue_radar, BlueRadarParams, "Blue Radar",                          \
      APOGEE_BLUE_RADAR_PARAMETERS)                                        \
    X(blue_satellite, BlueSatelliteParams, "Blue Satellite",              \
      APOGEE_BLUE_SATELLITE_PARAMETERS)                                    \
    X(red_missile, RedMissileParams, "Red Missile",                       \
      APOGEE_RED_MISSILE_PARAMETERS)                                       \
    X(blue_interceptor, BlueInterceptorParams, "Blue Interceptor",         \
      APOGEE_BLUE_INTERCEPTOR_PARAMETERS)


struct LocalParameterSpec
{
    std::string path;
    std::string name;
    std::string unit;
};

struct ParameterSpec
{
    std::string group;
    std::string path;
    std::string name;
    std::string unit;
};


#define APOGEE_UNWRAP(...) __VA_ARGS__

#define APOGEE_DECLARE_PARAMETER(OWNER, KIND, TYPE, MEMBER, INITIAL, NAME, UNIT) \
    TYPE MEMBER = APOGEE_UNWRAP INITIAL;

#define APOGEE_KINEMATIC_SPECS(MEMBER)                                      \
    LocalParameterSpec{#MEMBER ".pos_m.x", "Position X", "m"},             \
    LocalParameterSpec{#MEMBER ".pos_m.y", "Position Y", "m"},             \
    LocalParameterSpec{#MEMBER ".pos_m.z", "Position Z", "m"},             \
    LocalParameterSpec{#MEMBER ".vel_mps.x", "Velocity X", "m/s"},         \
    LocalParameterSpec{#MEMBER ".vel_mps.y", "Velocity Y", "m/s"},         \
    LocalParameterSpec{#MEMBER ".vel_mps.z", "Velocity Z", "m/s"},         \
    LocalParameterSpec{#MEMBER ".accel_mps2.x", "Acceleration X", "m/s^2"}, \
    LocalParameterSpec{#MEMBER ".accel_mps2.y", "Acceleration Y", "m/s^2"}, \
    LocalParameterSpec{#MEMBER ".accel_mps2.z", "Acceleration Z", "m/s^2"},

#define APOGEE_LOCAL_SPEC_VALUE(MEMBER, NAME, UNIT)                         \
    LocalParameterSpec{#MEMBER, NAME, UNIT},

#define APOGEE_LOCAL_SPEC_KINEMATICS(MEMBER, NAME, UNIT)                    \
    APOGEE_KINEMATIC_SPECS(MEMBER)

#define APOGEE_LOCAL_SPEC(OWNER, KIND, TYPE, MEMBER, INITIAL, NAME, UNIT)    \
    APOGEE_LOCAL_SPEC_##KIND(MEMBER, NAME, UNIT)

#define APOGEE_DEFINE_PARAMETER_STRUCT(ROOT, TYPE, GROUP, PARAMETERS)        \
    struct TYPE                                                             \
    {                                                                       \
        PARAMETERS(APOGEE_DECLARE_PARAMETER, TYPE)                          \
                                                                            \
        static std::vector<LocalParameterSpec> parameter_specs()            \
        {                                                                   \
            return {PARAMETERS(APOGEE_LOCAL_SPEC, TYPE)};                   \
        }                                                                   \
    };

APOGEE_PARAMETER_GROUPS(APOGEE_DEFINE_PARAMETER_STRUCT)


#define APOGEE_DECLARE_GROUP(ROOT, TYPE, GROUP, PARAMETERS) TYPE ROOT;

struct Params
{
    APOGEE_PARAMETER_GROUPS(APOGEE_DECLARE_GROUP)
};


inline std::vector<ParameterSpec> parameter_specs()
{
    std::vector<ParameterSpec> specs;

#define APOGEE_APPEND_GROUP(ROOT, TYPE, GROUP, PARAMETERS)                  \
    for (const LocalParameterSpec& local : TYPE::parameter_specs())         \
    {                                                                       \
        specs.push_back(ParameterSpec{                                      \
            GROUP,                                                          \
            std::string{#ROOT} + "." + local.path,                          \
            local.name,                                                     \
            local.unit                                                      \
        });                                                                 \
    }

    APOGEE_PARAMETER_GROUPS(APOGEE_APPEND_GROUP)

#undef APOGEE_APPEND_GROUP

    return specs;
}


#undef APOGEE_DECLARE_GROUP
#undef APOGEE_DEFINE_PARAMETER_STRUCT
#undef APOGEE_LOCAL_SPEC
#undef APOGEE_LOCAL_SPEC_KINEMATICS
#undef APOGEE_LOCAL_SPEC_VALUE
#undef APOGEE_KINEMATIC_SPECS
#undef APOGEE_DECLARE_PARAMETER
#undef APOGEE_UNWRAP

// The parameter-table and group-list macros remain defined for bindings.cpp.
