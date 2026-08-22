from add_build_to_path import add_apogee_build_to_path

add_apogee_build_to_path()

import apogee  # type: ignore
from params import create_params
from visualization import show_result


def main():
    params = create_params()
    result = apogee.run_sim(params)
    return show_result(result)


if __name__ == "__main__":
    main()
