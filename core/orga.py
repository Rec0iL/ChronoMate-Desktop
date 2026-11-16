"""
ChronoMate Desktop - Orga verdicts (mirrors judgeClass() in the Android app)

A marshal sets the active class and the field's usual BB weight once and then only reads the cards.
Each weapon class is judged at that selected weight; below it the card shows the heaviest weight from
the active list that would still keep this gun legal (or that none would).
"""

from dataclasses import dataclass
from typing import List, Optional

AWAITING, LEGAL, ILLEGAL = "AWAITING", "LEGAL", "ILLEGAL"


@dataclass(frozen=True)
class ClassVerdict:
    status: str
    energy_j: float = 0.0          # at the selected weight
    max_weight_g: float = 0.0      # heaviest weight that stays within the limit at this velocity
    best: Optional[object] = None  # WeightOption from the active list, or None


def judge(max_joules: float, velocity: float, weight_g: float, options: List) -> ClassVerdict:
    if velocity <= 0:
        return ClassVerdict(AWAITING)
    energy = 0.5 * (weight_g / 1000.0) * velocity ** 2
    max_w = 2.0 * max_joules / velocity ** 2 * 1000.0
    fitting = [o for o in options if o.weight <= max_w + 1e-9]
    best = max(fitting, key=lambda o: o.weight) if fitting else None
    return ClassVerdict(LEGAL if energy <= max_joules + 1e-9 else ILLEGAL, energy, max_w, best)
