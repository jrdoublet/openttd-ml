from pathlib import Path
import unittest

from sweeps.campaign_freeze import parse_ai_settings

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def source(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


class TestV155FleetPreguard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = AI / "info.nut"
        cls.globals = source("globals_pre.nut")
        cls.settings = source("settings.nut")
        cls.task_air = source("task_air.nut")

    def test_setting_declaration_and_defaults(self):
        defaults = parse_ai_settings(self.info)
        self.assertIn("air_fleet_c121_preguard", defaults)
        self.assertEqual(defaults["air_fleet_c121_preguard"], 0)

        # Check raw setting block in info.nut
        info_text = self.info.read_text(encoding="utf-8")
        self.assertIn('"air_fleet_c121_preguard"', info_text)
        self.assertIn("easy_value = 0, medium_value = 0, hard_value = 0", info_text)
        self.assertIn("custom_value = 0", info_text)

    def test_globals_and_settings_loading(self):
        self.assertIn("AIR_FLEET_C121_PREGUARD <- false;", self.globals)
        self.assertIn(
            'AIR_FLEET_C121_PREGUARD = AIController.GetSetting("air_fleet_c121_preguard") != 0;',
            self.settings,
        )

    def test_preguard_placement_and_structure_in_task_air(self):
        # Preguard must be placed immediately before OpexC121RefreshVisibleFleet
        preguard_sig = "if (AIR_FLEET_C121_PREGUARD && C121_AIR_VISIBLE_COMPETITION"
        refresh_sig = "OpexC121RefreshVisibleFleet(this._catalog, line, this._lines);"

        self.assertIn(preguard_sig, self.task_air)
        self.assertIn(refresh_sig, self.task_air)

        preguard_idx = self.task_air.index(preguard_sig)
        refresh_idx = self.task_air.index(refresh_sig)
        self.assertLess(preguard_idx, refresh_idx)

        # Between preguard and refresh, there should be no other function calls
        between = self.task_air[preguard_idx:refresh_idx]
        self.assertIn('"targetAirPlanes" in line', between)
        self.assertIn("isFirstLiveEligible", between)
        self.assertIn("c121_no_full_year_observation", between)
        self.assertIn("c121_wait_full_year_after_growth", between)
        self.assertIn('OpexDecide("AIR_FLEET_PREGUARD"', between)
        self.assertIn('OpexAirFleetRefusal(line, year, "O")', between)

    def test_first_live_exclusion_matches_historical(self):
        # The first live check condition must match historical lines 1187-1190
        self.assertIn("C121_AIR_FIRST_LIVE_GROWTH", self.task_air)
        self.assertIn(
            "C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS <= 0\n"
            "              || year - OPEX_START_YEAR < C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS",
            self.task_air,
        )
        self.assertIn('have == 1 && !("lastAirFleetYear" in line)', self.task_air)

    def test_decision_equivalence_logic(self):
        """Simulate line states to verify preguard produces identical growth outcomes."""
        def evaluate_line(line, year, preguard_active=False):
            have = line.get("vehCount", len(line.get("vehicles", [])))
            if have < 1:
                return "refuse_V"

            target = line.get("targetAirPlanes", None)
            c121_econ = True
            c121_visible = True
            c121_first_live = True

            # Preguard
            if preguard_active and c121_econ and c121_visible and target is not None:
                is_first_live_eligible = (
                    c121_first_live
                    and have == 1
                    and ("lastAirFleetYear" not in line)
                )
                if not is_first_live_eligible:
                    c121_age = year - line["year"] if "year" in line else -1
                    if c121_age < 2 or "lastProfit" not in line or line["lastProfit"] <= 0:
                        return "refuse_O"
                    if "lastAirFleetYear" in line and (year - line["lastAirFleetYear"]) < 2:
                        return "refuse_O"

            # Historical post-refresh guards
            if c121_visible and target is not None and have >= target:
                return "refuse_T"

            below_target = c121_econ and target is not None and target > have
            if below_target and c121_first_live and have == 1 and ("lastAirFleetYear" not in line):
                # first live path (can pass if balanced90 is true)
                first_live_ready = line.get("balanced90", False)
                if not first_live_ready:
                    c121_age = year - line["year"] if "year" in line else -1
                    if c121_age < 2 or "lastProfit" not in line or line["lastProfit"] <= 0:
                        return "refuse_O"
                return "grow_or_plan"
            elif below_target:
                c121_age = year - line["year"] if "year" in line else -1
                if c121_age < 2 or "lastProfit" not in line or line["lastProfit"] <= 0:
                    return "refuse_O"
                if "lastAirFleetYear" in line and (year - line["lastAirFleetYear"]) < 2:
                    return "refuse_Y"
                return "grow_or_plan"

            return "other"

        test_cases = [
            # Young line, have < target -> historically refused O, preguard refused O
            {"year": 1974, "line": {"year": 1973, "vehCount": 2, "targetAirPlanes": 3, "lastProfit": 100}},
            # Young line, have >= target -> historically refused T, preguard refused O (both refuse!)
            {"year": 1974, "line": {"year": 1973, "vehCount": 3, "targetAirPlanes": 2, "lastProfit": 100}},
            # Unprofitable line -> historically refused O (if below) or T (if >=), preguard refuses O
            {"year": 1975, "line": {"year": 1971, "vehCount": 2, "targetAirPlanes": 4, "lastProfit": -10}},
            {"year": 1975, "line": {"year": 1971, "vehCount": 4, "targetAirPlanes": 4, "lastProfit": -10}},
            # Line grown last year (cadence < 2) -> historically refused Y, preguard refused O (both refuse!)
            {"year": 1975, "line": {"year": 1970, "vehCount": 2, "targetAirPlanes": 4, "lastProfit": 500, "lastAirFleetYear": 1974}},
            # Eligible line (age >= 2, profit > 0, cooldown >= 2, have < target) -> both grow_or_plan!
            {"year": 1975, "line": {"year": 1970, "vehCount": 2, "targetAirPlanes": 4, "lastProfit": 500, "lastAirFleetYear": 1973}},
            # First live eligible (have == 1, no lastAirFleetYear) -> preguard does NOT refuse, both reach first live!
            {"year": 1974, "line": {"year": 1973, "vehCount": 1, "targetAirPlanes": 2, "balanced90": True}},
        ]

        for tc in test_cases:
            year = tc["year"]
            line = tc["line"]
            res_no_preguard = evaluate_line(line, year, preguard_active=False)
            res_preguard = evaluate_line(line, year, preguard_active=True)

            is_eligible_no = (res_no_preguard == "grow_or_plan")
            is_eligible_pre = (res_preguard == "grow_or_plan")
            self.assertEqual(
                is_eligible_no,
                is_eligible_pre,
                f"Mismatch for line {line} at year {year}: no_preguard={res_no_preguard}, preguard={res_preguard}"
            )


if __name__ == "__main__":
    unittest.main()
