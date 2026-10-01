"""No-engine tests of the post-build diagnostic and copied-source hooks."""
from pathlib import Path
import shutil
import tempfile
import unittest

from sweeps.diag_c121_postbuild import audit, instrument, ROOT, BASE_SETTINGS, probe_identity, run_isolated_arms


def log(seq, edge, day=100, tick=1000, pid=1, owner=0, **fields):
    tail = " ".join(f"{k}={v}" for k, v in fields.items())
    return (f"[script:4] [{owner}] [I] POSTBUILD v=1 seq={seq} pass={pid} "
            f"edge={edge} day={day} tick={tick} {tail}")


def phase():
    return [log(1, "pass_begin"), log(2, "phase_begin", kind="staged_full"),
            log(3, "phase_end", day=105, tick=1200, kind="staged_full",
                start_day=100, end_day=105, start_tick=1001, end_tick=1200, ops=1900000),
            log(4, "pass_end", day=105, tick=1201)]


class ReaderTests(unittest.TestCase):
    def test_phase_uses_real_calendar_not_ticks_over_74(self):
        a = audit("\n".join(phase()))
        w = a["windows"][0]
        self.assertEqual((w["days"], w["ticks"], w["ops"]), (5, 199, 1900000))
        self.assertIsNone(a["continuous_affordable_wait"])
        self.assertEqual(a["gaps"], [])
        self.assertEqual(a["issues"][0]["reason"], "censored_next_event")

    def test_next_events_and_new_line_vs_fleet(self):
        lines = phase() + [log(5, "dispatch", 109, 1400, pid=1),
                           log(6, "pass_begin", 109, 1401, pid=2),
                           log(7, "attempt", 110, 1500, pid=2, mode="fleet", rank=0),
                           log(8, "outcome", 111, 1600, pid=2, mode="fleet", outcome="built"),
                           log(9, "outcome", 113, 1800, pid=2, mode="air", outcome="built"),
                           log(10, "pass_end", 113, 1801, pid=2)]
        a = audit("\n".join(lines))
        self.assertEqual({g["metric"]: g["days"] for g in a["gaps"]},
                         {"regen_to_dispatch": 4, "regen_to_attempt": 5, "regen_to_built": 6, "build_gap_any": 2})
        self.assertEqual(a["issues"], [])

    def test_duplicate_and_gap_do_not_produce_windows(self):
        for lines in (phase() + [phase()[-1]], [phase()[0], *phase()[2:]]):
            a = audit("\n".join(lines))
            self.assertFalse(a["windows"])
            self.assertEqual(a["issues"][0]["reason"], "sequence_collision_or_gap")

    def test_no_cross_owner_or_reload_pairing(self):
        lines = phase()[:2] + [log(1, "phase_end", owner=1, kind="staged_full",
                                    start_day=100, end_day=100, start_tick=1000, end_tick=1000, ops=0)]
        self.assertEqual(audit("\n".join(lines))["windows"], [])
        lines = phase()[:2] + ["[script:4] [0] [I] OPEX 1970-1-1 LOAD_RECONCILE"] + phase()[2:]
        self.assertEqual(audit("\n".join(lines))["windows"], [])

    def test_missing_and_negative_measure_not_zero(self):
        for replacement in ("ops=-1", "unknown=1900000"):
            lines = phase()
            lines[2] = lines[2].replace("ops=1900000", replacement)
            self.assertFalse(audit("\n".join(lines))["windows"])

    def test_impossible_boundaries_are_rejected(self):
        lines = phase()
        lines[2] = lines[2].replace("start_day=100", "start_day=99")
        self.assertEqual(audit("\n".join(lines))["issues"][0]["reason"], "phase_boundary_order")

    def test_stop_money_is_only_point_observation(self):
        lines = [log(1, "stop", finance=10, available=-1), log(2, "stop", finance=10, available=20)]
        a = audit("\n".join(lines))
        self.assertEqual([s["financeable_at_stop"] for s in a["stops"]], [None, True])
        self.assertIsNone(a["continuous_affordable_wait"])

    def test_empty_trace_is_not_exposure(self):
        a = audit("AIR_PLAN_PERF total_ops=9000 days=3")
        self.assertEqual(a["counts"], {})
        self.assertEqual(a["windows"], [])


class StagingTests(unittest.TestCase):
    def test_loader_never_mixes_sources_under_same_ai_name(self):
        calls = []
        def loader(*, experiments, **kwargs):
            calls.append(experiments)
            self.assertEqual(len({e["arm"] for e in experiments}), 1)
            self.assertEqual(kwargs["max_workers"], 3)
            return experiments
        experiments = [{"arm": a, "seed": s} for s in (42, 100)
                       for a in ("c115", "c115_trace", "c121", "c121_trace")]
        result = list(run_isolated_arms(loader, experiments, max_workers=3))
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(result), 8)
        self.assertEqual({(e["arm"], e["seed"]) for e in result},
                         {(e["arm"], e["seed"]) for e in experiments})

    def test_identity_checks_negative_controls_and_owner(self):
        logs = {("c115", 42): "no probe", ("c115_trace", 42): log(1, "dispatch")}
        self.assertTrue(probe_identity(logs)["pass"])
        logs["c115", 42] = log(1, "dispatch")
        self.assertFalse(probe_identity(logs)["pass"])
        logs["c115", 42] = "no probe"
        logs["c115_trace", 42] = log(1, "dispatch", owner=1)
        self.assertFalse(probe_identity(logs)["pass"])
        logs["c115_trace", 42] = "no probe"
        self.assertFalse(probe_identity(logs)["pass"])
        self.assertFalse(probe_identity({})["pass"])

    def test_only_instrumentation_in_copy_and_preserved_calls(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "OpexAI"
            shutil.copytree(ROOT / "ai/OpexAI", target)
            before = {p.name: p.read_bytes() for p in target.glob("*.nut")}
            instrument(target)
            changed = sorted(name for name, value in before.items() if (target / name).read_bytes() != value)
            self.assertEqual(changed, ["main.nut", "scheduler_tasks.nut", "task_projects.nut"])
            after = (target / "task_projects.nut").read_text(encoding="utf-8")
            original = before["task_projects.nut"].decode("utf-8")
            for token in ("this._rebuildProjects(fleetPlan)", "OpexIncrementalUpdateProjects(",
                          "OpexAirBatchPlanStillLive(", "OpexAvailableCapital(", "return true;", "return false;"):
                self.assertEqual(after.count(token), original.count(token), token)
            self.assertEqual(after.count("PBOutcome(project, i, attempt.outcome);"), 5)
            self.assertIn('PBEnd("watcher_regen")', after)
            self.assertIn('PBEnd("rail_pending")', after)
            self.assertEqual(before["info.nut"], (target / "info.nut").read_bytes())
            self.assertEqual(before["settings.nut"], (target / "settings.nut").read_bytes())

    def test_c121_only_two_experiments_no_strategy(self):
        self.assertEqual(BASE_SETTINGS["c115"], ())
        self.assertEqual(dict(BASE_SETTINGS["c121"]), {"c121_air_economics": 1, "c121_catalog_incremental": 1})


if __name__ == "__main__":
    unittest.main()