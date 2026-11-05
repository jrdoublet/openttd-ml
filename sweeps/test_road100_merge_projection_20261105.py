"""ROAD1Y-B2 frozen master and strictly identified master+RAIL projections.

No fixtures are regenerated.  The merge adapter may skip only seven reviewed
RAIL-only context hunks; all actual ROAD100 deletions use frozen exact hunks.
"""

import difflib
import hashlib
import json
import subprocess
import sys
import unittest

from sweeps import road100_off_projection as road


_LEGACY_LAYERS = (
    ("road100_bus_districts_hunks.json", "ROAD1Y-B2"),
    ("road100_v36_optin_hunks.json", "ROAD100-36"),
    ("road100_v35_optin_hunks.json", "ROAD100-35"),
    ("road100_v34_optin_hunks.json", "ROAD100-34"),
    ("road100_v33_optin_hunks.json", "ROAD100-33"),
    ("road100_v31b_optin_hunks.json", "ROAD100-31b"),
    ("road100_v32_optin_hunks.json", "ROAD100-32"),
    ("road100_v31_optin_hunks.json", "ROAD100-31"),
    ("road100_v30a_optin_hunks.json", "ROAD100-30a"),
    ("road100_site_first_hunks.json", "ROAD100-7"),
    ("road100_optin_hunks.json", "ROAD100"),
)

# First parent of the published ROAD1Y+RAIL merge (6f57003f).  This immutable
# tree, rather than the advancing origin/master ref, is the old ROAD1Y witness.
_PRE_RAIL_MERGE_MASTER = "44d9313eab12e08685ac1bf0cc6254fe0257ba4d"


def _historical_off(name, source, *, merged_rail=False):
    """Project frozen layers independently, preserving reviewed RAIL-only hunks.

    Before the merge all B2 fixture hunks were removed; the merged master
    contains seven unrelated RAIL insertions inside the B2 context.  The
    alternate path is admitted ONLY at the exact frozen before/after hashes.
    """
    for filename, label in _LEGACY_LAYERS:
        data = json.loads((road.FIXTURE.parent / filename).read_text(encoding="utf-8"))
        edits = data.get(name)
        if merged_rail and filename == "road100_bus_districts_hunks.json":
            before_sha, after_sha, rail_only = road.ROAD1Y_B2_RAIL_MERGE[name]
            if hashlib.sha256(source.encode("utf-8")).hexdigest() != before_sha:
                raise AssertionError(f"{name}: unreviewed merged input")
            edits = [edit for i, edit in enumerate(edits) if i not in rail_only]
            source = road._subtract_exact(name, source, edits, label + "-reviewed-merge")
            if hashlib.sha256(source.encode("utf-8")).hexdigest() != after_sha:
                raise AssertionError(f"{name}: reviewed merged B2 output changed")
        else:
            source = road._subtract_exact(name, source, edits, label)
    return source


class Road100MergedProjection(unittest.TestCase):
    def test_origin_master_keeps_all_historical_projector_bytes(self):
        for name in road.FILES:
            with self.subTest(name=name):
                source = subprocess.check_output(
                    ["git", "show", "origin/master:ai/OpexAI/" + name], cwd=road.ROOT,
                ).decode("utf-8")
                reviewed = road.ROAD1Y_B2_RAIL_MERGE.get(name)
                digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
                # origin/master now IS the approved merged source.  Compare
                # the frozen projection in either era; never assert that the
                # moving branch must differ from the reviewed merge.
                merged_rail = reviewed is not None and digest == reviewed[0]
                projected = road.off_source(name, source)
                self.assertEqual(projected, _historical_off(name, source, merged_rail=merged_rail))
                self.assertEqual(road.off_source(name, projected), projected)

    def test_reviewed_rail_only_hunks_do_not_contain_road_changes(self):
        districts = json.loads(
            (road.FIXTURE.parent / "road100_bus_districts_hunks.json")
            .read_text(encoding="utf-8")
        )
        for name, (_, _, indices) in road.ROAD1Y_B2_RAIL_MERGE.items():
            for index in indices:
                with self.subTest(name=name, index=index):
                    entry = districts[name][index]
                    operations = difflib.SequenceMatcher(
                        None, entry["before"].splitlines(keepends=True),
                        entry["after"].splitlines(keepends=True), autojunk=False,
                    ).get_opcodes()
                    changes = [tag for tag, *_ in operations if tag != "equal"]
                    self.assertTrue(changes)
                    self.assertEqual(set(changes), {"insert"})

    def test_reviewed_merge_projects_all_road_sources_idempotently(self):
        for name in road.FILES:
            with self.subTest(name=name):
                source = (road.ROOT / "ai" / "OpexAI" / name).read_text(encoding="utf-8")
                if name in road.ROAD1Y_B2_RAIL_MERGE:
                    expected_sha = road.ROAD1Y_B2_RAIL_MERGE[name][0]
                    self.assertEqual(hashlib.sha256(source.encode("utf-8")).hexdigest(), expected_sha)
                projected = road.off_source(name, source)
                self.assertNotEqual(projected, source)
                self.assertEqual(road.off_source(name, projected), projected)
        retained = {
            "candidates.nut": ("RAIL_SIBLING", "OpexRailSiblingParent", "RAIL_OPEN"),
            "globals_pre.nut": ("RAIL_SIBLING <- 0;", "RAIL_OPEN"),
            "info.nut": ('name = "rail_sibling"',),
            "settings.nut": ('GetSetting("rail_sibling")',),
        }
        for name, markers in retained.items():
            with self.subTest(retained=name):
                source = (road.ROOT / "ai" / "OpexAI" / name).read_text(encoding="utf-8")
                projected = road.off_source(name, source)
                for marker in markers:
                    self.assertIn(marker, projected)

    def test_reviewed_intermediate_off_sources_are_exact_and_idempotent(self):
        # Several older checks remove RAIL-LONG/SEARCH-PRIO/DEPOT first.  These
        # are pinned source bytes, never a generic substring-based exception.
        sweeps_path = str(road.ROOT / "sweeps")
        if sweeps_path not in sys.path:
            sys.path.insert(0, sweeps_path)
        from n75_mc_legacy import (rail_long_config_off_bytes,
                                   rail_search_prio_config_off_bytes)
        from rail_depot_signal_legacy import strip_if_present

        for name, reviewed in road.ROAD1Y_B2_RAIL_MERGE.items():
            raw = (road.ROOT / "ai" / "OpexAI" / name).read_bytes()
            stages = []
            raw = rail_long_config_off_bytes(name, raw)
            stages.append(("rail_long_off", raw))
            raw = rail_search_prio_config_off_bytes(name, raw)
            stages.append(("rail_search_prio_off", raw))
            raw = strip_if_present(name, raw.decode("utf-8")).encode("utf-8")
            stages.append(("rail_depot_signal_off", raw))
            accepted = {p[0]: p[1] for p in road.ROAD1Y_B2_RAIL_MERGE_STAGES[name]}
            accepted[reviewed[0]] = reviewed[1]
            for stage, content in stages:
                with self.subTest(name=name, stage=stage):
                    source = content.decode("utf-8")
                    digest = hashlib.sha256(content).hexdigest()
                    # The last candidates stage matches the PRE-MERGE master,
                    # not the moving origin/master (which now includes RAIL).
                    # Keep an exact byte comparison against that immutable
                    # Git object before exercising the historical projector.
                    if name == "candidates.nut" and stage == "rail_depot_signal_off":
                        legacy = subprocess.check_output(
                            ["git", "show", _PRE_RAIL_MERGE_MASTER + ":ai/OpexAI/" + name],
                            cwd=road.ROOT,
                        ).decode("utf-8")
                        self.assertEqual(source, legacy)
                        self.assertEqual(road.off_source(name, source), _historical_off(name, source))
                        self.assertEqual(road.off_source(name, road.off_source(name, source)),
                                         road.off_source(name, source))
                        continue
                    self.assertIn(digest, accepted)
                    districts = json.loads(
                        (road.FIXTURE.parent / "road100_bus_districts_hunks.json")
                        .read_text(encoding="utf-8")
                    )[name]
                    b2 = road._subtract_road1y_b2(name, source, districts)
                    self.assertEqual(hashlib.sha256(b2.encode("utf-8")).hexdigest(), accepted[digest])
                    projected = road.off_source(name, source)
                    self.assertEqual(road.off_source(name, projected), projected)
                    if name == "info.nut" and stage == "rail_depot_signal_off":
                        marker = 'name = "rail_sibling"'
                        self.assertIn(marker, source)
                        with self.assertRaises(AssertionError):
                            road.off_source(name, source.replace(marker, marker + "_tampered", 1))

    def test_merge_sha_guard_rejects_unreviewed_rail_changes(self):
        mutations = {
            "candidates.nut": ("RAIL_SIBLING != 0", "RAIL_SIBLING != 1"),
            "globals_pre.nut": ("RAIL_SIBLING <- 0;", "RAIL_SIBLING <- 1;"),
            "info.nut": ('name = "rail_sibling"', 'name = "rail_sibling_edited"'),
            "settings.nut": ('GetSetting("rail_sibling")', 'GetSetting("rail_sibling_edited")'),
        }
        for name, (before, after) in mutations.items():
            with self.subTest(name=name):
                source = (road.ROOT / "ai" / "OpexAI" / name).read_text(encoding="utf-8")
                self.assertIn(before, source)
                with self.assertRaises(AssertionError):
                    road.off_source(name, source.replace(before, after, 1))

    def test_partial_or_modified_road_hunk_fails_closed(self):
        name = "candidates.nut"
        source = (road.ROOT / "ai" / "OpexAI" / name).read_text(encoding="utf-8")
        data = json.loads(
            (road.FIXTURE.parent / "road100_bus_districts_hunks.json")
            .read_text(encoding="utf-8")
        )[name]
        self.assertEqual(source.count(data[0]["after"]), 1)
        partial = source.replace(data[0]["after"], data[0]["before"], 1)
        self.assertNotEqual(partial, source)
        with self.assertRaises(AssertionError):
            road.off_source(name, partial)


if __name__ == "__main__":
    unittest.main()
