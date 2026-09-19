"""
ChronoMate Desktop - High-Performance Audio Engine
Uses pygame.mixer for zero-latency playback with system CLI fallbacks (pw-play, paplay, aplay).
Generates procedural WAV sound effects on demand:
- Pew: tactical pitch drop sweep (default)
- Beep: electronic chirp
- Plink: metallic steel target impact
- Alert: over-joule warning buzzer
"""

import os
import math
import wave
import struct
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import QObject
from core.models import SoundType


class AudioManager(QObject):
    _instance: Optional["AudioManager"] = None

    @classmethod
    def get_instance(cls) -> "AudioManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.sounds_dir = Path(__file__).resolve().parent.parent / "assets" / "sounds"
        self.sounds_dir.mkdir(parents=True, exist_ok=True)

        self._current_sound_type: SoundType = SoundType.PEW
        self._muted: bool = False
        self._volume: float = 0.8
        self._pygame_available: bool = False
        self._pygame_sounds: Dict[str, any] = {}

        self._ensure_sound_files()
        self._init_player()

    def _init_player(self):
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._pygame_available = True
            self._load_pygame_sounds()
        except Exception as e:
            print(f"pygame.mixer init fallback: {e}")
            self._pygame_available = False

    def _load_pygame_sounds(self):
        import pygame
        for name in ["pew", "beep", "plink", "alert"]:
            path = self.sounds_dir / f"{name}.wav"
            if path.exists():
                try:
                    snd = pygame.mixer.Sound(str(path))
                    snd.set_volume(self._volume)
                    self._pygame_sounds[name] = snd
                except Exception as e:
                    print(f"Error loading {name}.wav: {e}")

    def set_sound_type(self, sound_type: SoundType):
        self._current_sound_type = sound_type

    def get_sound_type(self) -> SoundType:
        return self._current_sound_type

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, volume))
        if self._pygame_available:
            for snd in self._pygame_sounds.values():
                snd.set_volume(self._volume)

    def set_muted(self, muted: bool):
        self._muted = muted

    def play_shot(self):
        """Plays the selected shot sound."""
        if self._muted or self._current_sound_type == SoundType.MUTE:
            return
        self._play_named_sound(self._current_sound_type.value)

    def play_alert(self):
        """Plays the over-joule warning sound."""
        if self._muted:
            return
        self._play_named_sound("alert")

    def play_test(self, sound_type: SoundType):
        """Plays a specific sound for previewing."""
        if sound_type == SoundType.MUTE:
            return
        self._play_named_sound(sound_type.value)

    def _play_named_sound(self, name: str):
        # 1. Try pygame.mixer (best performance & lowest latency)
        if self._pygame_available and name in self._pygame_sounds:
            try:
                self._pygame_sounds[name].play()
                return
            except Exception:
                pass

        # 2. System player fallback (pw-play, paplay, aplay)
        path = self.sounds_dir / f"{name}.wav"
        if not path.exists():
            return

        for player in ["pw-play", "paplay", "aplay"]:
            cmd = shutil.which(player)
            if cmd:
                try:
                    subprocess.Popen([cmd, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                except Exception:
                    continue

    def _ensure_sound_files(self):
        """Generates WAV sound effects procedurally if missing."""
        sample_rate = 44100

        # 1. "Pew" (Pitch drop sweep)
        pew_path = self.sounds_dir / "pew.wav"
        if not pew_path.exists():
            duration = 0.16
            n_samples = int(sample_rate * duration)
            samples = []
            phase = 0.0
            for i in range(n_samples):
                t = i / sample_rate
                freq = 1800.0 * math.exp(-t * 22.0) + 180.0
                phase += 2.0 * math.pi * freq / sample_rate
                env = math.exp(-t * 18.0)
                val = math.sin(phase) * env * 0.95
                samples.append(int(val * 32767))
            self._write_wav(pew_path, samples, sample_rate)

        # 2. "Beep" (Clean 880 Hz electronic tone)
        beep_path = self.sounds_dir / "beep.wav"
        if not beep_path.exists():
            duration = 0.09
            n_samples = int(sample_rate * duration)
            samples = []
            for i in range(n_samples):
                t = i / sample_rate
                freq = 880.0
                attack = min(1.0, i / (sample_rate * 0.01))
                decay = min(1.0, (n_samples - i) / (sample_rate * 0.02))
                val = math.sin(2.0 * math.pi * freq * t) * attack * decay * 0.8
                samples.append(int(val * 32767))
            self._write_wav(beep_path, samples, sample_rate)

        # 3. "Plink" (High metallic impact resonance)
        plink_path = self.sounds_dir / "plink.wav"
        if not plink_path.exists():
            duration = 0.22
            n_samples = int(sample_rate * duration)
            samples = []
            for i in range(n_samples):
                t = i / sample_rate
                f1 = 2800.0
                f2 = 4250.0
                f3 = 6100.0
                env1 = math.exp(-t * 30.0)
                env2 = math.exp(-t * 20.0)
                env3 = math.exp(-t * 40.0)
                val = (
                    0.5 * math.sin(2.0 * math.pi * f1 * t) * env1
                    + 0.3 * math.sin(2.0 * math.pi * f2 * t) * env2
                    + 0.2 * math.sin(2.0 * math.pi * f3 * t) * env3
                ) * 0.9
                samples.append(int(val * 32767))
            self._write_wav(plink_path, samples, sample_rate)

        # 4. "Alert" (Over-Joule buzzer)
        alert_path = self.sounds_dir / "alert.wav"
        if not alert_path.exists():
            duration = 0.25
            n_samples = int(sample_rate * duration)
            samples = []
            for i in range(n_samples):
                t = i / sample_rate
                freq = 320.0 if (int(t * 16) % 2 == 0) else 240.0
                val = (0.7 if math.sin(2.0 * math.pi * freq * t) > 0 else -0.7) * 0.75
                samples.append(int(val * 32767))
            self._write_wav(alert_path, samples, sample_rate)

    @staticmethod
    def _write_wav(path: Path, samples: list, sample_rate: int):
        with wave.open(str(path), "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            data = struct.pack(f"<{len(samples)}h", *samples)
            wav_file.writeframes(data)
