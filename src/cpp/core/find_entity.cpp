#include "core/find_entity.hpp"

#include <algorithm>
#include <stdexcept>

Entity& find_entity(std::vector<Entity>& entities, const std::string& key)
{
    const auto match = std::find_if(
        entities.begin(),
        entities.end(),
        [&](const Entity& entity)
        {
            return entity.key == key;
        }
    );

    if (match == entities.end())
    {
        throw std::invalid_argument("Scenario is missing entity: " + key);
    }

    return *match;
}
