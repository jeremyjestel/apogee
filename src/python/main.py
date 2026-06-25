import sys
#sys.path.append(r"C:\Users\jerem\OneDrive\Documents\apogee\build\Release")

import apogee
from params import Params
from cpp_conv import cpp_conv

def main():
    p = Params()

    base_params = apogee.Params()
    cpp_params = cpp_conv(base_params, p)

    result = apogee.run_ack(base_params)

    print(result)

if __name__ == "__main__":
    main()