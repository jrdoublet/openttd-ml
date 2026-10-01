"""Synthetic log fixtures only: no Squirrel compiler, planner or physical simulation."""
import contextlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from parallel_bypass_audit import analyse_text, main, read_artifact


def line(body, company=0, day=1):
    return f"[script:4] [{company}] [I] OPEX 1970-9-{day} {body}"


def slot(phase, fields="", company=0, pass_id=6, day=1):
    return line(f"C78_SLOT phase={phase} pass={pass_id} cycle=5 tick=4800 {fields}", company, day)


START = slot("projects_pass", "state=ok")
FIRST = [
    slot("air_attempt", "rank=0 src=10 dst=20 finance=60 available=200 built_before=0"),
    line("AIR_BUILD line=8 src=10 dst=20 src_town=1 dst_town=2 planes=1 cost=60"),
    slot("air_outcome", "rank=0 src=10 dst=20 outcome=built reason=built"),
]
BYPASS = "[script:4] [0] [I] C75_BYPASS phase=consumed mode=air capital=60 available=140 k_pass=30 built_before=1"
NEXT_ATTEMPT = slot("air_attempt", "rank=3 src=40 dst=50 finance=60 available=140 built_before=1")
DEAD = line("PROJECT_DISCARD rank=1 mode=air src=10 dst=30 reason=batch_plan_dead", day=2)
NEXT_SUCCESS = [
    line("AIR_BUILD line=9 src=40 dst=50 src_town=4 dst_town=5 planes=1 cost=60", day=2),
    slot("air_outcome", "rank=3 src=40 dst=50 outcome=built reason=built", day=2),
]
END = slot("projects_exit", "built_count=2 stop=done", day=2)
# Publication of DEAD is late, matching task_air.nut, not reordered by date.
STALE_THEN_VALID = [START, *FIRST, BYPASS, NEXT_ATTEMPT, DEAD, *NEXT_SUCCESS, END]
TOO_EXPENSIVE = [START, *FIRST,
                 slot("pass_stop", "reason=cash next_rank=1 next_mode=air finance=160 available=140 threshold=30"),
                 slot("projects_exit", "built_count=1 stop=cash")]
REAL_FAILURE = [START, *FIRST, BYPASS, NEXT_ATTEMPT,
                line("PROJECT_DISCARD rank=3 mode=air src=40 dst=50 reason=build_failed detail=BFAIL error=771"),
                slot("air_outcome", "rank=3 src=40 dst=50 outcome=rejected reason=build_failed"),
                slot("pass_stop", "reason=k_pass next_rank=4 next_mode=air finance=60 available=140 threshold=30"),
                slot("projects_exit", "built_count=1 stop=k_pass")]


def audit(rows):
    return analyse_text("\n".join(rows), "synthetic_fixture", "synthetic_log_fixture")


class TestParallelBypassAudit(unittest.TestCase):
    def test_stale_then_valid_is_observation_not_causal_gain(self):
        result = audit(STALE_THEN_VALID)
        p = result["passes"][0]
        self.assertEqual(len(p["sequences"]), 1)
        seq = p["sequences"][0]
        self.assertEqual(seq["dead_ranks"], [1])
        self.assertTrue(seq["following_bypass_linked"])
        self.assertFalse(seq["causal_advancement_proven"])
        dead = p["candidates"][1]
        self.assertTrue(dead["examined"])
        self.assertTrue(dead["rejected"])
        self.assertIsNone(dead["executor_attempted"])
        self.assertIsNone(dead["bypass_consumed"])
        self.assertIsNone(result["coverage"]["additional_airports"])

    def test_preserves_delayed_publication_not_fake_chronology(self):
        result = audit(STALE_THEN_VALID)
        events = result["events"]
        dead = next(e for e in events if e["tag"] == "PROJECT_DISCARD")
        bypass = next(e for e in events if e["tag"] == "C75_BYPASS")
        self.assertGreater(dead["line"], bypass["line"])
        self.assertEqual(dead["date"], "1970-09-02")
        self.assertIsNone(bypass["date"])

    def test_expensive_candidate_stops_without_bypass_or_attempt(self):
        p = audit(TOO_EXPENSIVE)["passes"][0]
        self.assertEqual(p["sequences"], [])
        self.assertEqual(len(p["candidates"]), 1)
        self.assertEqual(p["stops"][0]["fields"]["reason"], "cash")
        self.assertEqual(p["stops"][0]["fields"]["next_rank"], "1")
        gate = p["gate_candidates"][0]
        self.assertTrue(gate["examined"])
        self.assertIsNone(gate["executor_attempted"])
        self.assertEqual(gate["finance_gbp"], 160)

    def test_real_failure_consumes_bypass_not_success(self):
        p = audit(REAL_FAILURE)["passes"][0]
        candidate = p["candidates"][-1]
        self.assertTrue(candidate["bypass_consumed"])
        self.assertTrue(candidate["physical_builder_attempted"])
        self.assertFalse(candidate["construction_succeeded"])
        self.assertEqual(p["sequences"], [])
        self.assertEqual(p["stops"][0]["fields"]["next_rank"], "4")

    def test_executor_precheck_is_not_physical_build(self):
        rows = [s.replace("build_failed", "siteA_unbuildable") for s in REAL_FAILURE]
        candidate = audit(rows)["passes"][0]["candidates"][-1]
        self.assertTrue(candidate["executor_attempted"])
        self.assertIsNone(candidate["physical_builder_attempted"])
        self.assertFalse(candidate["construction_succeeded"])

    def test_late_executor_dead_is_not_early_r3_sequence(self):
        rows = STALE_THEN_VALID[:4] + [
            slot("air_attempt", "rank=1 src=10 dst=30 finance=60 available=140 built_before=1")
        ] + STALE_THEN_VALID[4:]
        self.assertEqual(audit(rows)["passes"][0]["sequences"], [])

    def test_no_matching_finance_does_not_link_bypass(self):
        rows = [s.replace("capital=60", "capital=61") for s in STALE_THEN_VALID]
        seq = audit(rows)["passes"][0]["sequences"][0]
        self.assertIsNone(seq["following_bypass_linked"])

    def test_missing_finance_is_not_zero_or_match(self):
        rows = [s.replace("capital=60", "").replace("finance=60", "") for s in STALE_THEN_VALID]
        self.assertIsNone(audit(rows)["passes"][0]["sequences"][0]["following_bypass_linked"])

    def test_other_company_never_supplies_discard(self):
        rows = [s.replace("[0]", "[1]") if "PROJECT_DISCARD" in s else s for s in STALE_THEN_VALID]
        self.assertEqual(audit(rows)["passes"][0]["sequences"], [])

    def test_unattributed_logs_do_not_default_to_company_zero(self):
        rows = [s.replace("[script:4] [0] [I] ", "") for s in STALE_THEN_VALID]
        result = audit(rows)
        self.assertEqual(result["passes"], [])
        self.assertGreater(result["coverage"]["unattributed_trace_lines"], 0)

    def test_repeated_pass_id_is_separate_occurrence(self):
        result = audit(STALE_THEN_VALID + STALE_THEN_VALID)
        self.assertEqual(len(result["passes"]), 2)
        self.assertNotEqual(result["passes"][0]["pass_instance"], result["passes"][1]["pass_instance"])

    def test_reload_prevents_cross_session_link(self):
        rows = [START, *FIRST, line("LOAD_RECONCILE restored=1"), DEAD, *NEXT_SUCCESS]
        self.assertEqual(audit(rows)["passes"][0]["sequences"], [])

    def test_duplicate_attempts_are_ambiguous_not_extra_builds(self):
        rows = [START, *FIRST, BYPASS, NEXT_ATTEMPT, NEXT_ATTEMPT, DEAD, *NEXT_SUCCESS, END]
        p = audit(rows)["passes"][0]
        self.assertTrue(p["candidates"][-1]["ambiguous"])
        self.assertEqual(p["sequences"], [])

    def test_catalog_candidate_is_not_examined(self):
        result = audit([slot("project_candidate", "rank=1 src=10 dst=20 affordable=1")])
        self.assertEqual(result["events"], [])
        self.assertIsNone(result["coverage"]["candidate_scan_total"])

    def test_missing_log_is_unreadable_not_zero(self):
        with patch.object(Path, "read_bytes", side_effect=FileNotFoundError("fixture missing")):
            result = read_artifact(Path("missing.log"))
        self.assertEqual(result["status"], "unreadable")
        self.assertEqual(result["streams"], [])

    def test_save_load_streams_never_join(self):
        import json
        data = {"phase_a": {"openttd_output_raw": "\n".join([START, *FIRST])},
                "phase_b": {"openttd_output_raw": "\n".join([DEAD, *NEXT_SUCCESS, END])}}
        with patch.object(Path, "read_bytes", return_value=json.dumps(data).encode()):
            result = read_artifact(Path("save.json"))
        self.assertEqual(len(result["streams"]), 2)
        self.assertFalse(any(p["sequences"] for s in result["streams"] for p in s["passes"]))

    def test_empty_stream_and_absent_stream_differ(self):
        with patch.object(Path, "read_bytes", return_value=b'{"phase_a":{"openttd_output_raw":""}}'):
            empty = read_artifact(Path("empty.json"))
        with patch.object(Path, "read_bytes", return_value=b'{}'):
            absent = read_artifact(Path("absent.json"))
        self.assertEqual(empty["streams"][0]["coverage"]["lines"], 0)
        self.assertEqual(absent["status"], "no_supported_log_stream")

    def test_cli_rejects_unassigned_output(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["missing.log", "--out", str(Path(__file__).resolve())])

    def test_cli_preserves_existing_evidence(self):
        from parallel_bypass_audit import OUTPUT_ROOT
        with patch.object(Path, "exists", return_value=True):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(["missing.log", "--out", str(OUTPUT_ROOT / "already_present.json")])

    def test_c78_build_name_alone_is_not_success(self):
        result = audit([line("C78_BUILD rank=1 mode=air outcome=rejected reason=build_failed")])
        self.assertEqual(result["coverage"]["tag_lines"]["C78_BUILD"], 1)
        self.assertEqual(result["passes"], [])
        self.assertFalse(result["causal_advancement_proven"])

    def test_error_attribution_uses_existing_collector(self):
        result = audit(["[script:4] [1] [E] Your script made an error"])
        self.assertEqual(result["script_errors"]["attributed"][0]["company_id"], 1)


if __name__ == "__main__":
    unittest.main()