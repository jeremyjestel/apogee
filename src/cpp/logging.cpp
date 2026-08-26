#include "logging.hpp"

#include <cmath>
#include <cstddef>

#include "core/constants.hpp"

LoggingLayout initialize_entity_state_logging(
    const std::vector<Entity>& entities,
    Result& result
)
{
    LoggingLayout layout;
    layout.simulation_time_axis = result.axes.size();
    layout.entities.reserve(entities.size());

    result.axes.push_back(Axis{
        .key = "simulation_time",
        .name = "Simulation Time",
        .unit = "s",
        .kind = "time"
    });

    for (const Entity& entity : entities)
    {
        EntityLoggingHandles handles;

        // Preserve entity identity separately so every series can refer to it by ID.
        result.entities.push_back(EntityDescriptor{
            .id = entity.id,
            .key = entity.key,
            .display_name = entity.display_name,
            .type = entity.type,
            .team = entity.team
        });

        // Keep position, velocity, and acceleration consecutive for each entity.
        handles.position_series = result.vectors.size();
        result.vectors.push_back(VectorSeries3{
            .entity_id = entity.id,
            .system = "kinematics",
            .key = "position",
            .name = "Position",
            .unit = "m",
            .frame = constants::eci_frame,
            .axis_key = "simulation_time"
        });
        handles.velocity_series = result.vectors.size();
        result.vectors.push_back(VectorSeries3{
            .entity_id = entity.id,
            .system = "kinematics",
            .key = "velocity",
            .name = "Velocity",
            .unit = "m/s",
            .frame = constants::eci_frame,
            .axis_key = "simulation_time"
        });
        handles.acceleration_series = result.vectors.size();
        result.vectors.push_back(VectorSeries3{
            .entity_id = entity.id,
            .system = "kinematics",
            .key = "acceleration",
            .name = "Acceleration",
            .unit = "m/s^2",
            .frame = constants::eci_frame,
            .axis_key = "simulation_time"
        });

        // Speed is logged separately because it is a scalar derived from velocity.
        handles.speed_series = result.scalars.size();
        result.scalars.push_back(ScalarSeries{
            .entity_id = entity.id,
            .system = "kinematics",
            .key = "speed",
            .name = "Speed",
            .unit = "m/s",
            .axis_key = "simulation_time"
        });

        layout.entities.push_back(handles);
    }

    return layout;
}


void log_entity_states(
    const std::vector<Entity>& entities,
    const LoggingLayout& layout,
    double time_s,
    Result& result
)
{
    result.axes[layout.simulation_time_axis].values.push_back(time_s);

    for (std::size_t index = 0; index < entities.size(); ++index)
    {
        const Entity& entity = entities[index];
        const EntityLoggingHandles& handles = layout.entities[index];

        result.vectors[handles.position_series].values.push_back(
            entity.kinematics.pos_m
        );
        result.vectors[handles.velocity_series].values.push_back(
            entity.kinematics.vel_mps
        );
        result.vectors[handles.acceleration_series].values.push_back(
            entity.kinematics.accel_mps2
        );

        // Convert the three velocity components into the scalar speed magnitude.
        const Vec3& velocity = entity.kinematics.vel_mps;
        result.scalars[handles.speed_series].values.push_back(
            std::sqrt(
                velocity.x * velocity.x +
                velocity.y * velocity.y +
                velocity.z * velocity.z
            )
        );
    }
}
