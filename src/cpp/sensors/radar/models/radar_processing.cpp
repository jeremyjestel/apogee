#include "sensors/radar/models/radar_processing.hpp"

#include <unsupported/Eigen/FFT>

#include "math/dsp/convolve.hpp"
#include "math/dsp/window.hpp"

namespace apogee
{
    void process_returns(RadarComponent &radar)
    {
        const CMatX &rp_map = radar.state.range_pulse_map;
        const CVecX &waveform = radar.state.wf;

        const VecX range_weighting = create_window(waveform.size(), radar.params.range_window);
        const VecX doppler_weighting = create_window(rp_map.cols(), radar.params.doppler_window);

        // Convolve with the conjugate-reversed template, windowed at template length.
        const CVecX mf_kernel = (range_weighting.array() * waveform.array()).conjugate().reverse().matrix();
        CMatX matched(rp_map.rows(), rp_map.cols());
        for (Index pulse = 0; pulse < rp_map.cols(); ++pulse)
        {
            const CVecX full = convolve(rp_map.col(pulse), mf_kernel, "full");
            // Remove the filter delay so row r still denotes the echo onset at
            // mdr + r*c/(2*fs), including even-length transmit templates.
            matched.col(pulse) = full.segment(waveform.size() - 1, rp_map.rows());
        }

        const Index fft_samples = rp_map.cols() * radar.params.doppler_zero_pad_factor;
        CMatX rd_map(rp_map.rows(), fft_samples);
        CVecX padded = CVecX::Zero(fft_samples);
        Eigen::FFT<double> fft;
        for (Index range = 0; range < matched.rows(); ++range)
        {
            const CVecX weighted =
                (matched.row(range).transpose().array() * doppler_weighting.array()).matrix();
            // Apply the pulse window before padding so coherent gain stays unchanged.
            padded.head(matched.cols()) = weighted;
            CVecX spectrum;
            fft.fwd(spectrum, padded);
            // fftshift: negative bins, zero Doppler, then positive bins.
            for (Index bin = 0; bin < spectrum.size(); ++bin)
                rd_map(range, bin) = spectrum[(bin + (spectrum.size() + 1) / 2) % spectrum.size()];
        }
        // Preserve complex amplitudes and unnormalized matched-filter/FFT gain.
        // The velocity view uses the same bins with v = f_D * wavelength / 2.
        radar.state.range_doppler_map = rd_map;
        radar.state.range_velocity_map = std::move(rd_map);
    }
}
