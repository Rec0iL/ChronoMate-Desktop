"""
ChronoMate Desktop - Session Manager
Allows on-demand saving, loading, and management of shooting sessions.
"""

import json
from pathlib import Path
from typing import List, Optional
from core.models import ChronoSession, Shot


class SessionManager:
    _instance: Optional["SessionManager"] = None

    @classmethod
    def get_instance(cls) -> "SessionManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.sessions_dir = Path.home() / ".local" / "share" / "ChronoMate" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.active_session: ChronoSession = ChronoSession()

    def reset_active_session(self, name: str = "New Session", gun_name: str = "", weapon_class: str = "AR", weight: float = 0.20):
        self.active_session = ChronoSession(
            name=name,
            gun_name=gun_name,
            selected_weapon_class=weapon_class,
            selected_weight=weight,
        )

    def add_shot(self, shot: Shot):
        self.active_session.shots.append(shot)

    def update_compensation_factor(self, factor: float):
        for shot in self.active_session.shots:
            shot.compensation_factor = factor

    def remove_shot(self, index: int):
        if 0 <= index < len(self.active_session.shots):
            self.active_session.shots.pop(index)

    def clear_shots(self):
        self.active_session.shots.clear()

    def save_session_to_file(self, file_path: Path) -> bool:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.active_session.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save session: {e}")
            return False

    def save_to_default_dir(self, name: Optional[str] = None) -> Path:
        if name:
            self.active_session.name = name
        safe_name = "".join(c for c in self.active_session.name if c.isalnum() or c in (" ", "_", "-")).strip()
        safe_name = safe_name.replace(" ", "_") or "Session"
        file_name = f"{safe_name}_{self.active_session.session_id}.json"
        target_path = self.sessions_dir / file_name
        self.save_session_to_file(target_path)
        return target_path

    def load_session_from_file(self, file_path: Path) -> bool:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.active_session = ChronoSession.from_dict(data)
            return True
        except Exception as e:
            print(f"Failed to load session: {e}")
            return False

    def list_saved_sessions(self) -> List[Path]:
        return sorted(self.sessions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
