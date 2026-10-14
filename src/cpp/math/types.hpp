#pragma once

#include <Eigen/Dense>
#include <Eigen/Geometry>

namespace apogee
{

	// Fixed-size vectors
	using Vec2 = Eigen::Vector2d;
	using Vec3 = Eigen::Vector3d;
	using Vec4 = Eigen::Vector4d;
	using Vec6 = Eigen::Matrix<double, 6, 1>;

	// Dynamic-size vector
	using VecX = Eigen::VectorXd;

	// Fixed-size matrices
	using Mat2 = Eigen::Matrix2d;
	using Mat3 = Eigen::Matrix3d;
	using Mat4 = Eigen::Matrix4d;
	using Mat6 = Eigen::Matrix<double, 6, 6>;

	// Dynamic-size matrix
	using MatX = Eigen::MatrixXd;

	// Orientation
	using Quat = Eigen::Quaterniond;

}
