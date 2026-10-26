
#include "math/dsp/convolve.hpp"

#include <algorithm>
#include <cmath>

namespace apogee{
    CVecX convolve(CVecX a, CVecX b, std::string type){
        int a_length = a.size();
        int b_length = b.size();
        int convolved_length = a_length + b_length - 1;
        CVecX convolved = CVecX::Zero(convolved_length);

        for (int n = 0; n < convolved_length; n++){
            for (int k = 0; k < a_length;k++){
                int idx = n - k;
                if (idx >= 0 && idx < b_length){
                    convolved[n] += a[k] * b[n-k];
                }
            }
        }
        if (type == "same"){

            Eigen::Index diff_length = convolved_length - a_length;
            convolved = convolved.segment(diff_length / 2,a_length).eval();

        }
        else if (type == "valid"){
            Index valid_length = std::abs(a_length - b_length) + 1;
            Index start = std::min(a_length, b_length) - 1;
            convolved = convolved.segment(start, valid_length).eval();
        }

        return convolved;
    }
}
