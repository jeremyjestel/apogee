import re


_PATH_TOKEN = re.compile(r"^[A-Za-z0-9_-]+$")


def validate_path_token(value, context):
    if not value or _PATH_TOKEN.fullmatch(value) is None:
        raise ValueError(
            f"{context} must contain only letters, numbers, underscores, or hyphens: "
            f"{value!r}"
        )
    return value


def world_entity(entity):
    return f"/world/entities/{validate_path_token(entity.key, 'entity key')}"


def world_trajectory(entity):
    return f"/world/trajectories/{validate_path_token(entity.key, 'entity key')}"


def world_vector(entity, series):
    entity_key = validate_path_token(entity.key, "entity key")
    quantity = validate_path_token(series.key, "vector-series key")
    return f"/world/vectors/{entity_key}/{quantity}"


def telemetry_series(entity, series):
    entity_key = validate_path_token(entity.key, "entity key")
    system = validate_path_token(series.system, "series system")
    quantity = validate_path_token(series.key, "series key")
    return f"/telemetry/entities/{entity_key}/{system}/{quantity}"


def analysis_series(entity, series):
    owner = (
        validate_path_token(entity.key, "entity key")
        if entity is not None
        else "global"
    )
    system = validate_path_token(series.system, "series system")
    quantity = validate_path_token(series.key, "series key")
    return f"/analysis/entities/{owner}/{system}/{quantity}"


def analysis_grid(entity, grid):
    owner = (
        validate_path_token(entity.key, "entity key")
        if entity is not None
        else "global"
    )
    system = validate_path_token(grid.system, "grid system")
    quantity = validate_path_token(grid.key, "grid key")
    return f"/analysis/entities/{owner}/{system}/{quantity}"
