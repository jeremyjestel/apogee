#include "systems/range_doppler_map.hpp"

#include <Eigen/Dense>
#include <cmath>
#include <cstddef>
#include <random>
#include <utility>

#include "core/constants.hpp"
#include "math/relative_kinematics.hpp"
#include "math/radar_range_equation.hpp"

// Update radar measurements after both entities have completed their motion step.
std::optional<RangePulseProduct> range_doppler_map(
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
    radar.state.signal_to_noise_db = radar_equation_result.snr_db;

    std::complex<double> target_slug;
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
            target_slug = std::sqrt(target_rcs_lin) * std::exp(constants::j * 2.0 * p.wavenumber * (target_range + i * p.pri_s * target_vel));
            range_pulse_empty(i, target_sample_ind) = target_slug;
        }

        Eigen::VectorXd pulse_time_vec_s = Eigen::VectorXd::LinSpaced(std::floor(p.sampling_rate_hz * p.pw_s), 0.0, p.pw_s);

        Eigen::VectorXcd lfm_waveform(pulse_time_vec_s.size());

        double chirp_rate = p.bandwidth_hz / p.pw_s;
    
        for (Eigen::Index i = 0; i < pulse_time_vec_s.size(); ++i) {
            double phase = constants::pi * chirp_rate * pulse_time_vec_s(i) * pulse_time_vec_s(i);
            lfm_waveform(i) = std::exp(constants::j * phase);
        }
        Eigen::RowVectorXcd convolved_range = Eigen::RowVectorXcd::Zero(range_pulse_map.cols());

        std::normal_distribution<double> randn(0.0, 1.0);
        Eigen::MatrixXcd noise_map = Eigen::MatrixXcd::Zero(p.pulse_num, num_samples);
        
        for (int n = 0; n < p.pulse_num; n++){
            Eigen::RowVectorXcd pulse = range_pulse_empty.row(n);
            for (int r = 0; r < num_samples; r++) {
                    noise_map(n, r) = std::complex<double>(
                        randn(radar.noise_generator),
                        randn(radar.noise_generator)
                    ) / std::sqrt(2.0);
                for (int k = 0; k < lfm_waveform.size(); k++) {
                    int output_index = r + k;

                    if (output_index < num_samples) {
                        convolved_range(output_index) += pulse(r) * lfm_waveform(k);
                    }
                }
            }
            range_pulse_map.row(n) = convolved_range;
        }

        Eigen::MatrixXcd range_pulse_noisy = range_pulse_map + noise_map;

        return RangePulseProduct{
            .samples = std::move(range_pulse_noisy)
        };

    }
    //have to create lfm waveform
    //convolve range pulse with waveform
    //Add noise
    //Add Clutter (small rcs and doppler targets with a distribution across ragne and doppler)
    //convolve the flipped conjugate to matched filter, or is this fft?
    // fft across pulses for doppler

    return std::nullopt;
}

Grid2D make_noisy_range_doppler_grid(
    const RangePulseProduct& product,
    const RadarParams& radar,
    int radar_entity_id
)
{
    const Eigen::MatrixXcd& range_pulse_noisy = product.samples;
    const double detectable_range_m = radar.mur_m - radar.mdr_m;
    const auto num_samples = range_pulse_noisy.cols();

    // Transpose the display grid so pulses run horizontally and range vertically.
    Grid2D range_doppler_noisy_grid{
        .entity_id = radar_entity_id,
        .system = "radar",
        .key = "range_doppler_noisy",
        .name = "Noisy Range-Doppler Map",
        .x_axis = Axis{
            .key = "pulse_index",
            .name = "Pulse",
            .unit = "",
            .kind = "sequence"
        },
        .y_axis = Axis{
            .key = "range_km",
            .name = "Range",
            .unit = "km",
            .kind = "continuous"
        },
        .value_unit = "dB",
        .rows = static_cast<std::size_t>(range_pulse_noisy.cols()),
        .columns = static_cast<std::size_t>(range_pulse_noisy.rows()),
        .presentation = Presentation{
            .order = 20
        }
    };

    range_doppler_noisy_grid.x_axis.values.reserve(
        range_doppler_noisy_grid.columns
    );
    for (Eigen::Index pulse = 0;
         pulse < range_pulse_noisy.rows();
         ++pulse)
    {
        range_doppler_noisy_grid.x_axis.values.push_back(
            static_cast<double>(pulse)
        );
    }

    range_doppler_noisy_grid.y_axis.values.reserve(
        range_doppler_noisy_grid.rows
    );
    for (Eigen::Index range_sample = 0;
         range_sample < range_pulse_noisy.cols();
         ++range_sample)
    {
        range_doppler_noisy_grid.y_axis.values.push_back(
            (
                radar.mdr_m +
                static_cast<double>(range_sample) *
                detectable_range_m /
                static_cast<double>(num_samples)
            ) / constants::meters_per_kilometer
        );
    }

    range_doppler_noisy_grid.values.reserve(
        range_doppler_noisy_grid.rows *
        range_doppler_noisy_grid.columns
    );
    for (Eigen::Index range_sample = 0;
         range_sample < range_pulse_noisy.cols();
         ++range_sample)
    {
        for (Eigen::Index pulse = 0;
             pulse < range_pulse_noisy.rows();
             ++pulse)
        {
            range_doppler_noisy_grid.values.push_back(
                20.0 * std::log10(
                    std::abs(range_pulse_noisy(pulse, range_sample))
                )
            );
        }
    }

    return range_doppler_noisy_grid;
}
