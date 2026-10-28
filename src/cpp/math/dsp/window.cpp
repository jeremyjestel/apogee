#include "math/dsp/window.hpp"

#include <algorithm>
#include <cmath>
#include <numbers>

namespace apogee{
    VecX create_window(int N, std::string window_type, std::optional<double> shape){
        if (window_type == "boxcar") window_type = "rectangular";
        if (window_type == "blackman-harris" || window_type == "blackman_harris"){
            window_type = "blackmanharris";
        }

        double beta = shape.value_or(14.0);
        double sigma = shape.value_or(N > 1 ? double(N - 1) / 5.0 : 1.0);
        double alpha = shape.value_or(0.5);

        if (N == 0) return VecX::Zero(0);
        if (N == 1) return VecX::Ones(1);

        VecX n = VecX::LinSpaced(N, 0.0, double(N - 1));
        VecX phase = (2.0 * std::numbers::pi * n.array() / double(N - 1)).matrix();

        if (window_type == "rectangular"){
            return VecX::Ones(N);
        }

        if (window_type == "hamming"){
            return (0.54 - 0.46 * phase.array().cos()).matrix();
        }

        if (window_type == "hann"){
            return (0.5 * (1.0 - phase.array().cos())).matrix();
        }

        if (window_type == "bartlett"){
            return (1.0 - (2.0 * n.array() / double(N - 1) - 1.0).abs()).matrix();
        }

        if (window_type == "blackman"){
            return (0.42 - 0.5 * phase.array().cos()
                + 0.08 * (2.0 * phase.array()).cos()).matrix();
        }

        if (window_type == "blackmanharris"){
            return (0.35875 - 0.48829 * phase.array().cos()
                + 0.14128 * (2.0 * phase.array()).cos()
                - 0.01168 * (3.0 * phase.array()).cos()).matrix();
        }

        if (window_type == "flattop"){
            return (0.21557895 - 0.41663158 * phase.array().cos()
                + 0.277263158 * (2.0 * phase.array()).cos()
                - 0.083578947 * (3.0 * phase.array()).cos()
                + 0.006947368 * (4.0 * phase.array()).cos()).matrix();
        }

        if (window_type == "kaiser"){
            double denominator = std::cyl_bessel_i(0.0, beta);
            VecX window(N);
            for (int idx = 0; idx < N; idx++){
                double x = 2.0 * n[idx] / double(N - 1) - 1.0;
                double radius = std::sqrt(std::max(0.0, 1.0 - x * x));
                window[idx] = std::cyl_bessel_i(0.0, beta * radius) / denominator;
            }
            return window;
        }

        if (window_type == "gaussian"){
            return (-0.5 * ((n.array() - double(N - 1) / 2.0) / sigma).square()).exp().matrix();
        }

        if (window_type == "tukey"){
            if (alpha == 0.0) return VecX::Ones(N);
            if (alpha == 1.0) return (0.5 * (1.0 - phase.array().cos())).matrix();

            VecX window = VecX::Ones(N);
            window[0] = window[N - 1] = 0.0;
            for (int idx = 1; idx < N - 1; idx++){
                double x = n[idx] / double(N - 1);
                if (x < alpha / 2.0){
                    window[idx] = 0.5 * (1.0 + std::cos(std::numbers::pi * (2.0 * x / alpha - 1.0)));
                }
                else if (x > 1.0 - alpha / 2.0){
                    window[idx] = 0.5 * (1.0 + std::cos(std::numbers::pi * (2.0 * (1.0 - x) / alpha - 1.0)));
                }
            }
            return window;
        }

        return VecX();
    }
}
