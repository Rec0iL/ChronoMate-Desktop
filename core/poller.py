"""
ChronoMate Desktop - Background Network Poller & HTML Scraper
Handles real-time polling of HT-X3000 / HT-50 chronographs,
candidate IP scanning, regex scraping, delta tracking, and Virtual Demo mode.
"""

import re
import time
import random
from typing import List, Optional, Tuple
import requests

from PySide6.QtCore import QThread, Signal
from core.models import ConnectionState, ChronoType


FIRE_RATE_REGEX = re.compile(r"(?i)(?:firerate|fire rate|射速)[^0-9]*(\d+(?:\.\d+)?)")
SHOT_REGEX = re.compile(r"(\d{2})\s*[:：]\s*(\d+(?:\.\d+)?)")
CHRONO_MARKER_REGEX = re.compile(r"(?i)(m/s|fps|ft/s|速度|射速|chrono)")

CANDIDATE_HOSTS = ["8.8.8.8", "192.168.4.1", "192.168.1.1", "192.168.0.1"]
MAX_MISSED_POLLS = 3


def parse_chrono_html(html: str) -> Tuple[float, List[float]]:
    """Extracts rate of fire and raw shot velocities from chrono HTML."""
    clean_text = re.sub(r"<[^>]+>", " ", html)

    fr_match = FIRE_RATE_REGEX.search(clean_text)
    fire_rate = float(fr_match.group(1)) if fr_match else 0.0

    raw_shots: List[float] = []
    for match in SHOT_REGEX.finditer(clean_text):
        try:
            vel = float(match.group(2))
            if vel > 0.0:
                raw_shots.append(vel)
        except ValueError:
            continue

    return fire_rate, raw_shots


def is_chrono_page(html: str) -> bool:
    """Verifies that the fetched page is indeed from a chronograph device."""
    clean_text = re.sub(r"<[^>]+>", " ", html)
    return bool(FIRE_RATE_REGEX.search(clean_text) or CHRONO_MARKER_REGEX.search(clean_text))


class ChronoPoller(QThread):
    # Signals
    connection_changed = Signal(str, str)  # (ConnectionState, error_message)
    shot_detected = Signal(float)          # (raw_velocity)
    telemetry_updated = Signal(str, str)   # (latest_velocity_str, fire_rate_str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running: bool = True
        self._demo_mode: bool = False
        self._auto_ip: bool = True
        self._custom_ip: str = "192.168.4.1"
        self._custom_port: int = 80
        self._chrono_url: Optional[str] = None
        self._missed_polls: int = 0
        self._connection_state: ConnectionState = ConnectionState.DISCONNECTED
        self._last_seen_raw_shots: List[float] = []

        # Demo generator state
        self._demo_next_shot_time: float = 0.0
        self._demo_burst_remaining: int = 0

    def set_demo_mode(self, enabled: bool):
        self._demo_mode = enabled
        if enabled:
            self._set_state(ConnectionState.CONNECTED)
        else:
            self._set_state(ConnectionState.DISCONNECTED)
            self._chrono_url = None

    def set_network_config(self, auto_ip: bool, custom_ip: str, custom_port: int = 80):
        self._auto_ip = auto_ip
        self._custom_ip = custom_ip.strip()
        self._custom_port = custom_port
        self._chrono_url = None
        self._missed_polls = 0

    def stop(self):
        self._running = False
        self.wait(2000)

    def _set_state(self, state: ConnectionState, error: str = ""):
        if self._connection_state != state:
            self._connection_state = state
            self.connection_changed.emit(state.value, error)

    def run(self):
        session = requests.Session()
        session.headers.update({"Cache-Control": "no-cache", "User-Agent": "ChronoMate-Desktop"})

        while self._running:
            if self._demo_mode:
                self._tick_demo()
                time.sleep(0.3)
                continue

            # Real Chronograph Polling
            target = self._chrono_url
            if not target:
                target = self._discover_chrono(session)

            if target:
                html = self._fetch(session, target, timeout=1.8)
                if html and is_chrono_page(html):
                    self._missed_polls = 0
                    self._process_html(html)
                    self._set_state(ConnectionState.CONNECTED)
                else:
                    self._on_poll_failed()
            else:
                self._on_poll_failed()

            sleep_duration = 1.0 if self._connection_state == ConnectionState.CONNECTED else 2.5
            time.sleep(sleep_duration)

    def _discover_chrono(self, session: requests.Session) -> Optional[str]:
        self._set_state(ConnectionState.CONNECTING)

        if not self._auto_ip and self._custom_ip:
            port_str = f":{self._custom_port}" if self._custom_port != 80 else ""
            candidate = f"http://{self._custom_ip}{port_str}"
            html = self._fetch(session, candidate, timeout=1.5)
            if html and is_chrono_page(html):
                self._chrono_url = candidate
                return candidate
            return None

        # Auto IP candidate discovery
        for host in CANDIDATE_HOSTS:
            if not self._running:
                return None
            candidate = f"http://{host}"
            html = self._fetch(session, candidate, timeout=1.0)
            if html and is_chrono_page(html):
                self._chrono_url = candidate
                return candidate

        return None

    def _fetch(self, session: requests.Session, url: str, timeout: float = 1.5) -> Optional[str]:
        try:
            resp = session.get(url, timeout=timeout)
            if resp.status_code == 200 and resp.text:
                return resp.text
        except Exception:
            pass
        return None

    def _on_poll_failed(self):
        self._missed_polls += 1
        if self._missed_polls >= MAX_MISSED_POLLS:
            self._chrono_url = None
            self._set_state(ConnectionState.DISCONNECTED, "Chrono not responding")

    def _process_html(self, html: str):
        fire_rate, raw_shots = parse_chrono_html(html)

        # Delta calculation matching Android ViewModel logic
        new_shots: List[float] = []
        if raw_shots and raw_shots != self._last_seen_raw_shots:
            if not self._last_seen_raw_shots:
                new_shots = raw_shots
            else:
                for i in range(len(raw_shots), -1, -1):
                    head = raw_shots[:i]
                    if len(self._last_seen_raw_shots) >= i and self._last_seen_raw_shots[-i:] == head:
                        new_shots = raw_shots[i:]
                        break
                    elif not head and i == 0:
                        new_shots = raw_shots
            self._last_seen_raw_shots = raw_shots

        # Emit new shots
        for vel in new_shots:
            self.shot_detected.emit(vel)

        latest_vel_str = f"{raw_shots[-1]:.2f}" if raw_shots else "0.00"
        self.telemetry_updated.emit(latest_vel_str, f"{fire_rate:.1f}")

    def _tick_demo(self):
        """Simulates semi-auto or burst airsoft shooting."""
        now = time.time()
        if now < self._demo_next_shot_time:
            return

        # Base velocity ~ 100 m/s with natural ± 1.2 m/s consistency jitter
        base_vel = 100.0 + random.uniform(-1.2, 1.2)

        # Decide whether to fire single or burst
        if self._demo_burst_remaining > 0:
            self._demo_burst_remaining -= 1
            self.shot_detected.emit(round(base_vel, 2))
            self.telemetry_updated.emit(f"{base_vel:.2f}", "750.0")
            self._demo_next_shot_time = now + 0.08  # ~750 RPM ROF burst
        else:
            # 20% chance of a 3-round burst, 80% single shot
            if random.random() < 0.2:
                self._demo_burst_remaining = 3
                self._demo_next_shot_time = now + 0.08
            else:
                self.shot_detected.emit(round(base_vel, 2))
                self.telemetry_updated.emit(f"{base_vel:.2f}", "0.0")
                # Wait 1.5 to 3.5 seconds before next shot
                self._demo_next_shot_time = now + random.uniform(1.8, 3.5)
