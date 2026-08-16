from add_build_to_path import add_apogee_build_to_path

add_apogee_build_to_path()

import apogee # type: ignore
from params import create_params
import matplotlib.pyplot as plt
import numpy as np
from plot_result import plot_result

def main():
    params = create_params()
    result = apogee.run_sim(params)
    print(result)
    plot_result(result)

if __name__ == "__main__":
    main()
