#include "sensors/radar/models/radar_returns.hpp"

#include <cmath>

#include "math/constants.hpp"
#include "math/dsp/convolve.hpp"
#include "math/gaussian.hpp"
#include "math/types.hpp"
#include "sensors/radar/models/radar_range_equation.hpp"


// Goal is to just return the complex range pulse map here
namespace apogee{
    void generate_returns(const KinematicStateECI &entity_motion,
        RadarComponent &radar,
        const std::vector<Entity> &targets,
        std::mt19937 &rng){

        const RadarParams &params = radar.params;

        Index range_n_samples = static_cast<Index>(std::round(params.sampling_rate_hz * (params.pri_s - params.pw_s)));
        VecX range_swath = VecX::LinSpaced(range_n_samples, params.mdr_m, params.mur_m);
        VecX pulse_swath = VecX::LinSpaced(params.pulse_num, 1, params.pulse_num);
        CMatX rp_delta_mat = CMatX::Zero(range_n_samples, params.pulse_num);
        CMatX rp_mat = CMatX::Zero(rp_delta_mat.rows(), rp_delta_mat.cols());
        Index target_range_ind;

        int pulse_n_samples = params.sampling_rate_hz * params.pw_s;
        VecX pulse_t_s = VecX::LinSpaced(pulse_n_samples, 0, params.pw_s);
        CVecX pulse_signal = (constants::j * params.frequency_hz * pulse_t_s).array().exp().matrix();
        RadarEquationResult rre_result;

        for (auto& target : targets) {
            Vec3 rel_pos_m = entity_motion.pos_m - target.kinematics.pos_m;
            double rel_range = rel_pos_m.norm();
            Vec3 rel_vel = entity_motion.vel_mps - target.kinematics.vel_mps;
            double radial_velocity_mps = rel_vel.dot(rel_pos_m.normalized()); // projects on to radial direction
            VecX range_progression = (rel_range + params.pri_s * radial_velocity_mps * pulse_swath.array()).matrix();
            double _ = (range_swath.array() - rel_range).abs().minCoeff(&target_range_ind);
            rre_result = radar_range_equation(params, target.radar_signature_dbsm, rel_range);
            rp_delta_mat.row(target_range_ind) = rre_result.signal_power_w * (constants::j * params.wavenumber * 2.0 * range_progression.array()).exp().matrix().transpose(); // Dirac delta here

        }
        CMatX noise_mat = std::sqrt(rre_result.noise_power_w) * crandn(rp_mat.rows(), rp_mat.cols(), rng);
        CMatX rp_noisy_mat = rp_delta_mat + noise_mat;
        for (int pulse_idx = 0; pulse_idx < params.pulse_num;pulse_idx++){
            rp_mat.col(pulse_idx) = convolve(rp_delta_mat.col(pulse_idx), pulse_signal, "same");
        }
        radar.state.range_pulse_map = rp_mat;
        


    }
}
