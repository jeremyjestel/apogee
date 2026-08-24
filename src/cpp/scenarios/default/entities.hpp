#pragma once

#include "core/entity_definition.hpp"

// Each factory owns the scenario-specific defaults for exactly one fixed entity.
EntityDefinition make_blue_radar_definition();
EntityDefinition make_blue_satellite_definition();
EntityDefinition make_red_missile_definition();
EntityDefinition make_blue_interceptor_definition();
