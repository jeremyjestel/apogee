#pragma once

#include <string>
namespace apogee {

struct RadarParams {

    // Transmitter
    double frequency_hz = 10e9;
    double peak_power_w = 1000.0;
    double pulse_width_s = 1e-6;
    double prf_hz = 1000.0;

    // Antenna
    double tx_gain_db = 30.0;
    double rx_gain_db = 30.0;

    // Receiver
    double noise_figure_db = 3.0;
    double noise_bandwidth_hz = 1e6;
    double system_loss_db = 0.0;
    double system_temperature_k = 290.0;

    // Processing
    double integration_gain_db = 0.0;
    double detection_threshold_db = 10.0;
};

struct RadarState {
    bool enabled = true;
    double last_update_s = 0.0;
};

struct RadarComponent {
    std::string name;
    RadarParams params;
    RadarState state;
};

}