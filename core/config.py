"""
ChronoMate Desktop - Configuration and Settings Persistence
"""

import json
from pathlib import Path
from typing import List, Optional

from core.models import (
    WeightType,
    ChronoType,
    CompensationMode,
    CustomWeight,
    CalibrationEntry,
    WeaponClass,
    SoundType,
    DEFAULT_WEAPON_CLASSES,
)


class ConfigManager:
    _instance: Optional["ConfigManager"] = None

    @classmethod
    def get_instance(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        config_dir = Path.home() / ".config" / "ChronoMate"
        config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = config_dir / "settings.json"

        # Defaults
        self.is_dark_mode: bool = True
        self.language: str = "en"
        self.chrono_type: ChronoType = ChronoType.HT_X3000

        self.auto_ip_enabled: bool = True
        self.custom_ip: str = "192.168.4.1"
        self.custom_port: int = 80

        self.sound_type: SoundType = SoundType.PEW
        self.sound_volume: float = 0.8
        self.sound_muted: bool = False

        self.selected_weight: float = 0.20
        self.weight_type: WeightType = WeightType.BB
        self.custom_weights: List[CustomWeight] = []

        self.max_allowed_joule: float = 1.50
        self.max_allowed_overhop_cm: float = 15.0

        self.compensation_mode: CompensationMode = CompensationMode.NONE
        self.calibration_entries: List[CalibrationEntry] = []
        self.is_calibration_active: bool = False

        self.weapon_classes: List[WeaponClass] = list(DEFAULT_WEAPON_CLASSES)
        self.selected_weapon_class: str = "AR"

        # Ballistic Tweaks
        self.diameter_mm: float = 5.95
        self.air_density_rho: float = 1.225
        self.drag_coefficient_cw: float = 0.35
        self.magnus_coefficient_k: float = 0.002
        self.spin_damping_cr: float = 0.01
        self.gravity: float = 9.81

        self.load()

    def add_calibration_entry(self, chrono_val: float, control_val: Optional[float] = None):
        self.calibration_entries.append(CalibrationEntry(chrono_value=chrono_val, control_value=control_val))
        self.save()

    def update_calibration_control(self, index: int, control_val: Optional[float]):
        if 0 <= index < len(self.calibration_entries):
            self.calibration_entries[index].control_value = control_val
            self.save()

    def remove_calibration_entry(self, index: int):
        if 0 <= index < len(self.calibration_entries):
            self.calibration_entries.pop(index)
            self.save()

    def clear_calibration(self):
        self.calibration_entries.clear()
        self.save()

    def get_compensation_factor(self) -> float:
        entries = [e for e in self.calibration_entries if e.control_value is not None and e.chrono_value > 0]
        if not entries or self.compensation_mode == CompensationMode.NONE:
            return 1.0

        ratios = sorted([e.control_value / e.chrono_value for e in entries])
        median_ratio = ratios[len(ratios) // 2]

        if self.compensation_mode == CompensationMode.MEDIAN:
            return (1.0 + median_ratio) / 2.0
        elif self.compensation_mode == CompensationMode.TRUST_EXTERNAL:
            return median_ratio
        return 1.0

    def load(self):
        if not self.config_path.exists():
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.is_dark_mode = data.get("is_dark_mode", True)
            self.language = data.get("language", "en")
            self.chrono_type = ChronoType(data.get("chrono_type", ChronoType.HT_X3000.value))

            self.auto_ip_enabled = data.get("auto_ip_enabled", True)
            self.custom_ip = data.get("custom_ip", "192.168.4.1")
            self.custom_port = int(data.get("custom_port", 80))

            self.sound_type = SoundType(data.get("sound_type", SoundType.PEW.value))
            self.sound_volume = float(data.get("sound_volume", 0.8))
            self.sound_muted = bool(data.get("sound_muted", False))

            self.selected_weight = float(data.get("selected_weight", 0.20))
            self.weight_type = WeightType(data.get("weight_type", WeightType.BB.value))

            self.custom_weights = [
                CustomWeight(
                    name=w.get("name", "Custom"),
                    weight=float(w.get("weight", 0.20)),
                    caliber=float(w.get("caliber", 6.0)),
                    caliber_unit=w.get("caliber_unit", "mm"),
                )
                for w in data.get("custom_weights", [])
            ]

            self.max_allowed_joule = float(data.get("max_allowed_joule", 1.50))
            self.max_allowed_overhop_cm = float(data.get("max_allowed_overhop_cm", 15.0))

            self.compensation_mode = CompensationMode(data.get("compensation_mode", CompensationMode.NONE.value))
            self.calibration_entries = [
                CalibrationEntry(
                    chrono_value=float(c.get("chrono_value", 0.0)),
                    control_value=float(c["control_value"]) if c.get("control_value") is not None else None,
                )
                for c in data.get("calibration_entries", [])
            ]

            if "weapon_classes" in data:
                self.weapon_classes = [WeaponClass.from_dict(wc) for wc in data["weapon_classes"]]
            self.selected_weapon_class = data.get("selected_weapon_class", "AR")

            self.diameter_mm = float(data.get("diameter_mm", 5.95))
            self.air_density_rho = float(data.get("air_density_rho", 1.225))
            self.drag_coefficient_cw = float(data.get("drag_coefficient_cw", 0.35))
            self.magnus_coefficient_k = float(data.get("magnus_coefficient_k", 0.002))
            self.spin_damping_cr = float(data.get("spin_damping_cr", 0.01))
            self.gravity = float(data.get("gravity", 9.81))

        except Exception as e:
            print(f"Error loading config: {e}")

    def save(self):
        data = {
            "is_dark_mode": self.is_dark_mode,
            "language": self.language,
            "chrono_type": self.chrono_type.value,
            "auto_ip_enabled": self.auto_ip_enabled,
            "custom_ip": self.custom_ip,
            "custom_port": self.custom_port,
            "sound_type": self.sound_type.value,
            "sound_volume": self.sound_volume,
            "sound_muted": self.sound_muted,
            "selected_weight": self.selected_weight,
            "weight_type": self.weight_type.value,
            "custom_weights": [
                {
                    "name": cw.name,
                    "weight": cw.weight,
                    "caliber": cw.caliber,
                    "caliber_unit": cw.caliber_unit,
                }
                for cw in self.custom_weights
            ],
            "max_allowed_joule": self.max_allowed_joule,
            "max_allowed_overhop_cm": self.max_allowed_overhop_cm,
            "compensation_mode": self.compensation_mode.value,
            "calibration_entries": [
                {"chrono_value": ce.chrono_value, "control_value": ce.control_value}
                for ce in self.calibration_entries
            ],
            "weapon_classes": [wc.to_dict() for wc in self.weapon_classes],
            "selected_weapon_class": self.selected_weapon_class,
            "diameter_mm": self.diameter_mm,
            "air_density_rho": self.air_density_rho,
            "drag_coefficient_cw": self.drag_coefficient_cw,
            "magnus_coefficient_k": self.magnus_coefficient_k,
            "spin_damping_cr": self.spin_damping_cr,
            "gravity": self.gravity,
        }

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
