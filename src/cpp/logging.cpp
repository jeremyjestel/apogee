#include "logging.hpp"

#include <algorithm>
#include <cstddef>
#include <cmath>
#include <stdexcept>
#include <string>
#include <unordered_set>


namespace
{
constexpr const char* SIMULATION_TIME_AXIS = "simulation_time";

Axis& require_axis(Result& result, const std::string& key)
{
    auto axis = std::find_if(
        result.axes.begin(),
        result.axes.end(),
        [&key](const Axis& candidate) { return candidate.key == key; }
    );

    if (axis == result.axes.end())
    {
        throw std::logic_error("Missing result axis: " + key);
    }

    return *axis;
}

VectorSeries3& require_vector_series(
    Result& result,
    int entity_id,
    const std::string& key
)
{
    auto series = std::find_if(
        result.vectors.begin(),
        result.vectors.end(),
        [entity_id, &key](const VectorSeries3& candidate)
        {
            return candidate.entity_id == entity_id &&
                candidate.system == "kinematics" &&
                candidate.key == key;
        }
    );

    if (series == result.vectors.end())
    {
        throw std::logic_error("Missing vector result series: " + key);
    }

    return *series;
}

ScalarSeries& require_scalar_series(
    Result& result,
    int entity_id,
    const std::string& key
)
{
    auto series = std::find_if(
        result.scalars.begin(),
        result.scalars.end(),
        [entity_id, &key](const ScalarSeries& candidate)
        {
            return candidate.entity_id == entity_id &&
                candidate.system == "kinematics" &&
                candidate.key == key;
        }
    );

    if (series == result.scalars.end())
    {
        throw std::logic_error("Missing scalar result series: " + key);
    }

    return *series;
}
}


void initialize_entity_state_logging(
    const std::vector<Entity>& entities,
    const std::string& coordinate_frame,
    Result& result
)
{
    if (entities.empty())
    {
        throw std::invalid_argument("At least one entity is required for logging");
    }
    if (coordinate_frame.empty())
    {
        throw std::invalid_argument("The coordinate frame cannot be empty");
    }
    if (!result.entities.empty() || !result.axes.empty() ||
        !result.scalars.empty() || !result.vectors.empty() ||
        !result.grids.empty())
    {
        throw std::logic_error("Entity state logging was already initialized");
    }

    std::unordered_set<int> entity_ids;
    std::unordered_set<std::string> entity_keys;

    for (const Entity& entity : entities)
    {
        if (entity.id <= 0)
        {
            throw std::invalid_argument("Entity IDs must be positive");
        }
        if (entity.key.empty() || entity.name.empty())
        {
            throw std::invalid_argument("Entity keys and names cannot be empty");
        }
        if (!entity_ids.insert(entity.id).second)
        {
            throw std::invalid_argument("Duplicate entity ID");
        }
        if (!entity_keys.insert(entity.key).second)
        {
            throw std::invalid_argument("Duplicate entity key: " + entity.key);
        }
    }

    result.axes.push_back(Axis{
        .key = SIMULATION_TIME_AXIS,
        .name = "Simulation Time",
        .unit = "s",
        .kind = "time"
    });

    for (const Entity& entity : entities)
    {
        result.entities.push_back(EntityDescriptor{
            .id = entity.id,
            .key = entity.key,
            .display_name = entity.name,
            .type = entity.type,
            .team = entity.team
        });

        result.vectors.push_back(VectorSeries3{
            .entity_id = entity.id,
            .system = "kinematics",
            .key = "position",
            .name = "Position",
            .unit = "m",
            .frame = coordinate_frame,
            .axis_key = SIMULATION_TIME_AXIS
        });
        result.vectors.push_back(VectorSeries3{
            .entity_id = entity.id,
            .system = "kinematics",
            .key = "velocity",
            .name = "Velocity",
            .unit = "m/s",
            .frame = coordinate_frame,
            .axis_key = SIMULATION_TIME_AXIS
        });
        result.vectors.push_back(VectorSeries3{
            .entity_id = entity.id,
            .system = "kinematics",
            .key = "acceleration",
            .name = "Acceleration",
            .unit = "m/s^2",
            .frame = coordinate_frame,
            .axis_key = SIMULATION_TIME_AXIS
        });
        result.scalars.push_back(ScalarSeries{
            .entity_id = entity.id,
            .system = "kinematics",
            .key = "speed",
            .name = "Speed",
            .unit = "m/s",
            .axis_key = SIMULATION_TIME_AXIS
        });
    }
}


void log_entity_states(
    const std::vector<Entity>& entities,
    double time_s,
    Result& result
)
{
    if (!std::isfinite(time_s))
    {
        throw std::invalid_argument("Simulation time must be finite");
    }

    Axis& time_axis = require_axis(result, SIMULATION_TIME_AXIS);
    if (!time_axis.values.empty() && time_s <= time_axis.values.back())
    {
        throw std::invalid_argument("Simulation time must increase monotonically");
    }

    const std::size_t expected_samples = time_axis.values.size();
    if (entities.size() != result.entities.size())
    {
        throw std::logic_error(
            "Logged entity set does not match initialized entity descriptors"
        );
    }

    std::unordered_set<int> logged_entity_ids;
    for (const Entity& entity : entities)
    {
        if (!logged_entity_ids.insert(entity.id).second)
        {
            throw std::logic_error("Logged entity IDs must be unique");
        }

        const auto descriptor = std::find_if(
            result.entities.begin(),
            result.entities.end(),
            [&entity](const EntityDescriptor& candidate)
            {
                return candidate.id == entity.id && candidate.key == entity.key;
            }
        );
        if (descriptor == result.entities.end())
        {
            throw std::logic_error(
                "Logged entity does not match an initialized descriptor"
            );
        }

        const Vec3* state_vectors[] = {
            &entity.kinematics.pos_m,
            &entity.kinematics.vel_mps,
            &entity.kinematics.accel_mps2
        };
        for (const Vec3* value : state_vectors)
        {
            if (!std::isfinite(value->x) ||
                !std::isfinite(value->y) ||
                !std::isfinite(value->z))
            {
                throw std::invalid_argument(
                    "Entity kinematic state must contain only finite values"
                );
            }
        }

        if (require_vector_series(result, entity.id, "position").values.size() != expected_samples ||
            require_vector_series(result, entity.id, "velocity").values.size() != expected_samples ||
            require_vector_series(result, entity.id, "acceleration").values.size() != expected_samples ||
            require_scalar_series(result, entity.id, "speed").values.size() != expected_samples)
        {
            throw std::logic_error("Entity result series are not aligned with simulation time");
        }
    }

    time_axis.values.push_back(time_s);

    for (const Entity& entity : entities)
    {
        require_vector_series(result, entity.id, "position").values.push_back(
            entity.kinematics.pos_m
        );
        require_vector_series(result, entity.id, "velocity").values.push_back(
            entity.kinematics.vel_mps
        );
        require_vector_series(result, entity.id, "acceleration").values.push_back(
            entity.kinematics.accel_mps2
        );

        const Vec3& velocity = entity.kinematics.vel_mps;
        require_scalar_series(result, entity.id, "speed").values.push_back(
            std::sqrt(
                velocity.x * velocity.x +
                velocity.y * velocity.y +
                velocity.z * velocity.z
            )
        );
    }
}
