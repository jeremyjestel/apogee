#include "sensors/radar/radar_system.hpp"

#include "sensors/radar/models/range_doppler_map.hpp"

namespace apogee
{
	std::optional<RangePulseProduct> update_radar(Entity &radar, const Entity &target)
	{
		// Entities without a radar component have no radar processing to perform.
		if (!radar.radar)
		{
			return std::nullopt;
		}

		// Pass only the owned module and the two kinematic states to processing.
		return range_doppler_map(
			*radar.radar, radar.kinematics, target.kinematics, target.radar_signature_dbsm);
	}

} // namespace apogee
