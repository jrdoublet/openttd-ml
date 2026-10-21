"""Static contracts for V303; engine diagnostics still required for Squirrel."""
import re
import tempfile
import unittest
from pathlib import Path

from test_v294cd_rail_astar import function_body, read
from diag_v303_reverse import analyse


class ReverseContracts(unittest.TestCase):
    def test_setting_is_opt_in_and_read_once(self):
        block = re.search(r'name = "v303_reverse_mode",(.*?)\}\);', read("info.nut"), re.S)[1]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{level}_value = 0", block)
        self.assertIn("min_value = 0, max_value = 2", block)
        self.assertIn("V303_REVERSE_MODE <- 0;", read("globals_pre.nut"))
        self.assertEqual(read("settings.nut").count('GetSetting("v303_reverse_mode")'), 1)

    def test_legacy_probe_remains_synchronous_and_guarded(self):
        body = function_body(read("task_rail.nut"), "OpexAI::_startRailSearch")
        self.assertLess(body.index("if (V303_REVERSE_MODE == 0)"), body.index("OpexV294fReverseProbe("))
        probe = function_body(read("builder_rail.nut"), "OpexV294fReverseProbe")
        self.assertIn("revPf.FindPath(iterationCap)", probe)
        self.assertIn("revTiles.reverse();", probe)
        self.assertIn("DECISION_LOG ? OpexOpsMeasureBegin() : null", probe)

    def test_slices_budget_direction_and_empty_queue(self):
        body = function_body(read("builder_rail.nut"), "OpexV303AdvanceReverse")
        for contract in (
            "s.totalCap - s.reverseSpent - s.forwardSpent",
            "s.reverseCap - s.reverseSpent", "local chunk = PATH_CHUNK;",
            "if (chunk > remaining) chunk = remaining;", "pf.FindPath(chunk)",
            "pf.LastConsumed()", "if (reverse) tiles.reverse();",
            "s.reverseTurn = !reverse;", "s.forwardDone && s.reverseDone",
            "s.forwardSpent = slice.iterations;", "slice.iterations += s.reverseSpent;",
            "OpexAdvanceSegmentedSearch(state.segmented, RAIL_SEARCH_SLICE, deadlineTick)",
        ):
            self.assertIn(contract, body)
        self.assertNotIn("while (", body)
        self.assertNotIn("Sleep(", body)
        create = function_body(read("builder_rail.nut"), "OpexV303CreateReverse")
        self.assertIn("totalCap = plan.iterationBudget + V294_RAIL_REVERSE_PROBE", create)
        self.assertIn("plan.plansB, plan.plansA", create)

    def test_live_search_is_dropped_even_without_old_save_marker(self):
        persist = read("persist.nut")
        load = function_body(persist, "OpexAI::Load")
        self.assertIn("this._railSearch = null;", load)
        self.assertLess(load.index("this._railSearch = null;"), load.index("data."))
        save = function_body(persist, "OpexAI::Save")
        self.assertIn("railSearchPending = this._railSearch != null", save)
        self.assertNotIn("reversePf", save)
        self.assertNotIn(".v303", save)
        task = function_body(read("task_rail.nut"), "OpexAI::_continueRailSearch")
        self.assertIn('if ("v303" in state) state.v303 = null;', task)


class DecoderContracts(unittest.TestCase):
    def test_company_filter_distances_and_missing_measurements(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "reference_seed42.log"
            p.write_text(
                "[script:4] [0] OPEX 1970 V294F_PROBE ok=1 iters=70 manh=160 mode=0 ticks=9 max_ticks=9 ops=90000\n"
                "[script:4] [1] OPEX 1970 V294F_PROBE ok=1 iters=999 manh=50\n"
                "[script:4] [0] OPEX 1970 RAIL_ATTEMPT src=1 dst=2 manh=160 ok=0 reason=ABND iters=5000\n"
                "[script:4] [0] OPEX 1970 V294F_PROBE ok=0 iters=0 manh=50\n",
                encoding="utf-8")
            row = analyse(directory)["arms"]["reference"]
            self.assertEqual(row["probes"]["n"], 2)
            self.assertEqual(row["probes"]["ticks"]["n"], 1)
            self.assertEqual(row["probe_found"], 1)
            self.assertEqual(row["distance"][">=160"]["abnd"], 1)
            self.assertEqual(row["distance"]["<60"]["probes"], 1)


if __name__ == "__main__":
    unittest.main()
