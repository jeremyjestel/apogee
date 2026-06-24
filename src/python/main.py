import sys
sys.path.append(r"C:\Users\jerem\OneDrive\Documents\apogee\build\Release")

import apogee
from params import Params

def main():
    p = Params()

    cpp_params = apogee.Params()
    cpp_params.dt = p.dt
    cpp_params.t_end = p.t_end

    result = apogee.run_ack(cpp_params)

    print(result)

if __name__ == "__main__":
    main()