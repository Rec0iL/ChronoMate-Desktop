"""
ChronoMate Desktop - Projectiles: library + active lists
One place that decides which weights the chips offer, so Dashboard, Trajectory, Orga, HUD and
Settings always show the same list (mirrors WeightsAndClasses.kt in the Android app).

The mode (Settings: Airsoft / PCP) picks the kind of projectile:
- Airsoft: BBs. Library = BB weights 0.12 … 0.48 g.
- PCP: pellets & slugs. Library = the catalogue in core/pellets.py.
Each mode has an ordered *active list* (what the chips show), made of library entries the user
added plus the user's own projectiles of that kind, which are always in it.

Every entry has a stable id: "bb:0.25", "pellet:<catalogue name>", "own:<id>".
Picking a pellet (or an own projectile with a BC) also makes it the PCP calculator's projectile.
"""

import uuid
from dataclasses import dataclass
from typing import List, Optional

from core.models import BallisticMode
from core.pellets import ALL_CALIBERS, PELLETS, Pellet

WEIGHT_MATCH_TOLERANCE = 0.0005

KIND_BB = "BB"
KIND_PELLET = "PELLET"

BB_LIBRARY = [0.12, 0.20, 0.23, 0.25, 0.28, 0.30, 0.32, 0.33, 0.36, 0.40, 0.43, 0.45, 0.46, 0.48]
DEFAULT_ACTIVE_BB = ["bb:%.2f" % w for w in (0.20, 0.23, 0.25, 0.28, 0.30, 0.32, 0.36, 0.40, 0.43, 0.45)]
# Starter set for PCP: the common .177 and .22 pellets on the German market
DEFAULT_ACTIVE_PCP = ["pellet:" + n for n in (
    "JSB Exact .177", "JSB Exact Heavy .177", "H&N Field Target Trophy .177", "H&N Baracuda Match .177",
    "RWS Superdome .177", "JSB Exact Jumbo .22", "JSB Exact Jumbo Heavy .22",
    "H&N Field Target Trophy .22", "H&N Baracuda Match .22", "RWS Superdome .22",
)]


@dataclass(frozen=True)
class WeightOption:
    id: str
    weight: float
    label: str
    kind: str = KIND_BB
    is_custom: bool = False          # the user's own projectile
    pellet: Optional[Pellet] = None


def same_weight(a: float, b: float) -> bool:
    return abs(a - b) < WEIGHT_MATCH_TOLERANCE


def new_own_id() -> str:
    return uuid.uuid4().hex[:8]


def mode_kind(cfg) -> str:
    return KIND_PELLET if cfg.ballistic_mode == BallisticMode.PCP else KIND_BB


def active_ids(cfg, kind: Optional[str] = None) -> List[str]:
    kind = kind or mode_kind(cfg)
    return cfg.active_pcp if kind == KIND_PELLET else cfg.active_airsoft


# --- resolving ids --------------------------------------------------------------------------------

def _pellet_by_name(name: str) -> Optional[Pellet]:
    return next((p for p in PELLETS if p.name == name), None)


def resolve(cfg, item_id: str) -> Optional[WeightOption]:
    if item_id.startswith("bb:"):
        try:
            w = float(item_id[3:])
        except ValueError:
            return None
        return WeightOption(item_id, w, f"{w:.2f}g", KIND_BB)
    if item_id.startswith("pellet:"):
        p = _pellet_by_name(item_id[7:])
        if p is None:
            return None
        return WeightOption(item_id, p.mass_grams, f"{p.name} {p.mass_grams:.3f}g", KIND_PELLET, pellet=p)
    if item_id.startswith("own:"):
        cw = own_by_id(cfg, item_id[4:])
        if cw is None:
            return None
        kind = cw.kind
        label = f"{cw.name} {cw.weight:.3f}g" if kind == KIND_PELLET else f"{cw.name} {cw.weight:.2f}g"
        return WeightOption(item_id, cw.weight, label, kind, is_custom=True)
    return None


def own_by_id(cfg, own_id: str):
    return next((cw for cw in cfg.custom_weights if cw.id == own_id), None)


# --- lists ----------------------------------------------------------------------------------------

def normalize_active(cfg):
    """Own projectiles are always in the active list of their kind; unknown ids are dropped."""
    for kind in (KIND_BB, KIND_PELLET):
        ids = active_ids(cfg, kind)
        cleaned = [i for i in dict.fromkeys(ids) if (r := resolve(cfg, i)) is not None and r.kind == kind]
        for cw in cfg.custom_weights:
            own = "own:" + cw.id
            if cw.kind == kind and own not in cleaned:
                cleaned.append(own)
        ids[:] = cleaned


def available_weights(cfg, kind: Optional[str] = None) -> List[WeightOption]:
    """The active list of the current mode, in the user's order."""
    options = [o for o in (resolve(cfg, i) for i in active_ids(cfg, kind)) if o is not None]
    if not options:   # never leave the chips empty
        options = [resolve(cfg, "bb:0.20")] if (kind or mode_kind(cfg)) == KIND_BB else \
                  [resolve(cfg, DEFAULT_ACTIVE_PCP[0])]
    return options


def library(cfg, kind: str, caliber: str = ALL_CALIBERS, query: str = "") -> List[WeightOption]:
    """All library entries of a kind (filtered); the caller marks the ones already active."""
    q = query.strip().lower()
    if kind == KIND_BB:
        items = [resolve(cfg, "bb:%.2f" % w) for w in BB_LIBRARY]
    else:
        items = [resolve(cfg, "pellet:" + p.name) for p in PELLETS
                 if caliber == ALL_CALIBERS or p.caliber == caliber]
    return [o for o in items if o is not None and (not q or q in o.label.lower())]


def add_to_active(cfg, item_id: str):
    opt = resolve(cfg, item_id)
    if opt is None:
        return
    ids = active_ids(cfg, opt.kind)
    if item_id not in ids:
        ids.append(item_id)


def remove_from_active(cfg, item_id: str) -> bool:
    """Library entries leave the active list; own projectiles stay (delete them instead)."""
    if item_id.startswith("own:"):
        return False
    for ids in (cfg.active_airsoft, cfg.active_pcp):
        if item_id in ids:
            ids.remove(item_id)
    keep_selection_offered(cfg)
    return True


def move_active(cfg, item_id: str, step: int):
    for ids in (cfg.active_airsoft, cfg.active_pcp):
        if item_id in ids:
            i = ids.index(item_id)
            j = i + step
            if 0 <= j < len(ids):
                ids[i], ids[j] = ids[j], ids[i]
            return


def delete_own(cfg, own_id: str):
    cfg.custom_weights = [cw for cw in cfg.custom_weights if cw.id != own_id]
    for ids in (cfg.active_airsoft, cfg.active_pcp):
        if "own:" + own_id in ids:
            ids.remove("own:" + own_id)
    keep_selection_offered(cfg)


# --- selection ------------------------------------------------------------------------------------

def is_selected(cfg, opt: WeightOption) -> bool:
    """Each mode keeps its own selection (switching modes restores it)."""
    return opt.id == cfg.selected_by_kind.get(opt.kind)


def select_option(cfg, opt: WeightOption):
    """Remember `opt` as its mode's selection; in the current mode it is the weight shots are
    recorded with. A pellet also becomes the PCP projectile."""
    cfg.selected_by_kind[opt.kind] = opt.id
    if opt.kind == mode_kind(cfg):
        cfg.selected_item = opt.id
        cfg.selected_weight = opt.weight
    sync_pcp_with_selection(cfg, opt)


def restore_mode_selection(cfg):
    """After a mode switch: bring back that mode's last selection (or a sensible one)."""
    kind = mode_kind(cfg)
    cfg.selected_item = cfg.selected_by_kind.get(kind, "")
    opt = resolve(cfg, cfg.selected_item) if cfg.selected_item else None
    if opt is not None:
        cfg.selected_weight = opt.weight
    keep_selection_offered(cfg)


def orga_selection(cfg) -> WeightOption:
    """Orga is always airsoft: the BB selection, whatever mode the Trajectory page is in."""
    opts = available_weights(cfg, KIND_BB)
    return next((o for o in opts if o.id == cfg.selected_by_kind.get(KIND_BB)), opts[0])


def keep_selection_offered(cfg):
    """After the list or the mode changed: keep the selection if it's still offered, else take an
    entry with the same weight, else the first."""
    options = available_weights(cfg)
    if any(o.id == cfg.selected_item for o in options):
        cfg.selected_by_kind[mode_kind(cfg)] = cfg.selected_item
        return
    same = next((o for o in options if same_weight(o.weight, cfg.selected_weight)), None)
    select_option(cfg, same or options[0])


def sync_pcp_with_selection(cfg, opt: WeightOption):
    """A picked pellet (or own projectile with a BC) becomes the PCP calculator's projectile."""
    pc = cfg.pcp
    if opt.pellet is not None:
        p = opt.pellet
        pc.projectile_name, pc.mass_grams, pc.caliber_mm = p.name, p.mass_grams, p.caliber_mm
        if p.bc is not None:          # unknown BC: keep the user's value (measure it!)
            pc.bc, pc.drag_model = p.bc, "G1"
    elif opt.is_custom and opt.kind == KIND_PELLET:
        cw = own_by_id(cfg, opt.id[4:])
        if cw is not None:
            pc.projectile_name, pc.mass_grams = cw.name, cw.weight
            if cw.caliber_unit == "mm":
                pc.caliber_mm = cw.caliber
            if cw.bc:
                pc.bc, pc.drag_model = cw.bc, cw.drag_model


def migrate(cfg, data: dict):
    """Settings written before the library existed: give own weights an id and a kind, build the
    active lists, and turn the old selection into an id."""
    for cw in cfg.custom_weights:
        if not cw.id:
            cw.id = new_own_id()
        if cw.kind not in (KIND_BB, KIND_PELLET):
            cw.kind = KIND_PELLET if cw.bc else KIND_BB
    if "active_airsoft" not in data:
        cfg.active_airsoft = list(DEFAULT_ACTIVE_BB)
    if "active_pcp" not in data:
        cfg.active_pcp = list(DEFAULT_ACTIVE_PCP)
        old = data.get("selected_pellet") or ""
        if old and ("pellet:" + old) not in cfg.active_pcp and _pellet_by_name(old):
            cfg.active_pcp.append("pellet:" + old)
    normalize_active(cfg)
    if cfg.selected_item and not cfg.selected_by_kind:
        opt = resolve(cfg, cfg.selected_item)
        if opt is not None:
            cfg.selected_by_kind[opt.kind] = opt.id
    if not cfg.selected_item:
        old = data.get("selected_pellet") or ""
        if old and cfg.ballistic_mode == BallisticMode.PCP:
            cfg.selected_item = "pellet:" + old
    keep_selection_offered(cfg)
