"""
ChronoMate Desktop - Core Data Models
Matches and extends com.example.chronomate.model
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import time
import uuid


class WeightType(str, Enum):
    BB = "BB"
    DIABLO = "DIABLO"
    CUSTOM = "CUSTOM"


class CompensationMode(str, Enum):
    NONE = "NONE"
    MEDIAN = "MEDIAN"
    TRUST_EXTERNAL = "TRUST_EXTERNAL"


class ChronoType(str, Enum):
    HT_X3000 = "HT-X3000"
    HT_50 = "HT-50"

    @property
    def display_name(self) -> str:
        return self.value

    @property
    def ssid(self) -> str:
        return "HT-X3000" if self == ChronoType.HT_X3000 else "HT50"


class ConnectionState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    LINKED = "LINKED"
    CONNECTED = "CONNECTED"
    FAILED = "FAILED"

    @property
    def badge_text(self) -> str:
        mapping = {
            ConnectionState.DISCONNECTED: "OFFLINE",
            ConnectionState.CONNECTING: "CONNECTING…",
            ConnectionState.LINKED: "LINKED (WAITING)",
            ConnectionState.CONNECTED: "LIVE",
            ConnectionState.FAILED: "FAILED",
        }
        return mapping.get(self, self.value)


class SoundType(str, Enum):
    PEW = "pew"
    BEEP = "beep"
    PLINK = "plink"
    MUTE = "mute"


@dataclass
class CustomWeight:
    name: str
    weight: float
    caliber: float = 6.0
    caliber_unit: str = "mm"

    def display_label(self) -> str:
        return f"{self.name} {self.caliber}{self.caliber_unit} {self.weight:.2f}g"


@dataclass
class CalibrationEntry:
    chrono_value: float
    control_value: Optional[float] = None


@dataclass
class Shot:
    raw_velocity: float
    weight_grams: float
    compensation_factor: float = 1.0
    timestamp: float = field(default_factory=time.time)

    @property
    def velocity(self) -> float:
        return self.raw_velocity * self.compensation_factor

    @property
    def energy_joules(self) -> float:
        return 0.5 * (self.weight_grams / 1000.0) * (self.velocity ** 2)

    def to_dict(self) -> dict:
        return {
            "raw_velocity": self.raw_velocity,
            "weight_grams": self.weight_grams,
            "compensation_factor": self.compensation_factor,
            "velocity": round(self.velocity, 2),
            "energy_joules": round(self.energy_joules, 2),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Shot":
        return cls(
            raw_velocity=float(data.get("raw_velocity", 0.0)),
            weight_grams=float(data.get("weight_grams", 0.20)),
            compensation_factor=float(data.get("compensation_factor", 1.0)),
            timestamp=float(data.get("timestamp", time.time())),
        )


@dataclass
class WeaponClass:
    name: str
    max_joules: float
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "max_joules": self.max_joules,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WeaponClass":
        return cls(
            name=data.get("name", "AR"),
            max_joules=float(data.get("max_joules", 1.5)),
            description=data.get("description", ""),
        )


DEFAULT_WEAPON_CLASSES = [
    WeaponClass(name="BACKUP", max_joules=1.00, description="Pistols / Sidearms (≤ 1.00 J)"),
    WeaponClass(name="AR", max_joules=1.50, description="Assault Rifles / Carbines (≤ 1.50 J)"),
    WeaponClass(name="LMG", max_joules=1.50, description="Light Machine Guns (≤ 1.50 J)"),
    WeaponClass(name="DMR", max_joules=2.00, description="Designated Marksman (≤ 2.00 J)"),
    WeaponClass(name="SNIPER", max_joules=2.80, description="Bolt Action Snipers (≤ 2.80 J)"),
]

STANDARD_BB_WEIGHTS = [0.20, 0.23, 0.25, 0.28, 0.30, 0.32, 0.36, 0.40, 0.43, 0.45]
STANDARD_DIABLO_WEIGHTS = [0.50, 0.51, 0.52, 0.53, 0.54]


@dataclass
class BallisticParams:
    mass_grams: float = 0.20
    diameter_mm: float = 5.95
    muzzle_velocity_mps: float = 100.0
    launch_angle_deg: float = 0.0
    starting_height_m: float = 1.5
    hop_up_rad_s: float = 1000.0
    air_density_rho: float = 1.225
    drag_coefficient_cw: float = 0.35
    magnus_coefficient_k: float = 0.002
    spin_damping_cr: float = 0.01
    gravity: float = 9.81


@dataclass
class TrajectoryPoint:
    x: float
    y: float
    velocity: float
    energy_joules: float
    time: float


@dataclass
class ProbeResult:
    distance: float
    bb_height_cm: float
    energy_j: float
    time_s: float
    relative_impact_cm: float
    hold_over_cm: float


@dataclass
class ChronoSession:
    name: str = "New Session"
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: float = field(default_factory=time.time)
    gun_name: str = ""
    selected_weapon_class: str = "AR"
    selected_weight: float = 0.20
    shots: List[Shot] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "created_at": self.created_at,
            "gun_name": self.gun_name,
            "selected_weapon_class": self.selected_weapon_class,
            "selected_weight": self.selected_weight,
            "notes": self.notes,
            "shots": [s.to_dict() for s in self.shots],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChronoSession":
        session = cls(
            session_id=data.get("session_id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Saved Session"),
            created_at=data.get("created_at", time.time()),
            gun_name=data.get("gun_name", ""),
            selected_weapon_class=data.get("selected_weapon_class", "AR"),
            selected_weight=float(data.get("selected_weight", 0.20)),
            notes=data.get("notes", ""),
            shots=[Shot.from_dict(s) for s in data.get("shots", [])],
        )
        return session
