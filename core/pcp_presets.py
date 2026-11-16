"""
ChronoMate Desktop - PCP projectile presets
Common pellets and slugs with the makers' published ballistic coefficients. These are approximate:
makers' BCs are often optimistic, and they vary with speed. Measure your own with the BC tool.
Mirrors PCP_PRESETS in the Android app (model/PcpPresets.kt).
"""

from dataclasses import dataclass
from typing import List

GRAIN = 0.06479891


@dataclass(frozen=True)
class PcpPreset:
    name: str
    grains: float
    caliber_mm: float
    bc: float
    drag_model: str = "G1"
    slug: bool = False
    source: str = ""     # who publishes the figure (most retailer values are Hawke "GA", used here as G1)

    @property
    def mass_grams(self) -> float:
        return round(self.grains * GRAIN, 3)

    def label(self) -> str:
        kind = "slug" if self.slug else "pellet"
        return f"{self.name} — {self.grains:g} gr / {self.mass_grams:.3f} g, BC ≈{self.bc:.3f} ({kind}, {self.source})"


PCP_PRESETS: List[PcpPreset] = [
    PcpPreset("JSB Exact .177", 8.44, 4.52, 0.027, slug=False, source="Pyramyd AIR (GA)"),
    PcpPreset("JSB Exact Heavy .177", 10.34, 4.52, 0.027, slug=False, source="Pyramyd AIR (GA)"),
    PcpPreset("H&N Field Target Trophy .177", 8.64, 4.5, 0.021, slug=False, source="H&N"),
    PcpPreset("H&N Baracuda Match .177", 10.65, 4.5, 0.024, slug=False, source="H&N"),
    PcpPreset("RWS Superdome .177", 8.3, 4.5, 0.014, slug=False, source="Vector Air"),
    PcpPreset("RWS Meisterkugeln .177", 8.2, 4.5, 0.01, slug=False, source="Vector Air"),
    PcpPreset("JSB Exact Jumbo .22", 15.89, 5.52, 0.028, slug=False, source="Pyramyd AIR (GA)"),
    PcpPreset("JSB Exact Jumbo Heavy .22", 18.13, 5.52, 0.033, slug=False, source="Pyramyd AIR (GA)"),
    PcpPreset("H&N Field Target Trophy .22", 14.66, 5.5, 0.019, slug=False, source="H&N"),
    PcpPreset("H&N Baracuda Match .22", 21.14, 5.5, 0.039, slug=False, source="H&N"),
    PcpPreset("RWS Superdome .22", 14.5, 5.5, 0.028, slug=False, source="Vector Air"),
    PcpPreset("JSB Exact King .25", 25.39, 6.35, 0.032, slug=False, source="Pyramyd AIR (GA)"),
    PcpPreset("JSB Exact King Heavy MkII .25", 33.95, 6.35, 0.054, slug=False, source="Pyramyd AIR (GA)"),
    PcpPreset("JSB Exact .30", 44.75, 7.62, 0.038, slug=False, source="Pyramyd AIR (GA)"),
    PcpPreset("JSB Knock Out Slug .22", 25.39, 5.5, 0.086, slug=True, source="Pyramyd AIR (GA)"),
    PcpPreset("H&N Slug HP .22", 21.0, 5.5, 0.091, slug=True, source="H&N"),
    PcpPreset("JSB Knock Out Slug .25", 33.49, 6.37, 0.095, slug=True, source="Pyramyd AIR (GA)"),
    PcpPreset("NSA Slug .25", 34.9, 6.35, 0.11, slug=True, source="Pyramyd AIR (G1)"),
]
