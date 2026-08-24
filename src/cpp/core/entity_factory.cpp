#include "core/entity_factory.hpp"

Entity instantiate_entity(const EntityDefinition& definition)
{
    // Copy scenario configuration into a fresh mutable entity for this run.
    Entity entity{
        .id = definition.id,
        .key = definition.key,
        .display_name = definition.display_name,
        .type = definition.type,
        .team = definition.team,
        .kinematics = definition.initial_kinematics,
        .radar_signature_dbsm = definition.radar_signature_dbsm
    };

    // Constructing the optional module also finalizes its immutable radar parameters.
    if (definition.radar)
    {
        entity.radar.emplace(*definition.radar);
    }

    return entity;
}
