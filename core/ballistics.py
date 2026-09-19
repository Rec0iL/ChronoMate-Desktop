"""
ChronoMate Desktop - Ballistics Engine
Accurate mathematical port of com.example.chronomate.ballistics.BallisticsEngine
Simulates airsoft projectile motion: Gravity, Aerodynamic Drag, Magnus Lift, Spin Damping.
"""

import math
from typing import List, Tuple, Optional
from core.models import BallisticParams, TrajectoryPoint, ProbeResult


class BallisticsEngine:
    def calculate_trajectory(self, params: BallisticParams) -> List[TrajectoryPoint]:
        """
        Calculates trajectory based on standard physics formulas for airsoft BBs.
        Ported directly from the Kotlin / JS logic.
        """
        points: List[TrajectoryPoint] = []

        dt = 0.01
        dti = 16.0
        n = 5000
        step_dt = dt / dti

        m = params.mass_grams / 1000.0  # g to kg
        d = params.diameter_mm / 1000.0  # mm to m
        rho = params.air_density_rho
        cw = params.drag_coefficient_cw
        k = params.magnus_coefficient_k
        cr = params.spin_damping_cr
        g = params.gravity

        # Initial spin (rad/s), inverted per JS logic
        omega = params.hop_up_rad_s * -1.0

        theta_rad = math.radians(params.launch_angle_deg)
        vx = params.muzzle_velocity_mps * math.cos(theta_rad)
        vy = params.muzzle_velocity_mps * math.sin(theta_rad)

        x = 0.0
        y = params.starting_height_m

        area_a = math.pi * (d ** 2) / 4.0
        coeff_c = 0.5 * cw * rho * area_a

        # Initial point at t=0
        points.append(
            TrajectoryPoint(
                x=x,
                y=y,
                velocity=params.muzzle_velocity_mps,
                energy_joules=0.5 * m * (params.muzzle_velocity_mps ** 2),
                time=0.0,
            )
        )

        for i in range(n):
            vx_start = vx
            vy_now = vy
            v_start = math.sqrt(vx_start ** 2 + vy_now ** 2)

            # 1. Update Rotation (decay based on current velocity)
            decay_coeff = cr * v_start
            omega *= math.exp(-decay_coeff * step_dt)

            # 2. Forces
            fg = -m * g
            fdx = -coeff_c * v_start * vx_start
            fdy = -coeff_c * v_start * vy_now

            # Magnus Effect (Lift)
            fmx = k * rho * area_a * vy_now * omega
            fmy = -k * rho * area_a * vx_start * omega

            # 3. Acceleration (F = m*a)
            ax = (fdx + fmx) / m
            ay = (fg + fdy + fmy) / m

            # 4. Update Position
            x += vx_start * step_dt
            y += vy_now * step_dt

            # 5. Update Velocity
            vx += ax * step_dt
            vy += ay * step_dt

            current_v = math.sqrt(vx ** 2 + vy ** 2)
            current_e = 0.5 * m * (v_start ** 2)
            current_time = (i + 1) * step_dt

            points.append(
                TrajectoryPoint(
                    x=x,
                    y=y,
                    velocity=current_v,
                    energy_joules=current_e,
                    time=current_time,
                )
            )

            # Ground collision check
            if y <= 0.0:
                break

        return points

    def probe_trajectory(
        self,
        trajectory: List[TrajectoryPoint],
        target_distance: float,
        eye_height_m: float,
        target_height_m: float,
        probe_x: float,
    ) -> Optional[ProbeResult]:
        """Probes a specific x coordinate along the flight path for telemetry."""
        if not trajectory:
            return None

        # Find closest point to probe_x
        pt = min(trajectory, key=lambda p: abs(p.x - probe_x))
        aim_line_y = eye_height_m + (pt.x / max(target_distance, 0.001)) * (target_height_m - eye_height_m)

        return ProbeResult(
            distance=pt.x,
            bb_height_cm=pt.y * 100.0,
            energy_j=pt.energy_joules,
            time_s=pt.time,
            relative_impact_cm=(pt.y - aim_line_y) * 100.0,
            hold_over_cm=(target_height_m - pt.y) * 100.0,
        )

    def calculate_metrics(
        self,
        trajectory: List[TrajectoryPoint],
        eye_height_m: float,
        target_height_m: float,
        target_distance_m: float,
    ) -> dict:
        """Computes effective range, max range, energy at target, overhop, etc."""
        if not trajectory:
            return {
                "effective_range": 0.0,
                "max_range": 0.0,
                "energy_at_target": 0.0,
                "time_to_target": 0.0,
                "hold_over_cm": 0.0,
                "max_overhop_cm": 0.0,
                "overhop_dist_m": 0.0,
            }

        max_range = trajectory[-1].x

        # Effective range: where BB crosses Line of Sight the 2nd time
        first_cross_idx = -1
        for idx, pt in enumerate(trajectory):
            aim_y = eye_height_m + (pt.x / target_distance_m) * (target_height_m - eye_height_m)
            if pt.y > aim_y:
                first_cross_idx = idx
                break

        if first_cross_idx == -1:
            second_crossing = None
            for pt in trajectory[1:]:
                aim_y = eye_height_m + (pt.x / target_distance_m) * (target_height_m - eye_height_m)
                if pt.y <= aim_y:
                    second_crossing = pt
                    break
            effective_range = second_crossing.x if second_crossing else 0.0
        else:
            second_crossing = None
            for pt in trajectory[first_cross_idx:]:
                aim_y = eye_height_m + (pt.x / target_distance_m) * (target_height_m - eye_height_m)
                if pt.y <= aim_y:
                    second_crossing = pt
                    break
            effective_range = second_crossing.x if second_crossing else trajectory[-1].x

        pt_target = min(trajectory, key=lambda p: abs(p.x - target_distance_m))
        energy_at_target = pt_target.energy_joules if pt_target else 0.0
        time_to_target = pt_target.time if pt_target else 0.0
        hold_over_cm = (target_height_m - pt_target.y) * 100.0 if pt_target else 0.0

        max_oh = 0.0
        max_oh_dist = 0.0
        for pt in trajectory:
            if pt.x <= target_distance_m:
                aim_line_y = eye_height_m + (pt.x / target_distance_m) * (target_height_m - eye_height_m)
                diff = pt.y - aim_line_y
                if diff > max_oh:
                    max_oh = diff
                    max_oh_dist = pt.x

        return {
            "effective_range": effective_range,
            "max_range": max_range,
            "energy_at_target": energy_at_target,
            "time_to_target": time_to_target,
            "hold_over_cm": hold_over_cm,
            "max_overhop_cm": max_oh * 100.0,
            "overhop_dist_m": max_oh_dist,
        }

    def optimize_hopup(
        self,
        base_params: BallisticParams,
        shooter_height_m: float,
        sight_height_cm: float,
        target_height_m: float,
        target_distance_m: float,
        max_allowed_overhop_cm: float,
    ) -> float:
        """
        Finds the optimal hop-up rotation (rad/s) maximizing effective range
        while remaining within the user's max overhop constraint.
        """
        eye_height_m = shooter_height_m + (sight_height_cm / 100.0)
        aim_angle_deg = math.degrees(math.atan2(target_height_m - eye_height_m, target_distance_m))

        best_hop = base_params.hop_up_rad_s
        max_range_val = 0.0
        max_allowed_overhop_m = max_allowed_overhop_cm / 100.0

        # Step through hop from 0 to 2000 rad/s
        for h in range(0, 2005, 10):
            p = BallisticParams(
                mass_grams=base_params.mass_grams,
                muzzle_velocity_mps=base_params.muzzle_velocity_mps,
                hop_up_rad_s=float(h),
                starting_height_m=shooter_height_m,
                launch_angle_deg=aim_angle_deg,
                diameter_mm=base_params.diameter_mm,
                air_density_rho=base_params.air_density_rho,
                drag_coefficient_cw=base_params.drag_coefficient_cw,
                magnus_coefficient_k=base_params.magnus_coefficient_k,
                spin_damping_cr=base_params.spin_damping_cr,
                gravity=base_params.gravity,
            )
            traj = self.calculate_trajectory(p)

            # Check overhop limit
            current_overhop = 0.0
            for pt in traj:
                if pt.x <= target_distance_m:
                    aim_y = eye_height_m + (pt.x / target_distance_m) * (target_height_m - eye_height_m)
                    diff = pt.y - aim_y
                    if diff > current_overhop:
                        current_overhop = diff

            if current_overhop <= max_allowed_overhop_m:
                # Find effective range
                cross_idx = -1
                for idx, pt in enumerate(traj):
                    aim_y = eye_height_m + (pt.x / target_distance_m) * (target_height_m - eye_height_m)
                    if pt.y > aim_y:
                        cross_idx = idx
                        break

                current_eff_range = 0.0
                if cross_idx != -1:
                    for pt in traj[cross_idx:]:
                        aim_y = eye_height_m + (pt.x / target_distance_m) * (target_height_m - eye_height_m)
                        if pt.y <= aim_y:
                            current_eff_range = pt.x
                            break

                if current_eff_range > max_range_val:
                    max_range_val = current_eff_range
                    best_hop = float(h)

        return best_hop
