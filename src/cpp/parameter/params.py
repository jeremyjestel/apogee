import apogee

def create_params():
    params = apogee.Params()
    params.missile.mass_kg = 1000.0 #adjusts the defaults

    return params