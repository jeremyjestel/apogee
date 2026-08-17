#include "logging.hpp"

#include <algorithm>
#include <string>


namespace
{
void append_vector(
    SimulationData3D& simulation_data,
    const std::string& entity_name,
    const std::string& state_name,
    const std::string& unit,
    const Vec3& value
)
{
    auto series = std::find_if(
        simulation_data.outputs.begin(),
        simulation_data.outputs.end(),
        [&entity_name, &state_name](const VectorDataSeries& output)
        {
            return output.entity_name == entity_name && output.name == state_name;
        }
    );

    if (series == simulation_data.outputs.end())
    {
        simulation_data.outputs.push_back(VectorDataSeries{
            entity_name,
            state_name,
            unit,
            {value.x},
            {value.y},
            {value.z}
        });
        return;
    }

    series->x.push_back(value.x);
    series->y.push_back(value.y);
    series->z.push_back(value.z);
}
}

void log_entity_states(
    const std::vector<Entity>& entities,
    double time_s,
    SimulationData3D& simulation_data
)
{
    simulation_data.times_s.push_back(time_s);

    for (const Entity& entity : entities)
    {
        append_vector(
            simulation_data,
            entity.name,
            "Position",
            "m",
            entity.kinematics.pos_m
        );
        append_vector(
            simulation_data,
            entity.name,
            "Velocity",
            "m/s",
            entity.kinematics.vel_mps
        );
        append_vector(
            simulation_data,
            entity.name,
            "Acceleration",
            "m/s^2",
            entity.kinematics.accel_mps2
        );
    }
}
