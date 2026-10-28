"""Targeted tests for Constat 1: GRAPH/FAST proposal iteration and fallback."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


class Road100GraphFastContracts(unittest.TestCase):
    def test_fast_trace_supports_start_variant_and_next_cursor(self):
        source = read("road100_graph_bridge.nut")
        self.assertIn("function OpexRoad100GBFastTrace(siteA, siteB, sleeveA, sleeveB,", source)
        self.assertIn("startVariantIndex = 0", source)
        self.assertIn("if (startVariantIndex < 0)", source)
        self.assertIn('result.reason = "FAST_SKIPPED"', source)
        self.assertIn("for (local vi = startVariantIndex; vi < variants.len(); vi++)", source)
        self.assertIn("result.variantIndex = vi;", source)
        self.assertIn("result.nextVariantIndex = (vi + 1 < variants.len()) ? (vi + 1) : -1;", source)

    def test_graph_bridge_trace_supports_fast_cursor_and_graph_fallback(self):
        source = read("road100_graph_bridge.nut")
        self.assertIn("function OpexRoad100GraphBridgeTrace(siteA, siteB, mark, limitOps, fastCursor = 0)", source)
        self.assertIn("nextFastCursor = -2", source)
        self.assertIn("local fast = OpexRoad100GBFastTrace(siteA, siteB, sleeveA, sleeveB,", source)
        self.assertIn("out.nextFastCursor = fast.nextVariantIndex;", source)
        self.assertIn("if (out.trace == null && (fastCursor == -1 ||", source)
        self.assertIn("fast.nextVariantIndex < 0", source)
        self.assertIn("out.nextFastCursor = -2;", source)

    def test_builder_road_iterates_proposals_with_shared_budget(self):
        source = read("builder_road.nut")
        self.assertIn("if (shape == -3) {", source)
        self.assertIn("local fastCursor = 0;", source)
        self.assertIn("while (true) {", source)
        self.assertIn("local graph = OpexRoad100GraphBridgeTrace(pair.a, pair.b, mark, limitOps, fastCursor);", source)
        self.assertIn("if (checked != null && checked.ok) {", source)
        self.assertIn("if ((\"nextFastCursor\" in graph) && graph.nextFastCursor >= 0) {", source)
        self.assertIn("fastCursor = graph.nextFastCursor;", source)
        self.assertIn("trials++;", source)
        self.assertIn("} else if ((\"nextFastCursor\" in graph) && graph.nextFastCursor == -1) {", source)
        self.assertIn("fastCursor = -1;", source)
        self.assertIn("if (reason == \"OPCAP\") break;", source)


class MockProposalIterator:
    """Executable behavioral oracle modeling the FAST variant iteration and GRAPH fallback."""

    def __init__(self, fast_variants_ok: list[bool], graph_ok: bool, max_ops: int = 180000):
        # fast_variants_ok: boolean for each of 5 variants: whether it passes physical verification
        self.fast_variants_ok = fast_variants_ok
        self.graph_ok = graph_ok
        self.ops = 0
        self.max_ops = max_ops
        self.limit_ops = max_ops

    def run_fast_trace(self, fast_cursor: int):
        self.ops += 1500
        if self.ops >= self.limit_ops - 50000:
            return {"trace": None, "reason": "FAST_OPCAP", "variantIndex": -1, "nextVariantIndex": -1}
        if fast_cursor < 0:
            return {"trace": None, "reason": "FAST_SKIPPED", "variantIndex": -1, "nextVariantIndex": -1}
        # Find next available variant
        for vi in range(fast_cursor, len(self.fast_variants_ok)):
            self.ops += 200
            next_cursor = (vi + 1) if (vi + 1 < len(self.fast_variants_ok)) else -1
            return {
                "trace": f"fast_trace_{vi}",
                "reason": "FAST_CANDIDATE",
                "variantIndex": vi,
                "nextVariantIndex": next_cursor,
            }
        return {"trace": None, "reason": "FAST_REJECT", "variantIndex": -1, "nextVariantIndex": -1}

    def run_graph_bridge(self, fast_cursor: int):
        fast = self.run_fast_trace(fast_cursor)
        out = {"trace": None, "reason": "PRECHECK", "nextFastCursor": -2}
        if fast["trace"] is not None:
            out["trace"] = fast["trace"]
            out["reason"] = "FAST_CANDIDATE"
            out["variantIndex"] = fast["variantIndex"]
            out["nextFastCursor"] = fast["nextVariantIndex"]

        if out["trace"] is None and (fast_cursor == -1 or (fast_cursor >= 0 and fast["nextVariantIndex"] < 0)):
            # GRAPH fallback
            self.ops += 6000
            out["nextFastCursor"] = -2
            if self.ops >= self.limit_ops - 50000:
                out["trace"] = None
                out["reason"] = "OPCAP"
            else:
                out["trace"] = "graph_trace"
                out["reason"] = "CANDIDATE_NEEDS_VERIFY"
        return out

    def verify_trace(self, trace: str):
        self.ops += 2500
        if trace.startswith("fast_trace_"):
            vi = int(trace.split("_")[-1])
            return {"ok": self.fast_variants_ok[vi]}
        elif trace == "graph_trace":
            return {"ok": self.graph_ok}
        return {"ok": False}

    def simulate_builder(self):
        fast_cursor = 0
        trials = 1
        accepted_trace = None
        reason = None
        while True:
            graph = self.run_graph_bridge(fast_cursor)
            trace = graph["trace"]
            checked = None
            if graph["reason"] == "OPCAP":
                reason = "OPCAP"
                break
            if trace is not None:
                checked = self.verify_trace(trace)
            if checked is not None and checked["ok"]:
                accepted_trace = trace
                break
            if self.ops >= self.limit_ops - 50000:
                reason = "OPCAP"
                break
            if "nextFastCursor" in graph and graph["nextFastCursor"] >= 0:
                fast_cursor = graph["nextFastCursor"]
                trials += 1
            elif "nextFastCursor" in graph and graph["nextFastCursor"] == -1:
                fast_cursor = -1
                trials += 1
            else:
                break
        return {"accepted": accepted_trace, "trials": trials, "reason": reason, "ops": self.ops}


class Road100GraphFastBehavioralOracle(unittest.TestCase):
    def test_first_fast_variant_fails_second_succeeds(self):
        # Variant 0 physically blocked, variant 1 physically clear
        oracle = MockProposalIterator(
            fast_variants_ok=[False, True, False, False, False],
            graph_ok=False,
        )
        res = oracle.simulate_builder()
        self.assertEqual(res["accepted"], "fast_trace_1")
        self.assertEqual(res["trials"], 2)
        self.assertIsNone(res["reason"])

    def test_all_fast_variants_fail_graph_fallback_succeeds(self):
        # All 5 FAST variants fail physically, GRAPH fallback succeeds
        oracle = MockProposalIterator(
            fast_variants_ok=[False, False, False, False, False],
            graph_ok=True,
        )
        res = oracle.simulate_builder()
        self.assertEqual(res["accepted"], "graph_trace")
        # 5 FAST attempts (0..4) then 1 GRAPH attempt = 6 trials
        self.assertEqual(res["trials"], 6)
        self.assertIsNone(res["reason"])

    def test_all_fast_and_graph_fail_exhausts_cleanly(self):
        oracle = MockProposalIterator(
            fast_variants_ok=[False, False, False, False, False],
            graph_ok=False,
        )
        res = oracle.simulate_builder()
        self.assertIsNone(res["accepted"])
        self.assertEqual(res["trials"], 6)
        self.assertIsNone(res["reason"])

    def test_budget_exhaustion_stops_iteration_with_opcap(self):
        oracle = MockProposalIterator(
            fast_variants_ok=[False, True, False, False, False],
            graph_ok=False,
            max_ops=53000,  # limitOps - 50000 = 3000 -> will hit OPCAP after first attempt
        )
        res = oracle.simulate_builder()
        self.assertIsNone(res["accepted"])
        self.assertEqual(res["reason"], "OPCAP")


if __name__ == "__main__":
    unittest.main()
