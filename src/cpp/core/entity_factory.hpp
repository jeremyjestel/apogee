#pragma once

#include "core/entity.hpp"
#include "core/entity_definition.hpp"

// Turn a reusable scenario definition into independent runtime component data.
Entity instantiate_entity(const EntityDefinition& definition);
