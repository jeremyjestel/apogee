#pragma once


struct RadarParams
{
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


struct InterceptorParams
{
    double mass_kg = 500.0;
    double thrust_n = 20000.0;
    double max_g = 30.0;
};


struct MissileParams
{
    double mass_kg = 800.0;
    double speed_mps = 1200.0;
    double drag_coefficient = 0.4;
};


struct SimulationParams
{
    double dt_s = 1.0;
    double duration_s = 10.0;
};


struct Params
{
    SimulationParams simulation;
    RadarParams radar;
    InterceptorParams interceptor;
    MissileParams missile;
};
