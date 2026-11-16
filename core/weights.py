"""
ChronoMate Desktop - Weight lists
One place that decides which projectile weights the chips offer, so Dashboard, Trajectory and
Settings always show the same list (mirrors availableWeights() in the Android app).
"""

from dataclasses import dataclass
from typing import List

from core.models import WeightType, STANDARD_BB_WEIGHTS, STANDARD_DIABLO_WEIGHTS

WEIGHT_MATCH_TOLERANCE = 0.0005


@dataclass(frozen=True)
class WeightOption:
    weight: float
    label: str
    is_custom: bool = False


def standard_weights(weight_type: WeightType) -> List[float]:
    if weight_type == WeightType.BB:
        return list(STANDARD_BB_WEIGHTS)
    if weight_type == WeightType.DIABLO:
        return list(STANDARD_DIABLO_WEIGHTS)
    return []


def available_weights(cfg) -> List[WeightOption]:
    """The loaded weights of the active type, then the custom weights.

    Custom weights are always part of the CUSTOM type; for BB / Diablo they are appended only when
    the "always show custom weights" setting is on.
    """
    options = [WeightOption(w, f"{w:.2f}g") for w in standard_weights(cfg.weight_type)]
    if cfg.weight_type == WeightType.CUSTOM or cfg.always_show_custom_weights:
        options += [WeightOption(cw.weight, f"{cw.name} {cw.weight:.2f}g", True) for cw in cfg.custom_weights]
    if not options:
        options = [WeightOption(0.20, "0.20g")]
    return options


def same_weight(a: float, b: float) -> bool:
    return abs(a - b) < WEIGHT_MATCH_TOLERANCE


def weight_in_list(weight: float, options: List[WeightOption]) -> bool:
    return any(same_weight(weight, o.weight) for o in options)
