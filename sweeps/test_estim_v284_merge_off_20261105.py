"""Merged ROAD1Y+RAIL ESTIM-1 and V284 OFF regression contracts.

All historical patches and pre-merge SHA remain frozen; new full-file SHA
transitions and exact edits belong exclusively to the 2026-11-05 merge.
"""

# Compare historical contracts after the exact outer FLEET-ARB projection.
from fleet_arb_off import historical_read_text as fleet_read_text

import hashlib
import json
import re
import unittest
from pathlib import Path

from estim_unifie_off_lots import PATCHES, PATCH_TEXT, estim_off
from estim_merged_off import (_fixture as estim_witness, _reviewed_overlay,
                              _sha as sha, NEW_C121)
from road100_off_projection import off_source as road_off
from test_b5_rail_persistence import function_body
from test_rail_search_prio_source_off import off_search_prio_source
from v257_demand_off import off_source as demand_off
from rail_open_legacy import off_source as rail_open_off
from rail_consist_legacy import off_source as consist_off
from v284_merged_off import (FIXTURE as V284_FIXTURE, PO01C_HOOK,
                            V284_HOOK, RAIL_SELECT, project_orchestrator,
                            project_expansion, reviewed_task_rail, reviewed_config)


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return fleet_read_text(AI / name, encoding="utf-8")


def pre_estim(name, source):
    for fn in (demand_off, rail_open_off, consist_off):
        source = fn(name, source)
    if name == "settings.nut":
        if source.count(NEW_C121) != 1:
            raise AssertionError("merged C121 settings insertion missing/duplicated")
        source = source.replace(NEW_C121, "", 1)
    return source


class EstimMergedOffContracts(unittest.TestCase):
    def test_original_estim_patch_and_v161_overlays_stay_byte_exact(self):
        fixture = estim_witness()
        self.assertEqual(hashlib.sha256(PATCH_TEXT.encode("utf-8")).hexdigest(),
                         fixture["historical_patch_sha256"])
        for name, item in fixture["files"].items():
            overlay = _reviewed_overlay(name, PATCHES[name])
            self.assertEqual(
                {str(i): [sha(pair[0]), sha(pair[1])]
                 for i, pair in enumerate(overlay) if i in item["changed_indices"]},
                item["hunk_sha256"],
            )
            self.assertTrue(all(PATCHES[name][i] != overlay[i]
                                for i in item["changed_indices"]))

    def test_all_six_live_and_road_first_variants_are_exact_idempotent(self):
        fixture = estim_witness()["files"]
        for name, witness in fixture.items():
            self.assertGreaterEqual(len(witness["on_off_sha256"]), 2, name)
            for variant in ("live", "road_first"):
                with self.subTest(name=name, variant=variant):
                    initial = read(name)
                    if variant == "road_first":
                        initial = road_off(name, initial)
                    pre = pre_estim(name, initial)
                    self.assertIn(sha(pre), witness["allowed_pre_hunks_sha256"])
                    projected = estim_off(name, initial)
                    self.assertEqual(sha(projected),
                                     witness["on_off_sha256"][sha(pre)])
                    self.assertEqual(estim_off(name, projected), projected)
                    self.assertNotIn("ESTIM_UNIFIE", projected)
                    self.assertNotIn("ESTIM-1", projected)

    def test_mutation_and_duplication_are_rejected_in_known_merged_sources(self):
        changes = (
            ("globals_pre.nut", "ESTIM_K_R_PRIOR_WEIGHT <- 15.0;",
             "ESTIM_K_R_PRIOR_WEIGHT <- 16.0;"),
            ("economy.nut", "if (longModel && !monoLong) calibrationOffered /= 2.0;",
             "if (longModel) calibrationOffered /= 2.0;"),
            ("settings.nut", 'require("air_economics_c121_fullscan.nut");',
             'require("air_economics_c121_broken.nut");'),
            ("settings.nut", 'V233L_CONSTRUCT = AIController.GetSetting("v233l_constructibilite");',
             'V233L_CONSTRUCT = 999;'),
        )
        for name, old, new in changes:
            with self.subTest(name=name, token=old):
                source = read(name)
                self.assertEqual(source.count(old), 1)
                with self.assertRaises(AssertionError):
                    estim_off(name, source.replace(old, new, 1))
        # An entire duplicate C121 dispatch must not slip past the SHA guard.
        with self.assertRaises(AssertionError):
            estim_off("settings.nut", read("settings.nut") + NEW_C121)

    def test_c121_fullscan_is_exactly_subtracted_but_other_settings_survive(self):
        before = read("settings.nut")
        after = estim_off("settings.nut", before)
        self.assertIn("V233L_CONSTRUCT = AIController.GetSetting", after)
        self.assertNotIn("OpexC121ChooseRoutePlane <-", after)
        self.assertNotIn('GetSetting("estim_unifie")', after)
        self.assertIn('GetSetting("v284_rail_growth")', after)


class V284MergedOffContracts(unittest.TestCase):
    def test_orchestrator_and_rail_expansion_are_new_sha_locked_witnesses(self):
        fixture = json.loads(fleet_read_text(V284_FIXTURE, encoding="utf-8"))
        from test_v284_rail_growth import read as v284_source

        source = v284_source("orchestrator.nut")
        self.assertEqual(sha(source), fixture["merged_orchestrator"]["source_sha256"])
        body = function_body(source, "function OpexAI::_runOrchestratorTick()")
        self.assertEqual(body.count(PO01C_HOOK), 1)
        self.assertEqual(body.count(V284_HOOK), 1)
        projected = project_orchestrator(body)
        self.assertEqual(sha(projected),
                         fixture["merged_orchestrator"]["function_off_sha256"])
        self.assertEqual(project_orchestrator(projected), projected)

        rail_live = read("task_rail.nut")
        rail = reviewed_task_rail(
            rail_live, off_search_prio_source("task_rail.nut", rail_live))
        body = function_body(rail, "function OpexAI::_expandRailLines(year)")
        self.assertEqual(body.count(RAIL_SELECT), 1)
        projected = project_expansion(body)
        self.assertEqual(sha(projected),
                         fixture["merged_task_rail"]["expansion_off_sha256"])
        self.assertEqual(project_expansion(projected), projected)

    def test_v284_modified_guard_cannot_pass_as_historical(self):
        from test_v284_rail_growth import read as v284_source
        original = function_body(v284_source("orchestrator.nut"),
                                 "function OpexAI::_runOrchestratorTick()")
        with self.assertRaises(AssertionError):
            project_orchestrator(original.replace(
                "OpexV284Tick(this)", "OpexV284Tick(BROKEN)", 1))
        with self.assertRaises(AssertionError):
            project_orchestrator(original + V284_HOOK)
        live = read("task_rail.nut")
        rail = off_search_prio_source("task_rail.nut", live)
        body = function_body(rail, "function OpexAI::_expandRailLines(year)")
        with self.assertRaises(AssertionError):
            project_expansion(body.replace("OpexV284Select(this, year)",
                                           "OpexV284Select(this, BROKEN)", 1))
        with self.assertRaises(AssertionError):
            reviewed_task_rail(live + "/* BROKEN */", rail)

    def test_v284_config_sources_are_frozen_and_setting_unique(self):
        from test_v284_rail_growth import read as v284_source
        fixture = json.loads(fleet_read_text(V284_FIXTURE, encoding="utf-8"))
        for name in ("settings.nut", "globals_pre.nut"):
            with self.subTest(name=name):
                live = read(name)
                projected = off_search_prio_source(name, live)
                self.assertEqual(reviewed_config(name, live, projected), projected)
                self.assertEqual(v284_source(name), projected)
                with self.assertRaises(AssertionError):
                    reviewed_config(name, live + " ", projected)
        info = v284_source("info.nut")
        witness = fixture["merged_info_after_v233"]
        self.assertEqual(sha(info), witness["sha256"])
        names = re.findall(r'AddSetting\(\{\s*name\s*=\s*"([^"]+)"', info)
        self.assertEqual(len(names), witness["add_setting_count"])
        self.assertEqual(len(set(names)), witness["unique_setting_count"])
        self.assertEqual(names.count("v284_rail_growth"), 1)


if __name__ == "__main__":
    unittest.main()
