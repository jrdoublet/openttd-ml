"""Source-only V190/V233 merged projections; immutable historic fixtures.

The new merge SHA witnesses are separate from the earlier economic/engine
snapshots.  This file never updates their JSON or accepts a partial variant.
"""

# Compare historical contracts after the exact outer FLEET-ARB projection.
from fleet_arb_off import historical_read_text as fleet_read_text

import hashlib
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

import v190_fix_directional_legacy as directional
import v190_fix_legacy as independent
import v233_long_good_legacy as long_good
from road100_off_projection import off_source as road_off
from test_rail_search_prio_20261103 import off_config_bytes


def _source(name):
    return fleet_read_text(ROOT / "ai" / "OpexAI" / name, encoding="utf-8")


def _sha(source):
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


class V190V233MergeProjection(unittest.TestCase):
    def test_v190_fix2_task_rail_repeated_off_is_exact(self):
        source = _source("task_rail.nut")
        projected = directional.off_source("task_rail.nut", source)
        self.assertEqual(_sha(projected), directional._MERGED_TASK_RAIL_ALREADY_OFF_SHA256)
        self.assertEqual(projected, directional.off_source("task_rail.nut", projected))
        self.assertNotIn("v190Directional", projected)

    def test_v190_fix1_complete_off_is_idempotent_on_reviewed_merge(self):
        for name in ("builder_rail.nut", "task_rail.nut"):
            with self.subTest(name=name):
                projected = independent.off_source(name, _source(name))
                self.assertEqual(_sha(projected), independent._MERGED_V190_ALREADY_OFF_SHA256[name])
                self.assertEqual(independent.off_source(name, projected), projected)

    def test_v233_frozen_json_is_unmodified(self):
        data = json.loads(fleet_read_text(ROOT / "sweeps" / "fixtures" / "v233_long_good_off.json", encoding="utf-8"))
        self.assertEqual(data, long_good.FIXTURE)

    def test_v233_reconciled_builder_and_info_have_reviewed_output_sha(self):
        for name in ("builder_rail.nut", "info.nut"):
            live = _source(name)
            variants = {"live": live, "road-off": road_off(name, live)}
            if name == "info.nut":
                config = off_config_bytes(name, live.encode("utf-8")).decode("utf-8")
                variants["config-off"] = config
                variants["config-road-off"] = road_off(name, config)
            for label, source in variants.items():
                with self.subTest(name=name, stage=label):
                    actual = long_good.off_source(name, source)
                    if name == "info.nut":
                        self.assertNotIn('name = "v233_long_good"', actual)
                        self.assertNotIn('name = "v233l_constructibilite"', actual)
                        self.assertIn('name = "v284_rail_growth"', actual)
                    else:
                        self.assertNotIn("if (OpexV233LIs(candidate) && plan.doubleTrack != 1)", actual)
                        self.assertNotIn("if (OpexV233LIs(candidate) && !okD", actual)
                        self.assertNotIn("if (OpexV233LIs(candidate) && !OpexV233LRecheck", actual)
                        self.assertIn("OpexRailRepairJoinSite", actual)

    def test_v233_partial_merge_source_is_not_silently_accepted(self):
        substitutions = {
            "builder_rail.nut": (
                "OpexV233LMonoAllowed(candidate, plan) ? 1 : 2",
                "OpexV233LMonoAllowed(candidate, plan) ? 2 : 2",
            ),
            "info.nut": (
                'name = "v233l_constructibilite"',
                'name = "v233l_constructibilite_bad"',
            ),
        }
        for name, (before, after) in substitutions.items():
            with self.subTest(name=name):
                source = _source(name)
                self.assertEqual(source.count(before), 1)
                changed = source.replace(before, after, 1)
                self.assertNotEqual(changed, source)
                with self.assertRaises(AssertionError):
                    long_good.off_source(name, changed)


if __name__ == "__main__":
    unittest.main()
