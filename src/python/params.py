from dataclasses import dataclass

@dataclass
class Params:
    dt: float = 0.01
    t_end: float = 10.0