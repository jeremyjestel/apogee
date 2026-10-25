#pragma once

#include <complex>
#include <Eigen/Dense>
#include <Eigen/Geometry>

namespace apogee
{
    // Scalar types
    using Complex = std::complex<double>;

    // Dynamic-size vectors
    using VecX = Eigen::VectorXd;
    using CVecX = Eigen::VectorXcd;

    // Fixed-size vectors
    using Vec2 = Eigen::Vector2d;
    using Vec3 = Eigen::Vector3d;
    using Vec4 = Eigen::Vector4d;
    using Vec6 = Eigen::Matrix<double, 6, 1>;

    // Fixed-size complex vectors
    using CVec2 = Eigen::Vector2cd;
    using CVec3 = Eigen::Vector3cd;
    using CVec4 = Eigen::Vector4cd;
    using CVec6 = Eigen::Matrix<Complex, 6, 1>;

    // Fixed-size matrices
    using Mat2 = Eigen::Matrix2d;
    using Mat3 = Eigen::Matrix3d;
    using Mat4 = Eigen::Matrix4d;
    using Mat6 = Eigen::Matrix<double, 6, 6>;

    // Fixed-size complex matrices
    using CMat2 = Eigen::Matrix2cd;
    using CMat3 = Eigen::Matrix3cd;
    using CMat4 = Eigen::Matrix4cd;
    using CMat6 = Eigen::Matrix<Complex, 6, 6>;

    // Dynamic-size matrices
    using MatX = Eigen::MatrixXd;
    using CMatX = Eigen::MatrixXcd;

    // Orientation
    using Quat = Eigen::Quaterniond;

	//Indexing
	using Index = Eigen::Index;
}