#pragma once

#include <random>
#include <cmath>
#include "math/types.hpp"

namespace apogee
{
    // Real Gaussian vector
    inline VecX randn(Eigen::Index size, std::mt19937& rng)
    {
        std::normal_distribution<double> dist(0.0, 1.0);

        return VecX::NullaryExpr(size, [&]() {
            return dist(rng);
        });
    }

    // Real Gaussian matrix
    inline MatX randn(
        Eigen::Index rows,
        Eigen::Index cols,
        std::mt19937& rng)
    {
        std::normal_distribution<double> dist(0.0, 1.0);

        return MatX::NullaryExpr(rows, cols, [&]() {
            return dist(rng);
        });
    }

    // Complex Gaussian vector
    inline CVecX crandn(Eigen::Index size, std::mt19937& rng)
    {
        std::normal_distribution<double> dist(
            0.0, 1.0 / std::sqrt(2.0));

        return CVecX::NullaryExpr(size, [&]() {
            return Complex(dist(rng), dist(rng));
        });
    }

    // Complex Gaussian matrix
    inline CMatX crandn(
        Eigen::Index rows,
        Eigen::Index cols,
        std::mt19937& rng)
    {
        std::normal_distribution<double> dist(
            0.0, 1.0 / std::sqrt(2.0));

        return CMatX::NullaryExpr(rows, cols, [&]() {
            return Complex(dist(rng), dist(rng));
        });
    }
}