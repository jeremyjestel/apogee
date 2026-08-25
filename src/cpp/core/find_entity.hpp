#pragma once

#include <string>
#include <vector>

#include "core/entity.hpp"

// Find one runtime entity by its stable scenario key.
Entity& find_entity(std::vector<Entity>& entities, const std::string& key);
