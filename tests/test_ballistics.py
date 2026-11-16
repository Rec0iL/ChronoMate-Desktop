"""
Tests for BallisticsEngine
"""

import unittest
from core.models import BallisticParams
from core.ballistics import BallisticsEngine


class TestBallistics(unittest.TestCase):
    def setUp(self):
        self.engine = BallisticsEngine()

    def test_trajectory_generation(self):
        params = BallisticParams(
            mass_grams=0.20,
            diameter_mm=5.95,
            muzzle_velocity_mps=100.0,
            launch_angle_deg=0.0,
            starting_height_m=1.5,
            hop_up_rad_s=1000.0,
        )
        trajectory = self.engine.calculate_trajectory(params)
        self.assertGreater(len(trajectory), 10)
        self.assertEqual(trajectory[0].x, 0.0)
        self.assertEqual(trajectory[0].y, 1.5)
        self.assertEqual(trajectory[0].velocity, 100.0)
        # Verify it hits the ground or advances in X
        self.assertGreater(trajectory[-1].x, 30.0)
        self.assertLessEqual(trajectory[-1].y, 0.05)

    def test_probe_trajectory(self):
        params = BallisticParams(mass_grams=0.25, muzzle_velocity_mps=110.0)
        trajectory = self.engine.calculate_trajectory(params)
        probe = self.engine.probe_trajectory(
            trajectory=trajectory,
            target_distance=50.0,
            eye_height_m=1.55,
            target_height_m=1.5,
            probe_x=25.0,
        )
        self.assertIsNotNone(probe)
        self.assertAlmostEqual(probe.distance, 25.0, delta=1.5)
        self.assertGreater(probe.energy_j, 0.0)
        self.assertGreater(probe.time_s, 0.0)

    def test_hop_up_optimizer(self):
        params = BallisticParams(mass_grams=0.28, muzzle_velocity_mps=100.0)
        best_hop = self.engine.optimize_hopup(
            base_params=params,
            shooter_height_m=1.5,
            sight_height_cm=5.0,
            target_height_m=1.5,
            target_distance_m=50.0,
            max_allowed_overhop_cm=15.0,
        )
        self.assertGreaterEqual(best_hop, 0.0)
        self.assertLessEqual(best_hop, 2000.0)


if __name__ == "__main__":
    unittest.main()


class TestBbWeather(unittest.TestCase):
    """Weather & wind for the airsoft BB engine (shared card with the PCP calculator)."""

    def test_crosswind_drift(self):
        from core.models import BallisticParams
        eng = BallisticsEngine()
        calm = BallisticParams(mass_grams=0.25, muzzle_velocity_mps=105, hop_up_rad_s=900)
        windy = BallisticParams(mass_grams=0.25, muzzle_velocity_mps=105, hop_up_rad_s=900,
                                wind_speed_mps=3.0, wind_clock=3.0)
        a = eng.calculate_trajectory(calm)
        b = eng.calculate_trajectory(windy)
        self.assertTrue(all(p.z == 0.0 for p in a))            # no wind: no sideways motion
        at30 = min(b, key=lambda p: abs(p.x - 30.0))
        self.assertLess(at30.z, -0.2)                            # wind from the right pushes left
        calm30 = min(a, key=lambda p: abs(p.x - 30.0))
        lag = calm30.time - 30.0 / 105.0
        self.assertAlmostEqual(at30.z, -3.0 * lag, delta=0.02)  # ≈ lag-time rule

    def test_weather_scales_tuned_density(self):
        from core.config import ConfigManager
        cfg = ConfigManager.get_instance()
        env = cfg.environment
        env.temperature_c, env.pressure_hpa, env.humidity_pct, env.use_altitude = 15.0, 1013.25, 0.0, False
        self.assertAlmostEqual(cfg.effective_air_density(), cfg.air_density_rho, places=6)
        env.temperature_c = 35.0
        self.assertLess(cfg.effective_air_density(), cfg.air_density_rho)
        env.temperature_c, env.humidity_pct = 15.0, 50.0
