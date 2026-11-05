"""Regression contracts for the strict ROAD1Y+RAIL INVEST-STALL OFF bridge.

Historical 2026-11-03 fixtures remain independently readable and unchanged.
Only the 2026-11-05 merge's reviewed, SHA-identified intermediates are added.
"""

import hashlib
import unittest
from pathlib import Path

from double_grow_off import off_source as double_grow_off
from invest_stall_merged_off import (
    FROZEN, MERGED, already_merged_off, merged_off_sha, project_merge_stage,
)
from invest_stall_source_off import BEFORE, project_off
from invest_stall_v2_off import off_source as v2_off
from invest_stall_v2_r2_off import off_source as r2_off
from invest_stall_v3_off import off_source as v3_off
from rail_long_v2_off import off_source as rail_long_v2_off
from v257_demand_off import off_source as demand_off


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
STAGES = {"v3": v3_off, "r2": r2_off, "v2": v2_off}


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def before_stall(name):
    return rail_long_v2_off(name, double_grow_off(name, demand_off(name, source(name))))


class InvestStallMergedOffContracts(unittest.TestCase):
    def test_historical_frozen_fixtures_are_immutable(self):
        for stage, path in FROZEN.items():
            with self.subTest(stage=stage):
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    MERGED["historical_fixture_sha256"][stage],
                )
        self.assertEqual(
            BEFORE["builder_rail.nut"],
            "2823c835fd1f54f4fab33e7c5f5f99c8a029c6a0371cbdc2412c6b75d90a5570",
        )

    def test_every_merge_source_off_is_exact_and_idempotent(self):
        self.assertEqual(len(MERGED["files"]), 13)
        for name, row in MERGED["files"].items():
            with self.subTest(name=name):
                projected = project_off(name, source(name))
                self.assertEqual(digest(projected), row["off_sha256"])
                self.assertTrue(already_merged_off(name, projected))
                self.assertEqual(merged_off_sha(name), row["off_sha256"])
                self.assertEqual(project_off(name, projected), projected)

    def test_each_merged_stage_uses_exact_old_hunks_and_locked_sha(self):
        for name, row in MERGED["files"].items():
            with self.subTest(name=name):
                code = before_stall(name)
                self.assertEqual(digest(code), row["pre_sha256"])
                for stage in ("v3", "r2", "v2"):
                    transition = row["stages"].get(stage)
                    if transition is None:
                        continue
                    self.assertEqual(digest(code), transition["on_sha256"])
                    projected = STAGES[stage](name, code)
                    self.assertEqual(digest(projected), transition["off_sha256"])
                    self.assertEqual(project_merge_stage(name, projected, stage), projected)
                    code = projected
                self.assertEqual(digest(code), row["pre_v1_sha256"])

    def test_partial_or_modified_v3_r2_v2_source_fails_closed(self):
        cases = (
            ("builder_rail.nut", "v3"),
            ("candidates.nut", "v3"),
            ("candidates.nut", "r2"),
            ("candidates.nut", "v2"),
            ("po01c_generators.nut", "v2"),
        )
        for name, stage in cases:
            with self.subTest(name=name, stage=stage):
                code = before_stall(name)
                for prior in ("v3", "r2", "v2"):
                    if prior == stage:
                        break
                    if prior in MERGED["files"][name]["stages"]:
                        code = STAGES[prior](name, code)
                import json
                edits = json.loads(FROZEN[stage].read_text(encoding="utf-8"))["files"][name]["edits"]
                target = "".join(edits[0]["after"])
                self.assertEqual(code.count(target), 1)
                tampered = code.replace(target, target + "/* altered */\n", 1)
                self.assertIsNone(project_merge_stage(name, tampered, stage))
                with self.assertRaises(AssertionError):
                    STAGES[stage](name, tampered)
                duplicated = code + target
                self.assertIsNone(project_merge_stage(name, duplicated, stage))
                with self.assertRaises(AssertionError):
                    STAGES[stage](name, duplicated)

    def test_road_first_candidate_projection_has_separate_exact_sha_chain(self):
        from road100_off_projection import off_source as road_off

        name = "candidates.nut"
        variant = MERGED["files"][name]["variants"]["road_off"]
        projected_road = road_off(name, source(name))
        merged_off = project_off(name, projected_road)
        self.assertEqual(digest(merged_off), variant["off_sha256"])
        self.assertEqual(project_off(name, merged_off), merged_off)
        self.assertTrue(already_merged_off(name, merged_off))
        # The ROAD-first input must not masquerade as the unprojected tree.
        self.assertNotEqual(variant["pre_sha256"], MERGED["files"][name]["pre_sha256"])

    def test_merged_platform_sha_is_separate_from_historical_witness(self):
        from invest_stall_diagnostic_off import off_source as diagnostic_off
        from invest_stall_platform_off import FIXTURE, off_source as platform_off
        from rail_long_v3_multi_off import upgrade_reservation_off

        name = "task_rail.nut"
        witness = MERGED["platform"][name]
        self.assertEqual(
            hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
            MERGED["historical_fixture_sha256"]["platform"],
        )
        live = upgrade_reservation_off(name, diagnostic_off(name, source(name)))
        self.assertEqual(digest(live), witness["on_sha256"])
        projected = platform_off(name, live)
        self.assertEqual(digest(projected), witness["off_sha256"])
        self.assertEqual(platform_off(name, projected), projected)
        with self.assertRaises(AssertionError):
            platform_off(name, live.replace("OpexInvestStall", "OpexInvestStalx", 1))


if __name__ == "__main__":
    unittest.main()
