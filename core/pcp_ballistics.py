"""
ChronoMate Desktop - PCP Airgun Ballistics (pellets & slugs)

Point-mass (3-DOF) exterior ballistics as used by airgun calculators:
- drag from the standard G1 / G7 drag tables, scaled by the ballistic coefficient (BC, lb/in²),
  looked up by Mach number, so drag rises the way it really does near the speed of sound;
- air density and speed of sound from temperature, pressure (or altitude) and humidity;
- wind as a vector in the drag (cross-, head- and tailwind);
- uphill / downhill shots (the zero is set on level ground, like a real rifle);
- the zero angle is solved exactly for the zero range and the scope height.

Spin drift and Coriolis are left out on purpose: below a millimetre at airgun ranges.
The Kotlin port in the Android app (PcpEngine.kt) must give the same numbers (see tests).
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

GRAIN_TO_GRAM = 0.06479891
MPS_TO_FPS = 1.0 / 0.3048
J_TO_FTLB = 0.7375621
LB_PER_IN2_TO_KG_PER_M2 = 703.0696
MRAD_PER_MOA = 0.2908882

# Standard drag functions: (Mach, Cd). Values from the published G1 / G7 tables.
G1_TABLE: List[Tuple[float, float]] = [
    (0.00, 0.2629), (0.05, 0.2558), (0.10, 0.2487), (0.15, 0.2413), (0.20, 0.2344),
    (0.25, 0.2278), (0.30, 0.2214), (0.35, 0.2155), (0.40, 0.2104), (0.45, 0.2061),
    (0.50, 0.2032), (0.55, 0.2020), (0.60, 0.2034), (0.70, 0.2165), (0.725, 0.2230),
    (0.75, 0.2313), (0.775, 0.2417), (0.80, 0.2546), (0.825, 0.2706), (0.85, 0.2901),
    (0.875, 0.3136), (0.90, 0.3415), (0.925, 0.3734), (0.95, 0.4084), (0.975, 0.4448),
    (1.00, 0.4805), (1.025, 0.5136), (1.05, 0.5427), (1.075, 0.5677), (1.10, 0.5883),
    (1.125, 0.6053), (1.15, 0.6191), (1.20, 0.6393), (1.25, 0.6518), (1.30, 0.6589),
    (1.35, 0.6621), (1.40, 0.6625), (1.45, 0.6607), (1.50, 0.6573), (1.55, 0.6528),
    (1.60, 0.6474), (1.65, 0.6413), (1.70, 0.6347), (1.75, 0.6280), (1.80, 0.6210),
    (1.85, 0.6141), (1.90, 0.6072), (1.95, 0.6003), (2.00, 0.5934),
]

G7_TABLE: List[Tuple[float, float]] = [
    (0.00, 0.1198), (0.05, 0.1197), (0.10, 0.1196), (0.15, 0.1194), (0.20, 0.1193),
    (0.25, 0.1194), (0.30, 0.1194), (0.35, 0.1194), (0.40, 0.1193), (0.45, 0.1193),
    (0.50, 0.1194), (0.55, 0.1193), (0.60, 0.1194), (0.65, 0.1197), (0.70, 0.1202),
    (0.725, 0.1207), (0.75, 0.1215), (0.775, 0.1226), (0.80, 0.1242), (0.825, 0.1266),
    (0.85, 0.1306), (0.875, 0.1368), (0.90, 0.1464), (0.925, 0.1660), (0.95, 0.2054),
    (0.975, 0.2993), (1.00, 0.3803), (1.025, 0.4015), (1.05, 0.4043), (1.075, 0.4034),
    (1.10, 0.4014), (1.125, 0.3987), (1.15, 0.3955), (1.20, 0.3884), (1.25, 0.3810),
    (1.30, 0.3732), (1.35, 0.3657), (1.40, 0.3580), (1.50, 0.3440), (1.55, 0.3376),
    (1.60, 0.3315), (1.65, 0.3260), (1.70, 0.3209), (1.75, 0.3160), (1.80, 0.3117),
    (1.85, 0.3078), (1.90, 0.3042), (1.95, 0.3010), (2.00, 0.2980),
]

DRAG_TABLES = {"G1": G1_TABLE, "G7": G7_TABLE}

INTEGRATION_DT = 0.0005   # s; 0.5 ms ≈ 14 cm per step at 280 m/s
MAX_FLIGHT_TIME = 4.0     # s
TRANSONIC_WARN_MACH = 0.90


def drag_coefficient(model: str, mach: float) -> float:
    table = DRAG_TABLES.get(model, G1_TABLE)
    if mach <= table[0][0]:
        return table[0][1]
    if mach >= table[-1][0]:
        return table[-1][1]
    lo, hi = 0, len(table) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if table[mid][0] <= mach:
            lo = mid
        else:
            hi = mid
    m0, c0 = table[lo]
    m1, c1 = table[hi]
    return c0 + (c1 - c0) * (mach - m0) / (m1 - m0)


@dataclass
class Atmosphere:
    temperature_c: float = 15.0
    pressure_hpa: float = 1013.25   # absolute (station) pressure
    humidity_pct: float = 50.0
    altitude_m: float = 0.0
    use_altitude: bool = False      # True: pressure follows from altitude (standard atmosphere)

    def station_pressure_pa(self) -> float:
        if self.use_altitude:
            return 101325.0 * (1.0 - 2.25577e-5 * self.altitude_m) ** 5.25588
        return self.pressure_hpa * 100.0

    def _vapour_pressure_pa(self) -> float:
        t = self.temperature_c
        saturation = 610.78 * 10.0 ** (7.5 * t / (t + 237.3))
        return max(0.0, min(100.0, self.humidity_pct)) / 100.0 * saturation

    def density(self) -> float:
        t_k = self.temperature_c + 273.15
        p = self.station_pressure_pa()
        e = self._vapour_pressure_pa()
        return (p - e) / (287.058 * t_k) + e / (461.495 * t_k)

    def speed_of_sound(self) -> float:
        t_k = self.temperature_c + 273.15
        p = self.station_pressure_pa()
        e = self._vapour_pressure_pa()
        t_virtual = t_k / (1.0 - 0.378 * e / p)
        return math.sqrt(1.4 * 287.058 * t_virtual)


@dataclass
class PcpParams:
    mass_grams: float = 1.175          # 18.13 gr
    caliber_mm: float = 5.52
    bc: float = 0.035                  # lb/in², of the chosen drag model
    drag_model: str = "G1"
    muzzle_velocity_mps: float = 274.0
    sight_height_cm: float = 5.0
    zero_range_m: float = 30.0
    shot_angle_deg: float = 0.0        # + uphill, − downhill
    wind_speed_mps: float = 0.0
    wind_clock: float = 3.0            # direction the wind comes FROM, 12 = from the target
    max_range_m: float = 100.0
    step_m: float = 5.0
    kill_zone_cm: float = 3.0
    gravity: float = 9.80665


@dataclass
class PcpPoint:
    range_m: float          # along the line of sight
    drop_cm: float          # + above the line of sight, − below
    drift_cm: float         # + right, − left
    velocity_mps: float
    energy_j: float
    time_s: float
    mach: float

    def hold_mrad(self) -> float:
        """Angle to hold / dial: + = hold over (dial up), − = hold under."""
        return 0.0 if self.range_m <= 0 else -math.atan2(self.drop_cm / 100.0, self.range_m) * 1000.0

    def drift_mrad(self) -> float:
        """+ = hold right (pellet blown left), − = hold left."""
        return 0.0 if self.range_m <= 0 else -math.atan2(self.drift_cm / 100.0, self.range_m) * 1000.0


@dataclass
class PcpResult:
    points: List[PcpPoint] = field(default_factory=list)      # dense, every few cm
    range_card: List[PcpPoint] = field(default_factory=list)  # every step_m
    zero_angle_mrad: float = 0.0
    near_zero_m: Optional[float] = None
    far_zero_m: Optional[float] = None
    max_ordinate_cm: float = 0.0
    max_ordinate_range_m: float = 0.0
    kill_zone_from_m: Optional[float] = None
    kill_zone_to_m: Optional[float] = None
    muzzle_energy_j: float = 0.0
    muzzle_mach: float = 0.0
    speed_of_sound_mps: float = 340.0
    air_density: float = 1.225
    warnings: List[str] = field(default_factory=list)   # i18n keys

    def point_at(self, range_m: float) -> Optional[PcpPoint]:
        return _interpolate(self.points, range_m)


def _interpolate(points: List[PcpPoint], range_m: float) -> Optional[PcpPoint]:
    if not points or range_m < points[0].range_m or range_m > points[-1].range_m:
        return None
    lo, hi = 0, len(points) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if points[mid].range_m <= range_m:
            lo = mid
        else:
            hi = mid
    a, b = points[lo], points[hi]
    span = b.range_m - a.range_m
    f = 0.0 if span <= 0 else (range_m - a.range_m) / span
    mix = lambda u, v: u + (v - u) * f
    return PcpPoint(
        range_m=range_m,
        drop_cm=mix(a.drop_cm, b.drop_cm),
        drift_cm=mix(a.drift_cm, b.drift_cm),
        velocity_mps=mix(a.velocity_mps, b.velocity_mps),
        energy_j=mix(a.energy_j, b.energy_j),
        time_s=mix(a.time_s, b.time_s),
        mach=mix(a.mach, b.mach),
    )


class PcpBallistics:
    """Stateless solver; create once, call solve() as often as needed."""

    def fly(self, p: PcpParams, atm: Atmosphere, zero_angle_rad: float,
            shot_angle_rad: float, max_range_m: float, with_wind: bool = True) -> List[PcpPoint]:
        """Integrates one shot (RK4) and returns points relative to the line of sight."""
        rho = atm.density()
        c = atm.speed_of_sound()
        m = p.mass_grams / 1000.0
        k = (math.pi / 8.0) * rho / (max(p.bc, 1e-4) * LB_PER_IN2_TO_KG_PER_M2)
        model = p.drag_model
        g = p.gravity
        sight = p.sight_height_cm / 100.0

        # Wind "from" clock direction → air velocity vector (x downrange, z to the right).
        if with_wind and p.wind_speed_mps > 0:
            theta = math.radians((p.wind_clock % 12.0) * 30.0)
            wx = -p.wind_speed_mps * math.cos(theta)
            wz = -p.wind_speed_mps * math.sin(theta)
        else:
            wx = wz = 0.0

        bore = shot_angle_rad + zero_angle_rad
        v0 = p.muzzle_velocity_mps
        # State: x, y, z, vx, vy, vz (world frame, y up, bore at the origin)
        s = [0.0, 0.0, 0.0, v0 * math.cos(bore), v0 * math.sin(bore), 0.0]

        # Line of sight: from the scope (perpendicular above the bore) along the shot angle.
        ux, uy = math.cos(shot_angle_rad), math.sin(shot_angle_rad)
        nx, ny = -uy, ux
        sx, sy = -sight * math.sin(shot_angle_rad), sight * math.cos(shot_angle_rad)

        def deriv(st):
            rx, ry, rz = st[3] - wx, st[4], st[5] - wz
            v = math.sqrt(rx * rx + ry * ry + rz * rz)
            a = k * drag_coefficient(model, v / c) * v
            return (st[3], st[4], st[5], -a * rx, -a * ry - g, -a * rz)

        def to_point(st, t):
            dx, dy = st[0] - sx, st[1] - sy
            v = math.sqrt(st[3] ** 2 + st[4] ** 2 + st[5] ** 2)
            return PcpPoint(
                range_m=dx * ux + dy * uy,
                drop_cm=(dx * nx + dy * ny) * 100.0,
                drift_cm=st[2] * 100.0,
                velocity_mps=v,
                energy_j=0.5 * m * v * v,
                time_s=t,
                mach=v / c,
            )

        dt = INTEGRATION_DT
        t = 0.0
        points = [to_point(s, 0.0)]
        while t < MAX_FLIGHT_TIME:
            k1 = deriv(s)
            s2 = [s[i] + 0.5 * dt * k1[i] for i in range(6)]
            k2 = deriv(s2)
            s3 = [s[i] + 0.5 * dt * k2[i] for i in range(6)]
            k3 = deriv(s3)
            s4 = [s[i] + dt * k3[i] for i in range(6)]
            k4 = deriv(s4)
            s = [s[i] + dt / 6.0 * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]) for i in range(6)]
            t += dt
            pt = to_point(s, t)
            points.append(pt)
            if pt.range_m >= max_range_m or pt.velocity_mps < 5.0:
                break
        return points

    def solve_zero_angle(self, p: PcpParams, atm: Atmosphere) -> float:
        """Bore angle above the line of sight (rad) that puts the pellet on the LOS at zero range.
        Zeroing happens on level ground and without wind, like at the range."""
        zero = max(1.0, p.zero_range_m)

        def miss(angle: float) -> float:
            pts = self.fly(p, atm, angle, 0.0, zero + 0.5, with_wind=False)
            pt = _interpolate(pts, zero)
            return pt.drop_cm if pt else -1e9

        angle = 0.0
        for _ in range(12):
            err = miss(angle)
            if abs(err) < 1e-4:
                break
            # d(drop_cm)/d(angle) ≈ zero_range_cm, exact enough for quick convergence
            angle -= err / (zero * 100.0)
            angle = max(-0.05, min(0.25, angle))
        return angle

    def solve(self, p: PcpParams, atm: Atmosphere) -> PcpResult:
        res = PcpResult()
        res.speed_of_sound_mps = atm.speed_of_sound()
        res.air_density = atm.density()
        res.muzzle_energy_j = 0.5 * (p.mass_grams / 1000.0) * p.muzzle_velocity_mps ** 2
        res.muzzle_mach = p.muzzle_velocity_mps / res.speed_of_sound_mps

        if p.muzzle_velocity_mps <= 1.0 or p.mass_grams <= 0:
            return res

        zero_angle = self.solve_zero_angle(p, atm)
        res.zero_angle_mrad = zero_angle * 1000.0
        res.points = self.fly(p, atm, zero_angle, math.radians(p.shot_angle_deg), p.max_range_m)

        step = max(1.0, p.step_m)
        n = int(p.max_range_m // step)
        for i in range(n + 1):
            pt = res.point_at(i * step)
            if pt:
                res.range_card.append(pt)

        # Zero crossings, max ordinate and the kill-zone window (all along the LOS).
        half_kz = p.kill_zone_cm / 2.0
        prev = res.points[0]
        in_zone = abs(prev.drop_cm) <= half_kz
        if in_zone:
            res.kill_zone_from_m = prev.range_m
        for pt in res.points[1:]:
            if prev.drop_cm < 0 <= pt.drop_cm and res.near_zero_m is None:
                res.near_zero_m = _cross(prev, pt, 0.0)
            elif prev.drop_cm >= 0 > pt.drop_cm and res.far_zero_m is None:
                res.far_zero_m = _cross(prev, pt, 0.0)
            if pt.drop_cm > res.max_ordinate_cm and res.far_zero_m is None:
                res.max_ordinate_cm = pt.drop_cm
                res.max_ordinate_range_m = pt.range_m
            now_in = abs(pt.drop_cm) <= half_kz
            if now_in and not in_zone and res.kill_zone_from_m is None:
                res.kill_zone_from_m = pt.range_m
            if in_zone and not now_in and res.kill_zone_from_m is not None and res.kill_zone_to_m is None:
                if pt.drop_cm < -half_kz:      # only falling out of the bottom ends the window
                    res.kill_zone_to_m = pt.range_m
            in_zone = now_in
            prev = pt
        if res.kill_zone_from_m is not None and res.kill_zone_to_m is None and in_zone:
            res.kill_zone_to_m = res.points[-1].range_m

        if res.muzzle_mach >= TRANSONIC_WARN_MACH:
            res.warnings.append("pcp_warn_transonic")
        if res.points and res.points[-1].range_m < p.max_range_m - 0.5:
            res.warnings.append("pcp_warn_short")
        if res.max_ordinate_cm > half_kz:
            res.warnings.append("pcp_warn_overhop_kz")
        return res

    def best_zero_for_kill_zone(self, p: PcpParams, atm: Atmosphere,
                                result: Optional[PcpResult] = None) -> Optional[Tuple[float, float, float]]:
        """Zero range (m) that makes the kill-zone window as long as possible, on level ground
        without wind. Returns (zero_m, from_m, to_m) or None.

        Moving the zero only tilts the bore by a tiny angle, so the new path is the old one plus a
        straight line through the muzzle: drop'(s) = drop(s) - drop(Z) * s / Z.
        """
        if result is None or p.shot_angle_deg != 0.0 or p.wind_speed_mps != 0.0:
            q = PcpParams(**{**p.__dict__, "shot_angle_deg": 0.0, "wind_speed_mps": 0.0})
            result = self.solve(q, atm)
        pts = result.points
        if len(pts) < 3:
            return None
        half = p.kill_zone_cm / 2.0
        best = None
        top = int(min(p.max_range_m, pts[-1].range_m))
        for zero in range(5, top + 1):
            at_zero = _interpolate(pts, float(zero))
            if at_zero is None:
                break
            tilt = at_zero.drop_cm / zero
            start = None
            end = None
            broken = False
            for pt in pts:
                d = pt.drop_cm - tilt * pt.range_m
                if start is None:
                    if d >= -half:
                        start = pt.range_m
                    continue
                if d > half:
                    broken = True
                    break
                if d < -half:
                    end = pt.range_m
                    break
            if broken or start is None:
                continue
            end = end if end is not None else pts[-1].range_m
            if best is None or end - start > best[2] - best[1]:
                best = (float(zero), start, end)
        return best

    def solve_bc(self, p: PcpParams, atm: Atmosphere,
                 v_near: float, d_near: float, v_far: float, d_far: float) -> Optional[float]:
        """BC that turns v_near at d_near into v_far at d_far (two chrono readings)."""
        if v_far >= v_near or d_far <= d_near or v_near <= 0:
            return None

        def speed_at(bc: float, dist: float, v0: float) -> float:
            q = PcpParams(**{**p.__dict__, "bc": bc, "muzzle_velocity_mps": v0,
                             "wind_speed_mps": 0.0, "shot_angle_deg": 0.0})
            pts = self.fly(q, atm, 0.0, 0.0, dist + 0.5, with_wind=False)
            pt = _interpolate(pts, dist)
            return pt.velocity_mps if pt else 0.0

        span = d_far - d_near
        lo, hi = 0.002, 1.5
        if speed_at(lo, span, v_near) > v_far or speed_at(hi, span, v_near) < v_far:
            return None
        for _ in range(50):
            mid = math.sqrt(lo * hi)
            if speed_at(mid, span, v_near) < v_far:
                lo = mid
            else:
                hi = mid
        return math.sqrt(lo * hi)


def _cross(a: PcpPoint, b: PcpPoint, level: float) -> float:
    span = b.drop_cm - a.drop_cm
    if span == 0:
        return a.range_m
    return a.range_m + (level - a.drop_cm) / span * (b.range_m - a.range_m)
