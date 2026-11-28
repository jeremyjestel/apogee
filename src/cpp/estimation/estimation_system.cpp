#include "estimation/estimation_system.hpp"

#include "core/entity.hpp"

namespace apogee
{
	void estimate(std::vector<Entity> &entities, [[maybe_unused]] double sim_time_s)
	{
		for (auto &entity : entities)
		{
			if (!entity.active || !entity.belief.enabled)
				continue;

			// 1. Read entity.belief.pending_detections from ALL of this entity's sensors.
			//    Process by measurement time, retaining future detections and defining
			//    an explicit policy for detections older than an existing track state.
			//    Radar target truth snapshots are not measurements.

			// 2. Predict candidate tracks to each detection's time before association.
			//    x_hat = f(x, dt), P_hat = F * P * F.transpose() + Q(dt).

			// 3. Gate and associate against the SAME entity.belief.tracks collection.
			//    Sensor identity records provenance; it does not partition tracks.
			//    Select h/H using detection.kind and pose, and R from its covariance.

			// 4. Call update_track for each associated detection. Radar and EO/IR can
			//    correct the same track while keeping their native measurement spaces.

			// 5. Initialize tentative tracks from unassigned detections, without
			//    inventing range for angle-only observations. Assign local track IDs.
			//    After processing, predict to sim_time_s and retire stale tracks.
			//    Remove only successfully handled detections from the shared inbox.
			//    Until these stages exist, preserve both tracks and pending detections.
		}
	}
}
