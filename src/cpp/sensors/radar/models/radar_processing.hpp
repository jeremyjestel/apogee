#pragma once

#include "sensors/radar/radar_component.hpp"

namespace apogee{
    // Range rows, pulse columns in; range rows, FFT-shifted Doppler columns out.
    // Processing depends only on measured returns and the transmit template.
    void process_returns(RadarComponent &radar);
}

