"""
ChronoMate Desktop - Weight lists
One place that decides which projectile weights the chips offer, so Dashboard, Trajectory, Orga
and Settings always show the same list (mirrors WeightsAndClasses.kt in the Android app).

BB: the standard airsoft weights. Diablos: the pellet & slug catalogue (core/pellets.py), filtered
by caliber. Custom: the user's own weights (also appended to the others when wanted).
Picking a pellet also makes it the PCP calculator's projectile, so both stay in step.
"""

from dataclasses import dataclass
from typing import List, Optional

from core.models import WeightType, STANDARD_BB_WEIGHTS
from core.pellets import ALL_CALIBERS, Pellet, pellets_for

WEIGHT_MATCH_TOLERANCE = 0.0005


@dataclass(frozen=True)
class WeightOption:
    weight: float
    label: str
    is_custom: bool = False
    pellet: Optional[Pellet] = None


def standard_weights(weight_type: WeightType) -> List[float]:
    return list(STANDARD_BB_WEIGHTS) if weight_type == WeightType.BB else []


def pellet_label(p: Pellet, caliber_filter: str) -> str:
    name = p.name if caliber_filter == ALL_CALIBERS else p.short
    return f"{name} {p.mass_grams:.3f}g"


def available_weights(cfg) -> List[WeightOption]:
    """The loaded weights of the active type, then the custom weights.

    Custom weights always belong to the CUSTOM type; for BB / Diablos they are appended only when
    the "always show custom weights" setting is on.
    """
    if cfg.weight_type == WeightType.DIABLO:
        options = [WeightOption(p.mass_grams, pellet_label(p, cfg.diabolo_caliber), pellet=p)
                   for p in pellets_for(cfg.diabolo_caliber)]
    else:
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


def is_selected(cfg, opt: WeightOption) -> bool:
    """Same weight, and for pellets the same pellet (two pellets can weigh the same)."""
    if not same_weight(opt.weight, cfg.selected_weight):
        return False
    # A pellet is selected by name; everything else only while no pellet is selected. Otherwise a
    # custom 0.69 g and the 0.690 g Baracuda Match would both light up.
    if opt.pellet is not None:
        return opt.pellet.name == cfg.selected_pellet
    return not cfg.selected_pellet


def select_option(cfg, opt: WeightOption):
    """Make `opt` the weight shots are recorded with, and keep the PCP projectile in step."""
    cfg.selected_weight = opt.weight
    cfg.selected_pellet = opt.pellet.name if opt.pellet else ""
    sync_pcp_with_selection(cfg)


def keep_selection_offered(cfg):
    """After the list changed: keep the selection if it's still offered, else take the first."""
    options = available_weights(cfg)
    if any(is_selected(cfg, o) for o in options):
        return
    # a pellet with the same weight is fine too (e.g. after the caliber filter changed)
    for o in options:
        if same_weight(o.weight, cfg.selected_weight):
            select_option(cfg, o)
            return
    select_option(cfg, options[0])


def sync_pcp_with_selection(cfg):
    """A picked pellet (or a custom weight with a BC) becomes the PCP calculator's projectile."""
    pc = cfg.pcp
    for o in available_weights(cfg):
        if not is_selected(cfg, o):
            continue
        if o.pellet is not None:
            p = o.pellet
            pc.projectile_name = p.name
            pc.mass_grams = p.mass_grams
            pc.caliber_mm = p.caliber_mm
            if p.bc is not None:          # unknown BC: keep the user's value (measure it!)
                pc.bc = p.bc
                pc.drag_model = "G1"
            return
        if o.is_custom:
            for cw in cfg.custom_weights:
                if same_weight(cw.weight, o.weight) and cw.bc:
                    pc.projectile_name = cw.name
                    pc.mass_grams = cw.weight
                    if cw.caliber_unit == "mm":
                        pc.caliber_mm = cw.caliber
                    pc.bc = cw.bc
                    pc.drag_model = cw.drag_model
                    return
        return
