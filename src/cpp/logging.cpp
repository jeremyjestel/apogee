#include "logging.hpp"

#include <cmath>
#include <cstddef>

namespace
{
// Every logged kinematic vector currently uses the Earth-centered inertial frame.
constexpr const char* COORDINATE_FRAME = "eci";
}

void initialize_entity_state_logging(
    const std::vector<Entity>& entities,
    Result& result
)
{
    // The shared simulation-time axis is stored first so logging can append by index.
    result.axes.push_back(Axis{
        .key = "simulation_time",
        .name = "Simulation Time",
        .unit = "s",
        .kind = "time"
    });

    for (const Entity& entity : entities)
    {
        // Preserve entity identity separately so every series can refer to it by ID.
        result.entities.push_back(EntityDescriptor{
            .id = entity.id,
            .key = entity.key,
            .display_name = entity.display_name,
            .type = entity.type,
            .team = entity.team
        });

        // Keep position, velocity, and acceleration consecutive for each entity.
        result.vectors.push_back(VectorSeries3{
            .entity_id = entity.id,
            .system = "kinematics",
            .key = "position",
            .name = "Position",
            .unit = "m",
            .frame = COORDINATE_FRAME,
            .axis_key = "simulation_time"
        });
        result.vectors.push_back(VectorSeries3{
            .entity_id = entity.id,
            .system = "kinematics",
            .key = "velocity",
            .name = "Velocity",
            .unit = "m/s",
            .frame = COORDINATE_FRAME,
            .axis_key = "simulation_time"
        });
        result.vectors.push_back(VectorSeries3{
            .entity_id = entity.id,
            .system = "kinematics",
            .key = "acceleration",
            .name = "Acceleration",
            .unit = "m/s^2",
            .frame = COORDINATE_FRAME,
            .axis_key = "simulation_time"
        });

        // Speed is logged separately because it is a scalar derived from velocity.
        result.scalars.push_back(ScalarSeries{
            .entity_id = entity.id,
            .system = "kinematics",
            .key = "speed",
            .name = "Speed",
            .unit = "m/s",
            .axis_key = "simulation_time"
        });
    }
}


void log_entity_states(
    const std::vector<Entity>& entities,
    double time_s,
    Result& result
)
{
    // Initialization guarantees that the first axis is the shared simulation clock.
    result.axes[0].values.push_back(time_s);

    for (std::size_t index = 0; index < entities.size(); ++index)
    {
        const Entity& entity = entities[index];

        // Each entity owns three consecutive vectors in its initialization order.
        const std::size_t vector_index = index * 3;

        result.vectors[vector_index].values.push_back(entity.kinematics.pos_m);
        result.vectors[vector_index + 1].values.push_back(entity.kinematics.vel_mps);
        result.vectors[vector_index + 2].values.push_back(entity.kinematics.accel_mps2);

        // Convert the three velocity components into the scalar speed magnitude.
        const Vec3& velocity = entity.kinematics.vel_mps;
        result.scalars[index].values.push_back(
            std::sqrt(
                velocity.x * velocity.x +
                velocity.y * velocity.y +
                velocity.z * velocity.z
            )
        );
    }
}
