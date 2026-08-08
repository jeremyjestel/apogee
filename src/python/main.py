from add_build_to_path import add_apogee_build_to_path

add_apogee_build_to_path()

import apogee
from params import create_params
import matplotlib.pyplot as plt
import numpy as np


def main():
    params = create_params()
    result = apogee.run_sim(params)
    # print([(range_m, snr_db) for range_m, snr_db in zip(result.ranges_m, result.snr_db)])

    ranges_km = np.asarray(result.ranges_m, dtype=np.float64) / 1000
    snr_db = np.asarray(result.snr_db, dtype=np.float64)

    plt.plot(ranges_km, snr_db)
    plt.xlabel("Range (km)")
    plt.ylabel("SNR (dB)")
    plt.title("Radar Range Performance")
    plt.show()

if __name__ == "__main__":
    main()
