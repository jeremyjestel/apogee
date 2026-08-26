def world_entity(entity):
    return f"/world/entities/{entity.key}"


def world_trajectory(entity):
    return f"/world/trajectories/{entity.key}"


def world_vector(entity, series):
    return f"/world/vectors/{entity.key}/{series.key}"


def telemetry_series(entity, series):
    owner = entity.key if entity else "global"
    return f"/telemetry/entities/{owner}/{series.system}/{series.key}"


def analysis_product(entity, item):
    # Place ownerless calculations in a shared global analysis namespace.
    owner = entity.key if entity else "global"
    return f"/analysis/entities/{owner}/{item.system}/{item.key}"


def data_child(path):
    return f"{path}/data"


def plot_child(path):
    return f"{path}/plot"


def metadata_child(path):
    return f"{path}/metadata"


def axis_child(path, axis_name):
    return f"{path}/{axis_name}_axis"
