#include <cmath>
#include <complex>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

#include "core/entity.hpp"
#include "math/constants.hpp"
#include "sensors/radar/models/radar_processing.hpp"
#include "sensors/radar/models/radar_range_equation.hpp"
#include "sensors/radar/models/radar_returns.hpp"

namespace
{
	using namespace apogee;

	void check(bool condition, const std::string &message)
	{
		if (!condition) throw std::runtime_error(message);
	}

	void check_close(Complex actual, Complex expected, double tolerance,
		const std::string &message)
	{
		check(std::isfinite(actual.real()) && std::isfinite(actual.imag()) &&
			std::abs(actual - expected) <= tolerance, message);
	}

	RadarComponent synthetic_echo(int waveform_samples, int pulses, int doppler_bin)
	{
		RadarComponent radar;
		radar.params.pulse_num = pulses;
		radar.params.doppler_zero_pad_factor = 1;
		radar.params.range_window = "rectangular";
		radar.params.doppler_window = "rectangular";
		radar.state.wf.resize(waveform_samples);
		for (int sample = 0; sample < waveform_samples; ++sample)
			radar.state.wf[sample] = std::polar(1.0, 0.33 * sample * sample - 0.21 * sample);
		radar.state.range_pulse_map = CMatX::Zero(19, pulses);
		for (int pulse = 0; pulse < pulses; ++pulse)
		{
			const Complex phase = std::polar(1.0,
				2.0 * constants::pi * doppler_bin * pulse / pulses);
			// A return starts at its measured range bin, without shifting by half the pulse.
			radar.state.range_pulse_map.col(pulse).segment(6, waveform_samples) =
				radar.state.wf * phase;
		}
		return radar;
	}

	void test_range_alignment_and_signed_doppler()
	{
		for (const int waveform_samples : { 3, 4, 5 })
			for (const int pulses : { 7, 8 })
				for (const int doppler_bin : { -2, 0, 2 })
				{
					auto radar = synthetic_echo(waveform_samples, pulses, doppler_bin);
					const CMatX raw = radar.state.range_pulse_map;
					process_returns(radar);
					const auto &rd = radar.state.range_doppler_map;
					const auto &rv = radar.state.range_velocity_map;
					check(rd.rows() == raw.rows() && rd.cols() == raw.cols(),
						"Processing must preserve range rows and pulse columns.");
					check(rd.size() > 0 && rv.size() > 0 &&
						rv.rows() == raw.rows() && rv.cols() == raw.cols() && rv == rd,
						"Range-Doppler and range-velocity maps must both retain the same processed bins.");
					check(radar.state.range_pulse_map == raw,
						"Processing must preserve the raw returns.");
					Index row = -1, column = -1;
					rd.cwiseAbs().maxCoeff(&row, &column);
					check(row == 6,
						"Odd and even matched filters must preserve the return's range bin.");
					check(column == pulses / 2 + doppler_bin,
						"Doppler bins must be centered and preserve their sign for odd/even FFT sizes.");
					check_close(rd(6, column), Complex(waveform_samples * pulses, 0.0), 1.0e-10,
						"Matched filtering and Doppler FFT must retain coherent amplitude gain.");
					for (int other = 0; other < pulses; ++other)
						if (other != column)
							check(std::abs(rd(6, other)) < 1.0e-10,
								"An exact Doppler-bin tone must not leak into other rectangular-window bins.");
				}
	}

	void test_independent_window_dimensions()
	{
		auto radar = synthetic_echo(5, 7, 0);
		radar.params.range_window = "hann";
		radar.params.doppler_window = "hamming";
		process_returns(radar);
		// Hann(5) sums to 2; Hamming(7) sums to 3.32. Neither has 19 range samples.
		check_close(radar.state.range_doppler_map(6, 3), Complex(6.64, 0.0), 1.0e-11,
			"Range weighting must use waveform length and Doppler weighting must use pulse count.");

		auto singleton = synthetic_echo(1, 1, 0);
		singleton.params.range_window = "hann";
		singleton.params.doppler_window = "hann";
		process_returns(singleton);
		check_close(singleton.state.range_doppler_map(6, 0), Complex(1.0, 0.0), 1.0e-12,
			"A one-sample waveform and one-pulse FFT must remain valid.");
	}

	RadarComponent make_radar()
	{
		RadarComponent radar;
		RadarParams inputs;
		inputs.frequency_hz = 1.0e9;
		inputs.power_dbw = 60.0;
		inputs.bandwidth_hz = 1.0e6;
		// Keep the five-sample pulse away from a floating-point truncation boundary.
		inputs.pw_us = 1.75;
		inputs.pri_us = 21.75;
		inputs.pulse_num = 8;
		inputs.doppler_zero_pad_factor = 1;
		inputs.range_window = "rectangular";
		inputs.doppler_window = "rectangular";
		radar.params = finalize_radar_params(inputs);
		return radar;
	}

	Entity target_at_bin(const RadarComponent &radar, int bin, double radial_velocity_mps = 0.0)
	{
		Entity target;
		target.id = bin;
		target.kinematics.pos_m.x() = radar.params.mdr_m +
			bin * constants::speed_of_light_mps / (2.0 * radar.params.sampling_rate_hz);
		target.kinematics.vel_mps.x() = radial_velocity_mps;
		return target;
	}

	void test_seeded_noise_and_baseband_waveform()
	{
		auto first = make_radar();
		auto repeated = make_radar();
		std::mt19937 first_rng(12345), repeated_rng(12345);
		const KinematicStateECI observer;
		generate_returns(observer, first, {}, first_rng);
		generate_returns(observer, repeated, {}, repeated_rng);
		check(first.state.range_pulse_map.rows() == 60 && first.state.range_pulse_map.cols() == 8,
			"No-target scans must retain the complete range-pulse grid.");
		check(first.state.range_pulse_map == repeated.state.range_pulse_map,
			"The same seed and inputs must reproduce raw receiver noise.");
		const double noise_power = constants::boltzmann_constant_j_per_k *
			constants::reference_noise_temperature_k * first.params.noise_figure_lin *
			first.params.bandwidth_hz;
		const double measured_noise_power = first.state.range_pulse_map.squaredNorm() /
			first.state.range_pulse_map.size();
		check(measured_noise_power > 0.7 * noise_power && measured_noise_power < 1.3 * noise_power,
			"No-target scans must contain unfiltered complex noise with the configured receiver power.");
		check(first.state.wf.size() == 5,
			"The baseband waveform must contain fs times pulse-width samples.");
		for (int sample = 0; sample < first.state.wf.size(); ++sample)
		{
			const double time_s = sample / first.params.sampling_rate_hz;
			const double phase = constants::pi * first.params.bandwidth_hz / first.params.pw_s *
				time_s * (time_s - first.params.pw_s);
			check_close(first.state.wf[sample], std::polar(1.0, phase), 1.0e-12,
				"Waveform samples must use the baseband LFM phase and n/fs time grid.");
		}
		const CMatX previous = first.state.range_pulse_map;
		generate_returns(observer, first, {}, first_rng);
		check(first.state.range_pulse_map != previous,
			"A new scan must advance the receiver-noise generator.");
	}

	void test_target_amplitude_superposition_and_swath()
	{
		auto noise = make_radar();
		auto one = make_radar();
		auto two = make_radar();
		auto outside = make_radar();
		const Entity target = target_at_bin(one, 20);
		std::mt19937 noise_rng(6789), one_rng(6789), two_rng(6789), outside_rng(6789);
		const KinematicStateECI observer;
		generate_returns(observer, noise, {}, noise_rng);
		generate_returns(observer, one, { target }, one_rng);
		generate_returns(observer, two, { target, target }, two_rng);
		const CMatX signal = one.state.range_pulse_map - noise.state.range_pulse_map;
		const CMatX doubled_signal = two.state.range_pulse_map - noise.state.range_pulse_map;
		check(signal.norm() > 0.0 && (doubled_signal - 2.0 * signal).norm() < signal.norm() * 1.0e-12,
			"Targets in the same range bin must add coherently instead of overwriting each other.");
		const double range_m = target.kinematics.pos_m.norm();
		const double power_w = radar_range_equation(one.params, target.radar_signature_dbsm,
			range_m).signal_power_w;
		const Complex expected = std::polar(std::sqrt(power_w), 2.0 * one.params.wavenumber * range_m);
		check_close(signal(20, 0), expected, std::sqrt(power_w) * 1.0e-11,
			"A target's complex voltage must scale with the square root of received power.");
		check(signal.topRows(20).norm() < signal.norm() * 1.0e-12 &&
			signal.bottomRows(35).norm() < signal.norm() * 1.0e-12,
			"A causal target echo must occupy only its waveform's range samples.");

		Entity too_near = target, too_far = target;
		too_near.kinematics.pos_m.x() = outside.params.mdr_m / 2.0;
		too_far.kinematics.pos_m.x() = outside.params.mur_m * 2.0;
		generate_returns(observer, outside, { too_near, too_far }, outside_rng);
		check(outside.state.range_pulse_map == noise.state.range_pulse_map,
			"Targets outside the receive swath must be omitted rather than clamped to edge bins.");
	}

	void test_end_to_end_target_doppler_sign()
	{
		for (const int bin : { -2, 2 })
		{
			auto radar = make_radar();
			auto noise = make_radar();
			const double velocity_mps = bin * radar.params.wavelength_m /
				(2.0 * radar.params.pulse_num * radar.params.pri_s);
			const Entity target = target_at_bin(radar, 20, velocity_mps);
			std::mt19937 signal_rng(42), noise_rng(42);
			const KinematicStateECI observer;
			generate_returns(observer, radar, { target }, signal_rng);
			generate_returns(observer, noise, {}, noise_rng);
			radar.state.range_pulse_map -= noise.state.range_pulse_map;
			process_returns(radar);
			Index row = -1, column = -1;
			radar.state.range_doppler_map.cwiseAbs().maxCoeff(&row, &column);
			check(row == 20 && column == radar.params.pulse_num / 2 + bin,
				"Generated approaching/receding echoes must compress at the correct signed Doppler and range bins.");
		}
	}
}

int main()
{
	try
	{
		test_range_alignment_and_signed_doppler();
		test_independent_window_dimensions();
		test_seeded_noise_and_baseband_waveform();
		test_target_amplitude_superposition_and_swath();
		test_end_to_end_target_doppler_sign();
		std::cout << "C++ radar processing checks passed.\n";
		return 0;
	}
	catch (const std::exception &error)
	{
		std::cerr << error.what() << '\n';
		return 1;
	}
}
