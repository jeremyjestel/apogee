#pragma once

#include <string>

#include "core/kinematic_state.hpp"

struct SimulationParams
{
    double dt_s = .1;
    double duration_s = 10.0;
    std::string coordinate_frame = "eci";
};

struct BlueRadarParams
{
    KinematicState initial_kinematics{
        Vec3{100.0, 200.0, 300.0},
        Vec3{1.0, 2.0, 3.0},
        Vec3{0.1, 0.2, 0.3}
    };
    double frequency_hz = 10e9;
    double wavelength_m = 3e8 / frequency_hz;
    double power_dbw = 50.0;
    double tx_gain_db = 35.0;
    double rx_gain_db = 20.0;
    double RCS_dbsm = -10.0;
    double noise_figure_db = 3.0;
    double bandwidth_hz = 1e6;
    double system_loss_db = 3.0; 
    double max_range_m = 10000.0;
    double range_step_m = 10.0;
};

struct BlueSatelliteParams
{
    KinematicState initial_kinematics{
        Vec3{1000.0, 2000.0, 3000.0},
        Vec3{10.0, 20.0, 30.0},
        Vec3{1.0, 2.0, 3.0}
    };
};

struct RedMissileParams
{
    KinematicState initial_kinematics{
        Vec3{-1000.0, -2000.0, 500.0},
        Vec3{100.0, 50.0, 25.0},
        Vec3{5.0, -2.0, 1.0}
    };
    double mass_kg = 800.0;
    double speed_mps = 1200.0;
    double drag_coefficient = 0.4;
};

struct BlueInterceptorParams
{
    KinematicState initial_kinematics{
        Vec3{500.0, -500.0, 100.0},
        Vec3{-25.0, 40.0, 15.0},
        Vec3{2.0, 3.0, -1.0}
    };
    double mass_kg = 500.0;
    double thrust_n = 20000.0;
    double max_g = 30.0;
};


struct Params
{
    SimulationParams simulation;
    BlueRadarParams blue_radar;
    BlueSatelliteParams blue_satellite;
    RedMissileParams red_missile;
    BlueInterceptorParams blue_interceptor;
};
