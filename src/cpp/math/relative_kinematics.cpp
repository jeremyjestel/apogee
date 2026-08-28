#include "math/relative_kinematics.hpp"

#include <cmath>

double difference_magnitude(const Vec3& a, const Vec3& b)
{
    // Apply the Euclidean norm to the coordinate difference between both points.
    const double dx = a.x - b.x;
    const double dy = a.y - b.y;
    const double dz = a.z - b.z;

    return std::sqrt(dx * dx + dy * dy + dz * dz);
}
