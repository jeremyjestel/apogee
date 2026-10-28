#pragma once

#include <optional>
#include <string>

#include "math/types.hpp"

namespace apogee{
    // Symmetric windows: rectangular, hann, hamming, bartlett, blackman,
    // blackmanharris, flattop, kaiser, gaussian, tukey. No gain normalization.
    // shape: Kaiser beta (14), Gaussian std in samples ((N - 1) / 5), Tukey alpha (0.5).
    // N == 0 returns empty, N == 1 returns one.
    // Caller supplies a supported name, non-negative length, and valid shape.
    VecX create_window(int N, std::string window_type,
        std::optional<double> shape = std::nullopt);
}
