#include "motion/models/gravity.hpp"
#include "math/constants.hpp"

namespace apogee
{
	Vec3 ekf(Vec6 measurement, double time)
	{
		return Vec3::Zero();
        /*
            predict with motion model moves estimate from current belief state
			
			convert measurement to state space with jacobian

			kalman gain calculation

			update state estimate with the kalman gain adjusted combo of measurement and prediction

			Update covariance with the jacobian rebase


        
        
        
        
        
        */
	}

} // namespace apogee
