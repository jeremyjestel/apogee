import matplotlib.pyplot as plt
import numpy as np
def plot_result(result):
    ranges_km = np.asarray(result.ranges_m, dtype=np.float64) / 1000
    snr_db = np.asarray(result.snr_db, dtype=np.float64)
    plt.plot(ranges_km, snr_db)
    plt.xlabel("Range (km)")
    plt.ylabel("SNR (dB)")
    plt.title("Radar Range Performance")
    plt.show()