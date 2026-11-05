#pragma once

#include "math/types.hpp"

namespace apogee
{
	struct Entity;

	Vec3 prop_nav(const Entity &entity, const Entity &target);
}
