
#include "math/dsp/convolve.hpp"

#include <algorithm>
#include <cmath>
#include <complex>

namespace apogee{
    CVecX correlate(CVecX a, CVecX b){
        int a_length = a.size();
        int b_length = b.size();
        int correlated_length = a_length + b_length - 1;
        CVecX correlated = CVecX::Zero(correlated_length);

        for (int tau = -(b_length - 1); tau < a_length; tau++){
            for (int n = 0; n < a_length;n++){
                int idx = n - tau;
                if (idx >= 0 && idx < b_length){
                    int tau_adj = tau + (b_length - 1);
                    correlated[tau_adj] += a[n] * std::conj(b[idx]);
                }
            }
        }
        return correlated;
    }
}
