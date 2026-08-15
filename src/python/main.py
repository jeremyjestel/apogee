from add_build_to_path import add_apogee_build_to_path

add_apogee_build_to_path()

import apogee
from params import create_params
import matplotlib.pyplot as plt
import numpy as np
from plot_result import plot_result


def main():
    params = create_params()
    result = apogee.run_sim(params)
    # print([(range_m, snr_db) for range_m, snr_db in zip(result.ranges_m, result.snr_db)])

    plot_result(result)


if __name__ == "__main__":
    main()
