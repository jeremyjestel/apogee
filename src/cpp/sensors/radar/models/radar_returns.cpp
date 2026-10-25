#pragma once
#include "math/types.hpp"
#include "Entity.hpp"
#include <cmath>


// Goal is to just return the complex range pulse map here
namespace apogee{
    void generate_returns(&KinematicState entity_motion, &RadarState radar, &std::vector<Entity> targets){

        range_n_samples = std::round(radar.fs_hz * (radar.mur_m - radar.mdr_m));
        range_swath = VecX::LinSpaced(range_n_samples, radar.mdr_m, radar.mur_m)
        pulse_swath = VecX::LinSpaced(radar.num_pulses, 1, radar.num_pulses);
        MatX range_pulse_base_mat = MatX::Zeros(radar.num_pulses, range_n_samples);

        int pulse_n_samples = radar.fs_hz * radar.pw_s;
        VecX pulse_t_s = VecX::LinSpaced(pulse_n_samples, 0, radar.pw_s);
        VecX pulse_signal = (constants::j * radar.freq_hz * pulse_t_s).exp();

        for (target : targets) {
            rel_pos_m = entity_motion.pos_m - target.kinematic_state.pos_m;
            rel_range = rel_pos.norm();
            rel_vel = entity_motion.vel_mps - target.kinematic_state.vel_mps;
            radial_velocity_mps = rel_vel.dot(rel_range.normalized());
            Index target_range_ind
            range_progression = rel_range + radar.pri_s * entity_motion.vel_mps * pulse_swath.array();
            sample_diff_ignore = (range_swath.array() - rel_range).abs().minCoeff(&target_range_ind);
            range_pulse_base_mat.row(target_range_ind) = (constants::j * radar.wavenumber * 2 * range_progression.array).exp().matrix; // Dirac delta here

       }

        CMatX range_pulse_mat = MatX::Zeros(range_pulse_base_mat.rows(), range_pulse_base_mat.cols());
        for (pulse_idx = 0; pulse_idx < radar.num_pulses;pulse_idx++){
            range_pulse_mat.col(pulse_idx) = convolve(range_pulse_base_mat.col(pulse_idx), pulse_signal, "same");
        }
        radar.range_pulse_map = range_pulse_mat;
        


    }
}
