#include "systems/range_doppler_map.hpp"

#include <Eigen/Dense>
#include <cmath>
#include <random>

#include "core/constants.hpp"
#include "math/relative_kinematics.hpp"
#include "math/radar_range_equation.hpp"

// Update radar measurements after both entities have completed their motion step.
void range_doppler_map(
    RadarModule &radar,
    const KinematicState &radar_kinematics,
    const KinematicState &target_kinematics,
    double target_rcs_dbsm)
{

    // This will be called each time step, independent variable is range in this case.
    // This does assume motion has occurred already
    // Returns the range doppler map the radar sees when tracking the missile, assumes max gain
    // Range is changing state, so recompute it from the current positions.
    radar.state.target_range_m = get_3d_difference(
        radar_kinematics.pos_m,
        target_kinematics.pos_m);
    radar.state.target_vel_mps = get_3d_difference(
        radar_kinematics.vel_mps,
        target_kinematics.vel_mps);
    double target_range = radar.state.target_range_m;
    double target_vel = radar.state.target_vel_mps;
    
    const RadarParams &p = radar.p;

    // Reuse the same range equation as the static SNR analysis.
    const auto radar_equation_result = radar_snr_db(
        p,
        target_rcs_dbsm,
        radar.state.target_range_m);
    radar.state.signal_to_noise_db = std::get<3>(radar_equation_result);

    std::complex<double> target_slug;
    double detectable_range_m = p.mur_m - p.mdr_m;
    double detectable_time_s = p.pri_s - p.pw_s;

    // if rounding here what do
    int num_samples = std::round(p.sampling_rate_hz * detectable_time_s);

    Eigen::MatrixXcd range_pulse_empty = Eigen::MatrixXcd::Zero(p.pulse_num, num_samples);
    Eigen::MatrixXcd range_pulse_map  = Eigen::MatrixXcd::Zero(p.pulse_num, num_samples);

    double travel_time_s =
        2 * radar.state.target_range_m / constants::speed_of_light_mps;

    int target_sample_ind = std::round(num_samples * (travel_time_s - p.pw_s) / (p.pri_s - p.pw_s));

    // A Target is detectable
    //  Eventually will include second time arounds in here
    if (travel_time_s > p.pw_s && travel_time_s < p.pri_s)
    {
        double target_rcs_lin = std::pow(10, (target_rcs_dbsm / 10));
        
        for (int i = 0; i < p.pulse_num; i++){
            target_slug = std::sqrt(target_rcs_lin) * std::exp(constants::j * 2 * p.wavenumber * (target_range + i * p.pri_s * target_vel));
            range_pulse_empty(i, target_sample_ind) = target_slug;
        }

        Eigen::VectorXd pulse_time_vec_s = Eigen::VectorXd::LinSpaced(std::floor(p.sampling_rate_hz * p.pw_s), 0.0, p.pw_s);

        Eigen::VectorXcd lfm_waveform(pulse_time_vec_s.size());

        double chirp_rate = p.bandwidth_hz / p.pw_s;
    
        for (Eigen::Index i = 0; i < pulse_time_vec_s.size(); ++i) {
            double phase = constants::pi * chirp_rate * pulse_time_vec_s(i) * pulse_time_vec_s(i);
            lfm_waveform(i) = std::exp(constants::j * phase);
        }
        Eigen::VectorXcd convolved_range = Eigen::VectorXcd::Zero(range_pulse_map.cols());

        std::random_device rd;
        std::mt19937 generator(rd());
        std::normal_distribution<double> randn(0.0, 1.0);
        double sample = randn(generator);
        Eigen::MatrixXcd noise_map  = Eigen::MatrixXcd::Zero(p.pulse_num, num_samples);
        
        for (int n = 0; n < p.pulse_num; n++){
            Eigen::RowVectorXcd pulse = range_pulse_empty.row(n);
            for (int r = 0; r < num_samples; r++) {
                    noise_map(n, r) = std::complex<double>(randn(generator), randn(generator)) / std::sqrt(2.0);
                for (int k = 0; k < lfm_waveform.size(); k++) {
                    int output_index = r + k;

                    if (output_index < num_samples) {
                        convolved_range(output_index) += pulse(r) * lfm_waveform(k);
                    }
                }
            }
            range_pulse_map.row(n) = convolved_range;
        }



    }
    //have to create lfm waveform
    //convolve range pulse with waveform
    //Add noise
    //Add Clutter (small rcs and doppler targets with a distribution across ragne and doppler)
    //convolve the flipped conjugate to matched filter, or is this fft?
    // fft across pulses for doppler
}
