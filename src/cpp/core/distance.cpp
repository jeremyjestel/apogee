#include "distance.hpp"
#include "vec3.hpp"
#include <cmath> 

double get_3d_distance(Vec3& a, Vec3& b)
{
    double dist_x = a.x - b.x;
    double dist_y = a.y - b.y;
    double dist_z = a.z - b.z;
    double dist_3d = std::sqrt(dist_x*dist_x + dist_y * dist_y + dist_z * dist_z);
    return dist_3d;
}
