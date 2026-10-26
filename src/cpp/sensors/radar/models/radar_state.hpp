#pragma once

#include <cstdint>
#include <random>
#include <utility>

#include "core/data_fields.hpp"
#include "math/types.hpp"
#include "params.hpp"

namespace apogee
{
	// RadarState contains only measurements that may change while the simulation runs.
	struct RadarState
	{
		bool enabled = true;
		double last_update_s = 0.0;
		double target_range_m = 0.0;
		double target_vel_mps = 0.0;
		double signal_to_noise_db = 0.0;
		CMatX range_pulse_map;

		static constexpr auto data_fields()
		{
			return std::tuple{ data_field("enabled", &RadarState::enabled, "Enabled"),
				data_field("last_update_s", &RadarState::last_update_s, "Last update", "s"),
				data_field("target_range_m", &RadarState::target_range_m, "Target range", "m"),
				data_field("target_vel_mps", &RadarState::target_vel_mps, "Target velocity", "m/s"),
				data_field("signal_to_noise_db", &RadarState::signal_to_noise_db, "Signal-to-noise ratio", "dB"),
				data_field("range_pulse_map", &RadarState::range_pulse_map, "Range-pulse map") };
		}
	};

	struct RadarModule
	{
		// Each module owns a finalized snapshot so parameter edits cannot leak into a run.
		explicit RadarModule(RadarParams input, std::uint32_t noise_seed = std::random_device{}())
			: p(finalize_radar_params(std::move(input))), noise_generator(noise_seed)
		{
		}

		const RadarParams p;
		RadarState state;
		std::mt19937 noise_generator;
	};

} // namespace apogee
