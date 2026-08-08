from dataclasses import asdict

def cpp_conv(base_class, py_params):

    for name, value in asdict(py_params).items():
        setattr(base_class, name, value)

    return base_class