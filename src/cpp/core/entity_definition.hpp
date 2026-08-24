#pragma once

#include <optional>
#include <string>
#include <tuple>

#include "core/kinematic_state.hpp"
#include "params.hpp"

// Configuration used to create one runtime Entity at the start of a run.
struct EntityDefinition
{
    int id = 0;
    std::string key;
    std::string display_name;
    std::string type;
    std::string team;
    KinematicState initial_kinematics;
    // An engaged optional attaches radar behavior when this definition is instantiated.
    std::optional<RadarParams> radar;
    double radar_signature_dbsm = 0.0;

    // Entity-wide editable values are exposed through the same descriptor mechanism.
    static constexpr auto fields()
    {
        return std::tuple{
            parameter(
                "radar_signature_dbsm",
                &EntityDefinition::radar_signature_dbsm,
                "Radar signature",
                "dBsm"
            )
        };
    }
};
