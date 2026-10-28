#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

#include "math/dsp/window.hpp"

namespace
{
	using namespace apogee;

	void check(bool condition, const std::string &message)
	{
		if (!condition) throw std::runtime_error(message);
	}

	void check_values(const VecX &actual, const std::vector<double> &expected,
		const std::string &name)
	{
		check(actual.size() == static_cast<int>(expected.size()), name + ": wrong length.");
		for (int i = 0; i < actual.size(); ++i)
			check(std::isfinite(actual[i]) && std::abs(actual[i] - expected[i]) < 3.0e-13,
				name + ": wrong sample " + std::to_string(i) + ".");
	}

	struct Reference
	{
		std::string name;
		std::vector<double> odd;
		std::vector<double> even;
	};

	// scipy.signal.windows, sym=True. Gaussian std=(N-1)/5, Kaiser beta=14, Tukey alpha=0.5.
	const std::vector<Reference> references{
		{ "rectangular", { 1, 1, 1, 1, 1 }, { 1, 1, 1, 1, 1, 1 } },
		{ "hann", { 0, 0.5, 1, 0.5, 0 },
			{ 0, 0.34549150281252633, 0.90450849718747373, 0.90450849718747373, 0.34549150281252633, 0 } },
		{ "hamming", { 0.08, 0.54, 1, 0.54, 0.08 },
			{ 0.08, 0.39785218258752431, 0.91214781741247586, 0.91214781741247586, 0.39785218258752431, 0.08 } },
		{ "bartlett", { 0, 0.5, 1, 0.5, 0 }, { 0, 0.4, 0.8, 0.8, 0.4, 0 } },
		{ "blackman", { 0, 0.34, 1, 0.34, 0 },
			{ 0, 0.20077014326253051, 0.84922985673746942, 0.84922985673746942, 0.20077014326253051, 0 } },
		{ "blackmanharris", { 0.00006, 0.21747, 1, 0.21747, 0.00006 },
			{ 0.00006, 0.10301148934566381, 0.79383351065433627, 0.79383351065433627, 0.10301148934566381, 0.00006 } },
		{ "flattop", { -0.000421051, -0.05473684, 1.000000003, -0.05473684, -0.000421051 },
			{ -0.000421051, -0.0677142520762119, 0.60687215257621197, 0.60687215257621197, -0.0677142520762119, -0.000421051 } },
		{ "kaiser", { 7.7268668352703676e-06, 0.16493218754795197, 1, 0.16493218754795197, 7.7268668352703676e-06 },
			{ 7.7268668352703676e-06, 0.068153743193960573, 0.76150939908739346, 0.76150939908739346, 0.068153743193960573, 7.7268668352703676e-06 } },
		{ "gaussian", { 0.043936933623407434, 0.45783336177161432, 1, 0.45783336177161432, 0.043936933623407434 },
			{ 0.04393693362340742, 0.32465246735834974, 0.88249690258459546, 0.88249690258459546, 0.32465246735834974, 0.04393693362340742 } },
		{ "tukey", { 0, 1, 1, 1, 0 }, { 0, 0.90450849718747373, 1, 1, 0.9045084971874735, 0 } }
	};

	void test_reference_values_and_lengths()
	{
		for (const auto &reference : references)
		{
			check_values(create_window(5, reference.name), reference.odd, reference.name + " odd");
			check_values(create_window(6, reference.name), reference.even, reference.name + " even");
			check_values(create_window(0, reference.name), {}, reference.name + " empty");
			check_values(create_window(1, reference.name), { 1 }, reference.name + " singleton");
			for (const int size : { 2, 3, 16 })
			{
				const VecX window = create_window(size, reference.name);
				check(window.size() == size, reference.name + ": wrong short-window length.");
				for (int i = 0; i < size; ++i)
					check(std::isfinite(window[i]) && std::abs(window[i] - window[size - 1 - i]) < 3.0e-13,
						reference.name + ": samples must be finite and symmetric.");
			}
		}
		check_values(create_window(6, "boxcar"), references[0].even, "boxcar alias");
		check_values(create_window(6, "blackman-harris"), references[5].even, "blackman-harris alias");
		check_values(create_window(6, "blackman_harris"), references[5].even, "blackman_harris alias");
	}

	void test_shape_parameters()
	{
		check_values(create_window(6, "kaiser", 5.0),
			{ 0.036710892271286676, 0.41490363924336682, 0.91381248386920011, 0.91381248386920011, 0.41490363924336682, 0.036710892271286676 },
			"Kaiser beta");
		check_values(create_window(6, "gaussian", 2.0),
			{ 0.45783336177161427, 0.75483960198900735, 0.96923323447634413, 0.96923323447634413, 0.75483960198900735, 0.45783336177161427 },
			"Gaussian standard deviation in samples");
		check_values(create_window(6, "tukey", 0.75),
			{ 0, 0.55226423163382676, 1, 1, 0.55226423163382665, 0 }, "Tukey alpha");
		check_values(create_window(6, "kaiser", 0.0), references[0].even, "Zero-beta Kaiser");
		check_values(create_window(6, "tukey", 0.0), references[0].even, "Zero-alpha Tukey");
		check_values(create_window(6, "tukey", 1.0), references[1].even, "Unit-alpha Tukey");
		for (const double alpha : { 1.0e-20, std::numeric_limits<double>::denorm_min() })
		{
			check_values(create_window(5, "tukey", alpha), { 0, 1, 1, 1, 0 }, "Tiny-alpha Tukey odd");
			check_values(create_window(6, "tukey", alpha), { 0, 1, 1, 1, 1, 0 }, "Tiny-alpha Tukey even");
		}
	}

}

int main()
{
	try
	{
		test_reference_values_and_lengths();
		test_shape_parameters();
		std::cout << "C++ window checks passed.\n";
		return 0;
	}
	catch (const std::exception &error)
	{
		std::cerr << error.what() << '\n';
		return 1;
	}
}
