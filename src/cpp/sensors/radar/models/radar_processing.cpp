#include "sensors/radar/models/radar_processing.hpp"

namespace apogee{
    void process_returns(const KinematicStateECI &radar_pos,
        RadarComponent &radar,
        const std::vector<Entity> &targets){

        // doppler weighted FFT across pulses

        // create kernel with weighting
        // matched filter convolution of range with waveform convolution



    }
}
