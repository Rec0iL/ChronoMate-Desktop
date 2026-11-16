"""
PCP airgun ballistics: physics sanity checks plus fixed reference numbers.
The same reference numbers are asserted in the Android app (PcpEngineTest.kt), so both apps
must compute identical range cards.
"""

import math
import unittest

from core.pcp_ballistics import (
    Atmosphere, PcpBallistics, PcpParams, GRAIN_TO_GRAM, drag_coefficient,
)

# (case, distance m) -> (drop cm, drift cm, velocity m/s)
REFERENCE = {
    ("base", 25): (0.1355, 0.0, 244.3650),
    ("base", 50): (-5.0159, 0.0, 220.0634),
    ("base", 100): (-56.2234, 0.0, 180.3056),
    ("g7slug", 25): (1.1753, -0.4954, 277.4201),
    ("g7slug", 100): (-25.4253, -8.1115, 243.8517),
    ("alt177", 50): (-9.6003, 7.9195, 177.3047),
    ("alt177", 100): (-95.5985, 34.8558, 126.7843),
}


def cases():
    return {
        "base": (PcpParams(mass_grams=18.13 * GRAIN_TO_GRAM, bc=0.035, muzzle_velocity_mps=274.32,
                           zero_range_m=30, sight_height_cm=5),
                 Atmosphere(15, 1013.25, 0)),
        "g7slug": (PcpParams(mass_grams=2.2, bc=0.045, drag_model="G7", muzzle_velocity_mps=290,
                             zero_range_m=50, sight_height_cm=6, wind_speed_mps=3, wind_clock=2,
                             shot_angle_deg=15, max_range_m=150),
                   Atmosphere(25, 950, 70)),
        "alt177": (PcpParams(mass_grams=0.547, bc=0.021, muzzle_velocity_mps=250, zero_range_m=25,
                             sight_height_cm=4.5, wind_speed_mps=2, wind_clock=9),
                   Atmosphere(-5, 0, 30, 600, True)),
    }


class TestPcpBallistics(unittest.TestCase):
    def setUp(self):
        self.eng = PcpBallistics()

    def test_reference_numbers(self):
        results = {name: self.eng.solve(p, a) for name, (p, a) in cases().items()}
        for (name, dist), (drop, drift, vel) in REFERENCE.items():
            pt = results[name].point_at(dist)
            self.assertIsNotNone(pt, f"{name}@{dist}")
            self.assertAlmostEqual(pt.drop_cm, drop, delta=0.002, msg=f"{name}@{dist} drop")
            self.assertAlmostEqual(pt.drift_cm, drift, delta=0.002, msg=f"{name}@{dist} drift")
            self.assertAlmostEqual(pt.velocity_mps, vel, delta=0.002, msg=f"{name}@{dist} v")

    def test_no_drag_matches_the_parabola(self):
        # An enormous BC means no drag: y = -g t² / 2 exactly, x = v t.
        p = PcpParams(bc=1e6, muzzle_velocity_mps=100.0, sight_height_cm=0.0)
        pts = self.eng.fly(p, Atmosphere(), 0.0, 0.0, 50.0, with_wind=False)
        pt = next(q for q in pts if q.range_m >= 50.0)
        t = pt.range_m / 100.0
        self.assertAlmostEqual(pt.drop_cm, -0.5 * p.gravity * t * t * 100.0, places=3)

    def test_zero_is_exact(self):
        p, a = cases()["base"]
        for zero in (15.0, 30.0, 45.0):
            p.zero_range_m = zero
            r = self.eng.solve(p, a)
            self.assertAlmostEqual(r.point_at(zero).drop_cm, 0.0, delta=0.01)

    def test_wind_drift_matches_lag_time_rule(self):
        # Crosswind drift = wind × (time of flight − range / muzzle velocity)  (Didion's rule)
        p, a = cases()["base"]
        p.wind_speed_mps, p.wind_clock = 4.0, 3.0
        r = self.eng.solve(p, a)
        for d in (25, 50, 100):
            pt = r.point_at(d)
            lag = pt.time_s - d / p.muzzle_velocity_mps
            self.assertAlmostEqual(pt.drift_cm, -4.0 * lag * 100.0, delta=0.05)

    def test_uphill_shoots_high(self):
        p, a = cases()["base"]
        level = self.eng.solve(p, a).point_at(80).drop_cm
        p.shot_angle_deg = 30.0
        uphill = self.eng.solve(p, a).point_at(80).drop_cm
        self.assertGreater(uphill, level)   # rifleman's rule: less drop on an incline

    def test_bc_from_two_speeds(self):
        p, a = cases()["base"]
        r = self.eng.solve(p, a)
        v40 = r.point_at(40).velocity_mps
        bc = self.eng.solve_bc(p, a, p.muzzle_velocity_mps, 0.0, v40, 40.0)
        self.assertAlmostEqual(bc, 0.035, delta=0.0003)
        self.assertIsNone(self.eng.solve_bc(p, a, 250.0, 0.0, 260.0, 20.0))  # faster far away: impossible

    def test_atmosphere(self):
        std = Atmosphere(15, 1013.25, 0)
        self.assertAlmostEqual(std.density(), 1.225, places=3)
        self.assertAlmostEqual(std.speed_of_sound(), 340.3, places=1)
        self.assertLess(Atmosphere(30, 1013.25, 0).density(), std.density())        # warm air is thinner
        self.assertAlmostEqual(Atmosphere(use_altitude=True, altitude_m=0).station_pressure_pa(), 101325, places=0)

    def test_drag_tables(self):
        self.assertAlmostEqual(drag_coefficient("G1", 0.5), 0.2032)
        self.assertAlmostEqual(drag_coefficient("G7", 1.0), 0.3803)
        self.assertAlmostEqual(drag_coefficient("G1", 0.9125), (0.3415 + 0.3734) / 2, places=6)
        self.assertGreater(drag_coefficient("G1", 0.95), drag_coefficient("G1", 0.6))  # transonic rise

    def test_transonic_warning(self):
        p, a = cases()["base"]
        p.muzzle_velocity_mps = 320.0   # Mach 0.94 at 15 °C
        self.assertIn("pcp_warn_transonic", self.eng.solve(p, a).warnings)

    def test_best_zero_for_kill_zone(self):
        p, a = cases()["base"]
        p.kill_zone_cm = 3.0
        zero, start, end = self.eng.best_zero_for_kill_zone(p, a)
        p.zero_range_m = zero
        r = self.eng.solve(p, a)
        self.assertLessEqual(r.max_ordinate_cm, 1.5 + 0.05)
        self.assertAlmostEqual(r.kill_zone_to_m, end, delta=0.5)
        self.assertGreater(end - start, 30.0)


if __name__ == "__main__":
    unittest.main()
