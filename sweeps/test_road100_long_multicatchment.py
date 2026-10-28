"""Targeted unit tests for ROAD100 multi-catchment marker propagation in LONG candidates."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 1
    cursor = brace + 1
    while depth > 0 and cursor < len(source):
        char = source[cursor]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        cursor += 1
    return source[start:cursor]


def simulate_multicatchment_pipeline(
    *,
    road100_multicatchment_setting: bool,
    town_already_served: bool,
) -> dict:
    """End-to-end simulation: preliminary -> candidate -> selection filter -> task live veto."""
    # 1. Preliminary long generation
    preliminary_long = {
        "mode": "road",
        "kind": "pax",
        "srcTown": 1,
        "dstTown": 2,
        "road100MultiCatchment": road100_multicatchment_setting,
    }

    # 2. Candidate admission (OpexRoad100LongBuildCandidate)
    candidate = {
        "mode": preliminary_long["mode"],
        "kind": preliminary_long["kind"],
        "srcTown": preliminary_long["srcTown"],
        "dstTown": preliminary_long["dstTown"],
    }
    # Propagation of multi-catchment marker
    if preliminary_long.get("road100MultiCatchment"):
        candidate["road100MultiCatchment"] = True

    # 3. Selection live filter (OpexRoad100FilterLiveBusTownProjects in projects_selection.nut)
    # Check if project is dropped
    is_dropped_by_selection = False
    multi_bypass_selection = (
        road100_multicatchment_setting
        and candidate.get("road100MultiCatchment", False)
    )
    if town_already_served and not multi_bypass_selection:
        is_dropped_by_selection = True

    # 4. Task live veto (OpexAI::_tryBuildRoadProject in task_road.nut)
    # Check if project triggers town_already_bus_served veto
    is_rejected_by_task = False
    rejection_reason = None
    multi_bypass_task = (
        candidate.get("road100MultiCatchment", False)
        and road100_multicatchment_setting
    )
    if town_already_served and not multi_bypass_task:
        is_rejected_by_task = True
        rejection_reason = "town_already_bus_served"

    return {
        "candidate_has_marker": candidate.get("road100MultiCatchment", False),
        "survives_selection": not is_dropped_by_selection,
        "survives_task": not is_rejected_by_task,
        "rejection_reason": rejection_reason,
    }


class Road100LongMultiCatchmentTests(unittest.TestCase):
    def setUp(self):
        self.candidates_src = (ROOT / "ai" / "OpexAI" / "candidates.nut").read_text(encoding="utf-8")
        self.task_road_src = (ROOT / "ai" / "OpexAI" / "task_road.nut").read_text(encoding="utf-8")
        self.selection_src = (ROOT / "ai" / "OpexAI" / "projects_selection.nut").read_text(encoding="utf-8")

    def test_candidates_nut_copies_multicatchment_in_long_build_candidate(self):
        """OpexRoad100LongBuildCandidate must copy road100MultiCatchment from preliminary."""
        body = function_body(self.candidates_src, "function OpexRoad100LongBuildCandidate(")
        self.assertIn('("road100MultiCatchment" in preliminary) && preliminary.road100MultiCatchment', body)
        self.assertIn('candidate.road100MultiCatchment <- true;', body)

    def test_preliminary_long_sets_multicatchment_from_setting(self):
        """preliminaryLong in generator must initialize road100MultiCatchment from ROAD100_MULTICATCHMENT."""
        self.assertIn('road100MultiCatchment = ROAD100_MULTICATCHMENT', self.candidates_src)

    def test_live_vetos_check_both_marker_and_global_setting(self):
        """Task and selection must require both candidate marker and ROAD100_MULTICATCHMENT setting."""
        self.assertIn(
            '!(ROAD100_MULTICATCHMENT\n             && ("road100MultiCatchment" in project.payload)\n             && project.payload.road100MultiCatchment)',
            self.selection_src,
        )
        self.assertIn(
            '!((("road100MultiCatchment" in candidate) && candidate.road100MultiCatchment)\n              && ROAD100_MULTICATCHMENT)',
            self.task_road_src,
        )

    def test_multicatchment_active_allows_long_project_on_served_town(self):
        """When ROAD100_MULTICATCHMENT is ON, LONG project on already served town survives vetos."""
        res = simulate_multicatchment_pipeline(
            road100_multicatchment_setting=True,
            town_already_served=True,
        )
        self.assertTrue(res["candidate_has_marker"])
        self.assertTrue(res["survives_selection"])
        self.assertTrue(res["survives_task"])
        self.assertIsNone(res["rejection_reason"])

    def test_multicatchment_off_rejects_long_project_on_served_town(self):
        """When ROAD100_MULTICATCHMENT is OFF (default), project is rejected as town_already_bus_served."""
        res = simulate_multicatchment_pipeline(
            road100_multicatchment_setting=False,
            town_already_served=True,
        )
        self.assertFalse(res["candidate_has_marker"])
        self.assertFalse(res["survives_selection"])
        self.assertFalse(res["survives_task"])
        self.assertEqual(res["rejection_reason"], "town_already_bus_served")

    def test_unserved_town_always_survives(self):
        """If town is not served, project survives regardless of multicatchment setting."""
        res_off = simulate_multicatchment_pipeline(
            road100_multicatchment_setting=False,
            town_already_served=False,
        )
        self.assertTrue(res_off["survives_selection"])
        self.assertTrue(res_off["survives_task"])

        res_on = simulate_multicatchment_pipeline(
            road100_multicatchment_setting=True,
            town_already_served=False,
        )
        self.assertTrue(res_on["survives_selection"])
        self.assertTrue(res_on["survives_task"])


if __name__ == "__main__":
    unittest.main()
