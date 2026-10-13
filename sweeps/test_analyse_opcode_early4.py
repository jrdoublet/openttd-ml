import tempfile
import unittest
from pathlib import Path

from analyse_opcode_early4 import read_log


def log(text):
    return "[2026-10-12 12:00:00] dbg: [script:4] [0] [I] " + text + "\n"


class EarlyOpcodeAnalysisTests(unittest.TestCase):
    def test_years_and_exclusive_loop_posts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.log"
            lines = [
                log("LOOP_OPS y=1970 post=_year n=1 ops=0 tk=10 max=0"),
                log("LOOP_OPS y=1970 post=orchestrator n=1 ops=55000 tk=5 max=55000"),
                log("LOOP_OPS y=1970 post=tg_plan n=1 ops=3000 tk=0 max=3000"),
                log("LOOP_OPS y=1970 post=tg_lines n=1 ops=7 tk=0 max=7"),
                log("LOOP_OPS y=1970 post=sleep_left n=1 ops=45000 tk=0 max=45000"),
                log("LOOP_OPS y=1970 post=sleep_ctx_no_pending_worker n=1 ops=45000 tk=0 max=45000"),
                log("LOOP_OPS y=1970 post=sleep_cap3k_no_pending_worker n=1 ops=42000 tk=0 max=42000"),
                log("OPEX 1971-1-5 C39_PASS_CLOCK phase=annual year=1971 key=projects|slice "
                    "passes=2 days=1 ticks=3 ops=2200 slice_days=1 slice_ticks=2 slice_ops=1700"),
                log("OPEX 1970-1-5 AIR_LIGHT edge=exit ops=100 prepare_ops=30 sites_ops=70"),
                log("OPEX 1970-1-5 CATALOG_COST reason=partial path=partial "
                    "total_ops=200 air_ops=80 road_ops=120"),
                log("OPEX 1970-1-5 CATALOG_COST_SLICE slice_ops=90 same_tick_slices=2"),
                log("OPEX 1970-1-6 PROJECTS_COST build_ops=50 fleet_ops=10 regen_ops=200 regen=full"),
                log("OPEX 1970-1-6 SCHED_IDLE t=projects w=0 r=projects_examined_no_effect "
                    "op=80 d=0 tk=0"),
                "[2026-10-12 12:00:00] dbg: [script:4] [1] [I] "
                "1970-2-22 CheckBuildVehicle 0[days] 0[ticks] 1681[ops] 2[times]\n",
            ]
            path.write_text("".join(lines), encoding="utf-8")
            report = read_log(path)
        loop = report["loop"]["1970"]
        self.assertEqual(loop["ticks"], 10)
        self.assertEqual(loop["top_executed.ops"], 55000)
        self.assertEqual(loop["top_unexplained.ops"], 0)
        self.assertEqual(loop["sleep_left.ops"], 45000)
        self.assertEqual(report["task"]["1970"]["task|projects.ops"], 500)
        self.assertEqual(report["task"]["1970"]["rail_astar_slice.ops"], 1700)
        self.assertEqual(report["air"]["1970"]["prepare_ops"], 30)
        self.assertEqual(report["catalog"]["1970"]["total_ops"], 200)
        self.assertEqual(report["catalog_slice"]["1970"]["slice_ops"], 90)
        self.assertEqual(report["aaa_partial"]["1970"]["CheckBuildVehicle.ops"], 1681)
        self.assertEqual(report["projects"]["1970"]["regen.full.ops"], 200)
        self.assertEqual(report["idle"]["1970"]
                         ["projects|projects_examined_no_effect|w0.calls"], 1)

    def test_profiled_main_parity_with_core_loop(self):
        root = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
        src = (root / "probes.nut").read_text(encoding="utf-8")
        main = (root / "main.nut").read_text(encoding="utf-8")
        for fragment in (
            "this._refreshSaveProjection();",
            "this._saveProjection = null;",
            "OpexC121StationFluxStep(this._catalog);",
            "this._runOrchestratorTick();",
            "AIController.Sleep(1);",
        ):
            self.assertIn(fragment, src)
            self.assertIn(fragment, main)
        self.assertIn('"sleep_cap3k_" + opportunityKind', src)
        self.assertIn('"sleep_ctx_" + opportunityKind', src)


if __name__ == "__main__":
    unittest.main()
