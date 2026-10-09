"""Fixtures HOST autonomes du schema RAIL_PREASTAR (sans OpenTTD ni Docker)."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse_rail_preastar as audit


START_FIELDS = (
    "mode=primary kind=freight cargo=COAL src=123 dst=456 line=-1 "
    "budget=10000 length=75 na=2 nb=1 amin=1 amax=4 azero=1 awater=0 "
    "bmin=0 bmax=2 bzero=0 bwater=1 aps=10:11:1:0:0,20:21:1:0:1 "
    "bps=30:31:1:0:1 probe_ops=123 rough=10"
)


def event(day, tag, rid, fields=""):
    return f"[2026-10-09 07:00:00] dbg: [script:4] [0] [I] OPEX {day} RAIL_PREASTAR_{tag} rid={rid} {fields}\n"


def start(rid, day="1974-3-2", fields=START_FIELDS):
    return event(day, "START", rid, fields)


def end(rid, stop="OK", iters=200, budget=10000, day="1974-3-3"):
    return event(day, "END", rid, f"stop={stop} iters={iters} budget={budget}")


def build(rid, reason="OK", ok=1, status="built", day="1974-3-4"):
    return event(day, "BUILD", rid, f"reason={reason} ok={ok} status={status}")


def frontier(rid, segment=1, opened=340, viable=3, day="1974-3-2", extra=""):
    return event(day, "FRONTIER", rid, "segment=" + str(segment)
                 + " iters=" + str(segment * 2000) + " used=2000"
                 + " open=" + str(opened) + " sampled=4 viable=" + str(viable)
                 + " backtracks=0 prefix=12" + extra)


def parsed(*lines, filename="reference_seed42_r0.log"):
    return audit.parse_lines(lines, source=filename)


class TestRailPreAStar(unittest.TestCase):
    def test_unique_rid_links_start_end_and_real_build(self):
        result = parsed(start("500:primary:1"), end("500:primary:1"), build("500:primary:1"))
        self.assertEqual(result["warnings"], [])
        attempt = result["attempts"][0]
        self.assertEqual((attempt["arm"], attempt["seed"], attempt["repeat"]), ("reference", 42, 0))
        self.assertEqual((attempt["mode"], attempt["rid"]), ("primary", "500:primary:1"))
        self.assertEqual((attempt["kind"], attempt["cargo"], attempt["src"], attempt["dst"]),
                         ("freight", "COAL", 123, 456))
        self.assertEqual((attempt["line"], attempt["na"], attempt["nb"]), (-1, 2, 1))
        self.assertEqual((attempt["start_date"], attempt["end_date"], attempt["build_date"]),
                         ("1974-03-02", "1974-03-03", "1974-03-04"))
        self.assertEqual(attempt["features"]["aps"], "10:11:1:0:0,20:21:1:0:1")
        self.assertEqual(attempt["features"]["probe_ops"], "123")
        self.assertEqual(attempt["plans"]["A"], [
            {"lead": 10, "exit": 11, "free": 1, "water": 0, "rail": 0},
            {"lead": 20, "exit": 21, "free": 1, "water": 0, "rail": 1},
        ])
        self.assertEqual((attempt["status"], attempt["search_class"], attempt["build_status"]),
                         ("paired", "ok", "built"))

    def test_mode_is_only_in_start_and_ids_can_share_the_same_tick(self):
        stock = START_FIELDS.replace("mode=primary", "mode=stock").replace("kind=freight", "kind=-").replace("cargo=COAL", "cargo=-").replace("src=123 dst=456", "src=-1 dst=-1")
        row = parsed(start("900:primary:3"), start("900:stock:7", fields=stock),
                     end("900:stock:7", "ABND", 10000), end("900:primary:3"))
        self.assertEqual(len(row["attempts"]), 2)
        self.assertEqual({a["mode"] for a in row["attempts"]}, {"primary", "stock"})
        self.assertEqual({a["search_class"] for a in row["attempts"]}, {"ok", "cap_abnd"})
        self.assertEqual(row["warnings"], [])

    def test_build_stock_lifecycle_over_months_and_ready_is_not_delivered(self):
        records = [start("stock:1", "1972-2-1", START_FIELDS.replace("mode=primary", "mode=stock")),
                   end("stock:1", day="1972-2-1"),
                   build("stock:1", "CASH", 0, "ready", "1972-2-1"),
                   build("stock:1", "CASH", 0, "cash", "1972-3-1"),
                   build("stock:1", "OK", 1, "built", "1972-5-20"),
                   start("stock:2", "1972-3-1", START_FIELDS.replace("mode=primary", "mode=stock")),
                   end("stock:2", day="1972-3-2"),
                   build("stock:2", "OK", 1, "ready", "1972-3-2")]
        result = parsed(*records)
        self.assertEqual(result["warnings"], [])
        first, second = result["attempts"]
        self.assertEqual([x["status"] for x in first["build_history"]], ["ready", "cash", "built"])
        self.assertEqual(first["build_ok"], 1)
        self.assertEqual(first["build_status"], "built")
        self.assertEqual(second["build_status"], "ready")
        perf = audit.evaluate_threshold(result["attempts"], "rough>=10")
        self.assertEqual(perf["counts"]["fp_build_ok"], 1)
        self.assertEqual(perf["counts"]["fp_build_unknown"], 1)

    def test_same_exact_log_event_is_deduplicated(self):
        s, e = start("42"), end("42", "ABND", 10000)
        result = parsed(s, s, e, e, build("42", "ABND", 0, "failed"),
                        build("42", "ABND", 0, "failed"))
        self.assertEqual(len(result["attempts"]), 1)
        self.assertEqual(result["duplicates"], 3)
        self.assertEqual(result["attempts"][0]["search_class"], "cap_abnd")
        self.assertEqual(len(result["attempts"][0]["build_history"]), 1)

    def test_same_rid_conflicting_starts_are_not_paired(self):
        result = parsed(start("same"), start("same", fields=START_FIELDS.replace("mode=primary", "mode=upgrade")),
                        end("same", "ABND", 10000))
        self.assertEqual(result["attempts"][0]["status"], "non_pairable")
        self.assertEqual(result["attempts"][0]["search_class"], "unknown")
        self.assertIn("conflicting_start", [x["code"] for x in result["warnings"]])
        self.assertEqual(audit.evaluate_threshold(result["attempts"], "rough>=10")["counts"]["tp"], 0)

    def test_unknown_and_missing_rids_are_censored_not_guessed(self):
        result = parsed(end("no_start", "ABND", 10000), start("no_end"),
                        event("1974-3-5", "END", "-", "stop=ABND iters=10000 budget=10000"))
        self.assertEqual(result["unidentified_events"], 1)
        self.assertEqual({a["status"] for a in result["attempts"]}, {"censored"})
        self.assertEqual({a["search_class"] for a in result["attempts"]}, {"unknown"})
        self.assertIn("missing_start", [w["code"] for w in result["warnings"]])
        self.assertIn("missing_end", [w["code"] for w in result["warnings"]])

    def test_missing_start_field_and_invalid_end_are_not_pairable(self):
        missing = START_FIELDS.replace(" na=2", "")
        result = parsed(start("a", fields=missing), end("a", "ABND", 10000),
                        start("b"), event("1974-3-3", "END", "b", "stop=ABND iters=broken budget=10000"))
        self.assertEqual([a["status"] for a in result["attempts"]], ["non_pairable", "non_pairable"])
        self.assertEqual([a["search_class"] for a in result["attempts"]], ["unknown", "unknown"])
        self.assertTrue(any("missing_fields:na" in w["detail"] for w in result["warnings"]))
        self.assertTrue(any("invalid_integer:iters" in w["detail"] for w in result["warnings"]))

    def test_mismatched_budget_and_reversed_dates_invalidate(self):
        result = parsed(start("a"), end("a", "ABND", 10000, 12000),
                        start("b", "1974-3-4"), end("b", "OK", 100, day="1974-3-2"))
        self.assertEqual({a["status"] for a in result["attempts"]}, {"non_pairable"})
        codes = {w["code"] for w in result["warnings"]}
        self.assertIn("budget_mismatch", codes)
        self.assertIn("end_precedes_start", codes)

    def test_supercede_and_timeout_do_not_masquerade_as_abnd(self):
        result = parsed(start("a"), end("a", "SUPERSEDE", 10000),
                        start("b"), end("b", "TIMEOUT", 10000),
                        start("c", fields=START_FIELDS.replace("length=75", "length=-1")),
                        end("c", "CANCEL", 200))
        self.assertEqual([a["search_class"] for a in result["attempts"]],
                         ["censored", "censored", "censored"])
        scores = audit.evaluate_threshold(result["attempts"], "rough>=10")
        self.assertEqual(scores["counts"]["excluded_other_outcome"], 3)

    def test_conflicting_terminal_build_is_quarantined(self):
        result = parsed(start("x"), end("x"),
                        build("x", "OK", 1, "built"),
                        build("x", "TRKFAIL", 0, "failed", "1974-4-1"))
        self.assertEqual(result["attempts"][0]["status"], "non_pairable")
        self.assertIn("conflicting_build_terminal", [w["code"] for w in result["warnings"]])

    def test_thresholds_avoid_false_rejection_and_mark_missing_fields(self):
        low = START_FIELDS.replace("rough=10", "rough=3")
        missing = START_FIELDS.replace(" rough=10", "")
        events = [start("cap"), end("cap", "ABND", 10000),
                  start("fp"), end("fp", "OK", 15), build("fp", "TRKFAIL", 0, "failed"),
                  start("tn", fields=low), end("tn", "OK", 22),
                  start("missing", fields=missing), end("missing", "ABND", 10000),
                  start("lowbudget", fields=START_FIELDS.replace("budget=10000", "budget=2448")),
                  end("lowbudget", "ABND", 2448, 2448),
                  start("pending")]
        result = parsed(*events)
        scores = audit.evaluate_threshold(result["attempts"], "rough>=10")
        self.assertEqual([scores["counts"][s] for s in ("tp", "fp", "tn", "fn")], [1, 1, 1, 0])
        self.assertEqual(scores["counts"]["excluded_missing_feature"], 1)
        self.assertEqual(scores["counts"]["excluded_other_budget"], 1)
        self.assertEqual(scores["counts"]["excluded_unpaired"], 1)
        self.assertEqual(scores["counts"]["fp_build_failed"], 1)
        self.assertEqual((scores["precision"], scores["false_positive_rate"], scores["recall"]),
                         (0.5, 0.5, 1.0))
        self.assertEqual(scores["false_positives"][0]["rid"], "fp")
        all_caps = audit.evaluate_threshold(result["attempts"], "rough>=10", target="cap_any")
        self.assertEqual(all_caps["counts"]["tp"], 2)

    def test_invalid_tokens_and_thresholds_are_explicit(self):
        result = parsed(start("x", fields=START_FIELDS + " na=3"), end("x"),
                        start("y"), end("y", day="1974-3-3"),
                        event("1974-3-4", "BUILD", "y", "reason=OK ok=? status=ready"))
        self.assertEqual([x["status"] for x in result["attempts"]], ["non_pairable", "non_pairable"])
        self.assertTrue(any(w["code"] == "invalid_event_fields" for w in result["warnings"]))
        with self.assertRaises(ValueError):
            audit.parse_threshold("rough=>10")
        with self.assertRaises(ValueError):
            audit.evaluate_threshold([], "rough>=10", target="unknown")

    def test_malformed_platform_signature_is_quarantined(self):
        bad = START_FIELDS.replace("aps=10:11:1:0:0,20:21:1:0:1", "aps=10:11:1")
        result = parsed(start("x", fields=bad), end("x"))
        self.assertEqual(result["attempts"][0]["status"], "non_pairable")
        self.assertTrue(any("invalid_plan_signatures:aps" in w["detail"] for w in result["warnings"]))

    def test_segment_cutoffs_are_matched_by_rid_and_end_summary(self):
        records = [start("one"), frontier("one"), frontier("one"),
                   frontier("one", segment=2, opened=150, viable=0),
                   end("one", "ABND", 10000)[:-1]
                   + " segments=4 backtracks=2 choices=1 alternatives=0 prefix=65 active_open=84 segment_used=2000\n",
                   start("two"), end("two", "OK", 210), build("two")]
        result = parsed(*records)
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["duplicates"], 1)
        one, two = result["attempts"]
        self.assertEqual(one["segmented"], {"segments": 4, "backtracks": 2,
                                           "choices": 1, "alternatives": 0, "prefix": 65,
                                           "active_open": 84, "segment_used": 2000})
        self.assertEqual([cut["open"] for cut in one["frontier_history"]], [340, 150])
        self.assertEqual([cut["viable"] for cut in one["frontier_history"]], [3, 0])
        self.assertEqual(one["search_class"], "cap_abnd")
        self.assertIsNone(two["segmented"])  # anciens logs conserves
        self.assertEqual(two["frontier_history"], [])

    def test_incomplete_frontier_is_non_pairable_not_a_failed_path(self):
        bad = parsed(start("bad"), frontier("bad", extra=" sampled=5"), end("bad"))
        self.assertEqual(bad["attempts"][0]["status"], "non_pairable")
        self.assertEqual(bad["attempts"][0]["search_class"], "unknown")
        self.assertTrue(any(w["code"] == "invalid_event_fields" for w in bad["warnings"]))
        conflict = parsed(start("x"), frontier("x"), frontier("x", viable=2), end("x"))
        self.assertEqual(conflict["attempts"][0]["status"], "non_pairable")
        self.assertIn("conflicting_frontier_segment", conflict["attempts"][0]["issues"])
        censored = parsed(start("open"), frontier("open"))
        self.assertEqual(censored["attempts"][0]["status"], "censored")
        self.assertEqual(censored["attempts"][0]["search_class"], "unknown")
        self.assertEqual(len(censored["attempts"][0]["frontier_history"]), 1)

    def test_log_filename_isolation_annual_metrics_and_json_serialization(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            (root / "reference_seed42_r0.log").write_text(start("same") + end("same", "ABND", 10000), encoding="utf8")
            (root / "variant_seed42_r0.log").write_text(start("same") + end("same", "OK", 20), encoding="utf8")
            (root / "reference_seed100_r1.log").write_text(start("same", "1975-1-2") + end("same", "OK", 30, day="1975-1-3"), encoding="utf8")
            (root / "unknown.log").write_text(start("ignored") + end("ignored"), encoding="utf8")
            result = audit.analyse(root, thresholds=["rough>=10"])
        self.assertEqual(result["logs_seen"], 4)
        self.assertEqual(result["summary"]["unique_rids"], 3)
        self.assertEqual(result["summary"]["by_arm"]["reference"]["cap_abnd"], 1)
        self.assertEqual(result["summary"]["by_arm"]["variant"]["ok"], 1)
        self.assertEqual(result["summary"]["by_start_year"]["1975"]["ok"], 1)
        self.assertEqual(result["thresholds"][0]["counts"]["fp"], 2)
        self.assertIn("invalid_log_name", [w["code"] for w in result["warnings"]])
        self.assertEqual(len(json.loads(json.dumps(result))["attempts"]), 3)


if __name__ == "__main__":
    unittest.main()
