#include "sensors/radar/models/radar_processing.hpp"
#include "math/dsp/correlate.hpp"
#include <complex>

namespace apogee{
    void process_returns(const KinematicStateECI &radar_pos,
        RadarComponent &radar,
        const std::vector<Entity> &targets){

        const RadarParams &params = radar.params;
        CMatX rp_map = radar.state.range_pulse_map;
        CMatX rp_mf_mat = CMatX::Zero(rp_map.rows(), rp_map.cols());

        CVecX range_weighting = window_creation(rp_map.rows, params.range_window);
        CVecX doppler_weighting = window_creation(rp_map.rows, params.doppler_window);
        CVecX mf_kernel = range_weighting * radar.state.wf.conjugate().reverse().eval(); //.array?

        for (int pulse_idx = 0; pulse_idx < params.pulse_num;pulse_idx++){
            rp_mf_mat.col(pulse_idx) = correlate(rp_map.col(pulse_idx), mf_kernel, "same");
        }
        // doppler weighted FFT across pulses
        
        // create kernel with weighting
        // matched filter convolution of range with waveform convolution



    }
}
