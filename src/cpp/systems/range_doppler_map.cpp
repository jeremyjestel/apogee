#include "systems/range_doppler_map.hpp"

#include <Eigen/Dense>
#include <cmath>

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
        radar_kinematics.pos_m,
        target_kinematics.pos_m);
    double target_range = radar.state.target_range_m;
    double target_vel = radar.state.target_vel_mps;
    
    const RadarParams &p = radar.p;

    // Reuse the same range equation as the static SNR analysis.
    const auto radar_equation_result = radar_snr_db(
        p,
        target_rcs_dbsm,
        radar.state.target_range_m);
    radar.state.signal_to_noise_db = std::get<3>(radar_equation_result);

    double target_slug;
    double detectable_range_m = p.mur_m - p.mdr_m;
    double detectable_time_s = p.pri_s - p.pw_s;

    // if rounding here what do
    int num_samples = std::round(p.sampling_rate_hz * detectable_time_s);

    Eigen::MatrixXd range_pulse = Eigen::MatrixXd::Zero(num_samples, p.pulse_num);

    double travel_time_s =
        2 * radar.state.target_range_m / constants::speed_of_light_mps;

    int target_sample_ind = std::round(num_samples * (travel_time_s - p.pw_s) / (p.pri_s - p.pw_s));

    // A Target is detectable
    //  Eventually will include second time arounds in here
    if (travel_time_s > p.pw_s && travel_time_s < p.pri_s)
    {
        double target_rcs_lin = std::pow(10, (target_rcs_dbsm / 10));
        
        for (int i = 0; i < p.pulse_num; i++){
            target_slug = std::sqrt(target_rcs_lin) * std::exp(j * 2 * p.wavenumber * (target_range + (i - 1) * target_vel));
            range_pulse(target_sample_ind, i) = target_slug;
        }
            
    }
    //have to create lfm waveform
    //convolve range pulse with waveform
    //Add noise
    //Add Clutter (small rcs and doppler targets with a distribution across ragne and doppler)
    //convolve the flipped conjugate to matched filter, or is this fft?
    // fft across pulses for doppler
}
