def world_entity(entity):
    return f"/world/entities/{entity.key}"


def world_trajectory(entity):
    return f"/world/trajectories/{entity.key}"


def world_vector(entity, series):
    return f"/world/vectors/{entity.key}/{series.key}"


def telemetry_series(entity, series):
    return f"/telemetry/entities/{entity.key}/{series.system}/{series.key}"


def analysis_series(entity, series):
    owner = entity.key if entity else "global"
    return f"/analysis/entities/{owner}/{series.system}/{series.key}"


def analysis_grid(entity, grid):
    owner = entity.key if entity else "global"
    return f"/analysis/entities/{owner}/{grid.system}/{grid.key}"
