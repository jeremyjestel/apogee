#pragma once

struct Vec3
{
    double x = 0.0;
    double y = 0.0;
    double z = 0.0;

    constexpr Vec3 operator*(double scalar) const noexcept
    {
        return {x * scalar, y * scalar, z * scalar};
    }

    constexpr Vec3& operator+=(const Vec3& other) noexcept
    {
        x += other.x;
        y += other.y;
        z += other.z;
        return *this;
    }
};
