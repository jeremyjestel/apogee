#include "estimation/models/ekf_update.hpp"

namespace apogee
{
	EkfUpdateStatus update_track([[maybe_unused]] EkfState &track,
		[[maybe_unused]] const Detection &detection)
	{
		/*
		initialize state x and covariance P and measurement z outside this
		hat is a predicted value
		HPH^T is basically how you send a covariance through a function. H is a jacobian there.
		That is how you can convert an xyz variance to rae without losing information, or minimally */


		// Prediction belongs to the shared estimator before this correction.
        /*State prediction
		xhat = f(x, del_t) propagate motion in state space*/


		/*Motion Jacobian
		F = Partial of f / x Converts state space to state space across time*/


		/*Covariance prediction
		P = F P FT + Q Covariance in motion frame with process noise in state space*/


		/*Prediction converted to this detection's measurement space
		zhat = h(xhat) using the sensor pose and detection.kind*/


		/*Measurement Jacobian
		H = Partial of h / x units coords transform, converts state space to measurement space*/


		/*Innovation
		y = z - zhat Difference between measurement and prediction state in measurement space*/


		/*Innovation Covariance
		S = H P HT + R Expected covariance in measurement space.
		R is detection.covariance, with dimensions matching detection.value.*/


		/*Kalman Gain
		K = P HT S^-1   How much of the disagreement is the predictions fault versus measurement in*/


		/*State Correction
		x = x + Ky Add Kalman gain adjusted difference to state in state space*/
		

		/*Covariance Correction
		P = (I - KH) P ( I - KH)T + K R KT Have to put P in terms of Kalman in state space*/

		// TODO: implement correction using the appropriate h/H and this detection's R.
		// Do not report a successful correction or overwrite state in the stub.
		return EkfUpdateStatus::NotImplemented;
	}

} // namespace apogee
