"""
ChronoMate Desktop - Pellet & slug catalogue (the "Diablos" weight type and the PCP projectiles)
Common airgun pellets (diabolos) and slugs, collected 2026-11-16 from the makers' and shops'
pages (H&N publishes BCs on hn-sport.de; JSB / Air Arms BCs are Pyramyd AIR "GA" figures; RWS, most
Air Arms .177, Crosman and Gamo publish none, so their BC is unknown). Weights come from the same
pages. BCs are approximate: measure your own with the BC tool.
Mirrors model/PelletCatalogue.kt in the Android app (both are generated from the same list).
"""

from dataclasses import dataclass
from typing import List, Optional

GRAIN = 0.06479891
CALIBERS = [(".177", 4.5), (".22", 5.5), (".25", 6.35), (".30", 7.62)]   # filter key, nominal mm
ALL_CALIBERS = "ALL"


def caliber_class(mm: float) -> str:
    return min(CALIBERS, key=lambda c: abs(c[1] - mm))[0]


@dataclass(frozen=True)
class Pellet:
    name: str              # e.g. "JSB Exact Heavy .177"
    short: str             # without the caliber tag, for chips
    grains: float
    caliber_mm: float
    bc: Optional[float]    # None = not published; measure it
    bc_model: str          # "GA" (Hawke airgun model, used as G1), "G1" or "" (not stated)
    slug: bool
    source: str

    @property
    def mass_grams(self) -> float:
        return round(self.grains * GRAIN, 3)

    @property
    def caliber(self) -> str:
        return caliber_class(self.caliber_mm)


PELLETS: List[Pellet] = [
    Pellet("Air Arms Diabolo Field .177", "Air Arms Diabolo Field", 8.44, 4.52, None, "", False, "Pyramyd AIR"),
    Pellet("Air Arms Diabolo Field Heavy .177", "Air Arms Diabolo Field Heavy", 10.34, 4.52, None, "", False, "Pyramyd AIR"),
    Pellet("Gamo Hunter .177", "Gamo Hunter", 7.56, 4.5, None, "", False, "Pyramyd AIR"),
    Pellet("H&N Baracuda Green .177", "H&N Baracuda Green", 6.64, 4.5, 0.013, "", False, "H&N"),
    Pellet("H&N Baracuda Hunter .177", "H&N Baracuda Hunter", 10.49, 4.5, 0.023, "", False, "H&N"),
    Pellet("H&N Baracuda Match .177", "H&N Baracuda Match", 10.65, 4.5, 0.024, "", False, "H&N"),
    Pellet("H&N Excite Econ II .177", "H&N Excite Econ II", 7.4, 4.5, None, "", False, "H&N / Pyramyd AIR"),
    Pellet("H&N Field Target Trophy .177", "H&N Field Target Trophy", 8.64, 4.5, 0.021, "", False, "H&N"),
    Pellet("H&N Field Target Trophy Green .177", "H&N Field Target Trophy Green", 5.71, 4.5, 0.018, "", False, "H&N"),
    Pellet("H&N Finale Match Light .177", "H&N Finale Match Light", 7.87, 4.49, None, "", False, "H&N"),
    Pellet("H&N Hornet .177", "H&N Hornet", 9.57, 4.5, 0.016, "", False, "H&N"),
    Pellet("H&N Rabbit Magnum II .177", "H&N Rabbit Magnum II", 15.74, 4.5, 0.049, "", False, "H&N"),
    Pellet("JSB Exact .177", "JSB Exact", 8.44, 4.52, 0.027, "GA", False, "Pyramyd AIR"),
    Pellet("JSB Exact Beast .177", "JSB Exact Beast", 16.28, 4.51, 0.033, "GA", False, "Pyramyd AIR"),
    Pellet("JSB Exact Heavy .177", "JSB Exact Heavy", 10.34, 4.52, 0.027, "GA", False, "Pyramyd AIR"),
    Pellet("JSB Exact Monster (redesigned) .177", "JSB Exact Monster (redesigned)", 13.43, 4.52, 0.03, "GA", False, "Pyramyd AIR"),
    Pellet("JSB Exact RS .177", "JSB Exact RS", 7.33, 4.51, 0.015, "GA", False, "Pyramyd AIR"),
    Pellet("JSB Hades .177", "JSB Hades", 10.34, 4.51, 0.027, "GA", False, "Pyramyd AIR"),
    Pellet("RWS Hobby .177", "RWS Hobby", 7.0, 4.5, None, "", False, "RWS"),
    Pellet("RWS Meisterkugeln Rifle .177", "RWS Meisterkugeln Rifle", 8.2, 4.5, None, "", False, "RWS"),
    Pellet("RWS Power Ball .177", "RWS Power Ball", 9.4, 4.5, None, "", False, "RWS"),
    Pellet("RWS R10 Match Rifle .177", "RWS R10 Match Rifle", 8.2, 4.5, None, "", False, "RWS"),
    Pellet("RWS Super Field .177", "RWS Super Field", 8.4, 4.52, None, "", False, "RWS"),
    Pellet("RWS Superdome .177", "RWS Superdome", 8.3, 4.5, None, "", False, "RWS"),
    Pellet("H&N Slug HP 13 gr .177", "H&N Slug HP 13 gr", 13.0, 4.5, 0.084, "", True, "H&N"),
    Pellet("H&N Slug HP 16 gr .177", "H&N Slug HP 16 gr", 16.0, 4.5, 0.089, "", True, "H&N"),
    Pellet("JSB KnockOut Slug 13.43 gr .177", "JSB KnockOut Slug 13.43 gr", 13.43, 4.52, 0.066, "GA", True, "Pyramyd AIR"),
    Pellet("Crosman Premier .22", "Crosman Premier", 14.3, 5.5, None, "", False, "Pyramyd AIR"),
    Pellet("H&N Baracuda Green .22", "H&N Baracuda Green", 12.96, 5.5, 0.029, "", False, "H&N"),
    Pellet("H&N Baracuda Hunter .22", "H&N Baracuda Hunter", 18.21, 5.5, 0.026, "", False, "H&N"),
    Pellet("H&N Baracuda Match .22", "H&N Baracuda Match", 21.14, 5.51, 0.039, "", False, "H&N"),
    Pellet("H&N Field Target Trophy .22", "H&N Field Target Trophy", 14.66, 5.53, 0.019, "", False, "H&N"),
    Pellet("H&N Rabbit Magnum II .22", "H&N Rabbit Magnum II", 25.31, 5.5, 0.036, "", False, "H&N"),
    Pellet("JSB Exact Jumbo .22", "JSB Exact Jumbo", 15.89, 5.52, 0.028, "GA", False, "Pyramyd AIR"),
    Pellet("JSB Exact Jumbo Beast .22", "JSB Exact Jumbo Beast", 33.95, 5.5, 0.051, "GA", False, "Pyramyd AIR"),
    Pellet("JSB Exact Jumbo Heavy .22", "JSB Exact Jumbo Heavy", 18.13, 5.52, 0.033, "GA", False, "Pyramyd AIR"),
    Pellet("JSB Exact Jumbo Monster .22", "JSB Exact Jumbo Monster", 25.39, 5.5, 0.048, "GA", False, "Pyramyd AIR"),
    Pellet("JSB Hades .22", "JSB Hades", 15.89, 5.5, 0.024, "GA", False, "Pyramyd AIR"),
    Pellet("JSB Ultra Shock .22", "JSB Ultra Shock", 25.39, 5.5, 0.024, "GA", False, "Pyramyd AIR"),
    Pellet("RWS Super Field .22", "RWS Super Field", 15.9, 5.52, None, "", False, "RWS"),
    Pellet("RWS Super H-Point .22", "RWS Super H-Point", 14.2, 5.5, None, "", False, "RWS"),
    Pellet("RWS Superdome .22", "RWS Superdome", 14.5, 5.5, None, "", False, "RWS"),
    Pellet("FX Hybrid Slug 22 gr .22", "FX Hybrid Slug 22 gr", 22.0, 5.51, 0.08, "G1", True, "Luftvapen (FX text) / Pyramyd AIR"),
    Pellet("H&N Slug HP 21 gr .22", "H&N Slug HP 21 gr", 21.0, 5.51, 0.091, "", True, "H&N"),
    Pellet("H&N Slug HP II 25 gr .22", "H&N Slug HP II 25 gr", 25.0, 5.51, 0.1, "", True, "H&N"),
    Pellet("JSB KnockOut Slug 25.39 gr .22 (.217)", "JSB KnockOut Slug 25.39 gr", 25.39, 5.5, 0.086, "GA", True, "Pyramyd AIR"),
    Pellet("Air Arms Diabolo Field .25", "Air Arms Diabolo Field", 25.4, 6.35, 0.039, "GA", False, "Pyramyd AIR"),
    Pellet("H&N Baracuda Hunter .25", "H&N Baracuda Hunter", 27.47, 6.35, 0.027, "", False, "H&N"),
    Pellet("H&N Baracuda Match .25", "H&N Baracuda Match", 30.86, 6.35, 0.037, "", False, "H&N"),
    Pellet("H&N Field Target Trophy .25", "H&N Field Target Trophy", 20.06, 6.35, 0.021, "", False, "H&N"),
    Pellet("JSB Exact King .25", "JSB Exact King", 25.39, 6.35, 0.039, "GA", False, "Pyramyd AIR"),
    Pellet("JSB Exact King Heavy MkII .25", "JSB Exact King Heavy MkII", 33.95, 6.35, 0.054, "GA", False, "Pyramyd AIR"),
    Pellet("RWS Superdome .25", "RWS Superdome", 31.0, 6.35, None, "", False, "RWS"),
    Pellet("FX Hybrid Slug 26 gr .25", "FX Hybrid Slug 26 gr", 26.0, 6.35, 0.09, "", True, "Luftvapen / Pyramyd AIR"),
    Pellet("H&N Slug HP II 28 gr .25", "H&N Slug HP II 28 gr", 28.0, 6.35, 0.096, "", True, "H&N"),
    Pellet("H&N Slug HP II 34 gr .25", "H&N Slug HP II 34 gr", 34.0, 6.35, 0.101, "", True, "H&N"),
    Pellet("JSB KnockOut Slug MkII 33.49 gr .25", "JSB KnockOut Slug MkII 33.49 gr", 33.49, 6.35, 0.093, "GA", True, "Pyramyd AIR"),
    Pellet("JSB Exact .30 44.75 gr", "JSB Exact 44.75 gr", 44.75, 7.62, 0.038, "GA", False, "Pyramyd AIR"),
    Pellet("JSB Exact .30 50.15 gr", "JSB Exact 50.15 gr", 50.16, 7.62, 0.042, "GA", False, "Pyramyd AIR"),
    Pellet("JSB Hades .30", "JSB Hades", 44.75, 7.62, 0.031, "GA", False, "Pyramyd AIR"),
    Pellet("H&N Slug HP II 50 gr .30", "H&N Slug HP II 50 gr", 50.0, 7.62, 0.115, "", True, "H&N"),
    Pellet("H&N Slug HP II 54 gr .30", "H&N Slug HP II 54 gr", 54.0, 7.62, 0.12, "", True, "H&N"),
    Pellet("JSB KnockOut Slug 50.15 gr .30", "JSB KnockOut Slug 50.15 gr", 50.15, 7.62, 0.09, "GA", True, "Pyramyd AIR"),
]


def pellets_for(caliber: str) -> List[Pellet]:
    return [p for p in PELLETS if caliber == ALL_CALIBERS or p.caliber == caliber]


def find_pellet(weight_g: float, caliber: str = ALL_CALIBERS) -> Optional[Pellet]:
    for p in pellets_for(caliber):
        if abs(p.mass_grams - weight_g) < 0.0005:
            return p
    return None
