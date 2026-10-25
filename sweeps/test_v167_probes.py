#!/usr/bin/env python3
"""Tests pour V167 — un seul reglage entier `probes` pilote panneaux, journal et sondes.

Contrats statiques :
1. `probes` est un entier signe sur bits 0..30, defaut publication 0 (bancs : 2).
2. Les anciennes sondes booleennes ont disparu des AddSetting / GetSetting ; chacune
   utilise un bit dedie et, si necessaire, son ancien groupe pour compatibilite.
3. Le bit 1 active toutes les sondes ; les bits dedies ne forcent jamais le journal.
4. Lanceur : `--probes N` injecte le reglage dans les deux bras, garde les panneaux et active
   `--script-debug` des qu'un bit hors panneaux est demande.
"""
from __future__ import annotations

import re
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
sys.path.insert(0, str(ROOT / "sweeps"))

try:
    import openttdlab  # noqa: F401
except ImportError:
    fake_lab = types.ModuleType("openttdlab")
    fake_lab.bananas_ai = mock.MagicMock()
    fake_lab.bananas_ai_library = mock.MagicMock()
    fake_lab.local_folder = mock.MagicMock()
    fake_lab.run_experiments = mock.MagicMock()
    sys.modules["openttdlab"] = fake_lab

from bench_v2 import parse_opex_variant  # noqa: E402
from campaign_freeze import parse_ai_setting_specs  # noqa: E402
from run_c66_reference import inject_probes, probes_need_script_debug  # noqa: E402

GROUP_BITS = {8, 16, 32, 64, 128}
ALL_BITS = 2147483647
LOG_BITS = 508
DEDICATED_BITS = {
    "probe_cost": (512, 64),
    "probe_scheduler": (1024, 8),
    "probe_loop_ops": (2048, 8),
    "probe_span_trace": (4096, 8),
    "probe_select_reject": (8192, 16),
    "probe_candidates_rail": (16384, 8),
    "probe_catalogue": (32768, 8),
    "probe_vehicle_lost": (65536, 128),
    "probe_portfolio": (131072, 128),
    "c122_air_regime_shadow": (262144, 16),
    "c122_air_threat_probe": (524288, 16),
    "probe_events": (1048576, 128),
    "rail_failure_audit": (2097152, 32),
    "c67_water_exposure_probe": (4194304, 64),
    "air_flotte1_shadow": (8388608, 0),
    # Bits 24/25 reserves : sondes runtime WIP AIR-ROI/AIR-LOAD non adoptees.
    "v309_idle_probe": (67108864, 0),
    "v308_carto_probe": (134217728, 0),
    "v307_abnd_autopsy": (268435456, 0),
    "v216_probe": (536870912, 0),
    "v211_rivals_log": (1073741824, 0),
}
# reglages nommes « shadow »/« diagnostic » mais qui changent des decisions : jamais groupes
DECISION_CHANGING = (
)
REMOVED_DECISION_SETTINGS = (
    "air_site_quote_keep_legacy_margin",
    "air_site_cost_quote",
    "air_site_cost_margin_pct",
    "air_batch_town_reserve",
    "air_bfail_dispose_orphan",
)


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError("unterminated " + name)


def _effective(probes: int):
    """Modele Python de OpexLoadSettings (les constantes sont verifiees dans le source)."""
    if probes & 1:
        probes = ALL_BITS
    signs = bool(probes & 2)
    log = bool(probes & LOG_BITS)
    groups = {bit for bit in GROUP_BITS if probes & bit}
    return signs, log, groups


class Declaration(unittest.TestCase):
    def test_probes_setting(self):
        spec = parse_ai_setting_specs(AI / "info.nut")
        self.assertEqual(spec["probes"]["default"], 0)
        self.assertFalse(spec["probes"]["boolean"])
        self.assertEqual((spec["probes"]["min_value"], spec["probes"]["max_value"]), (0, ALL_BITS))
        block = _read("info.nut").split('name = "probes"', 1)[1].split("});", 1)[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r" = 0\b")
        self.assertNotIn("debug_signs", spec)
        self.assertNotIn("decision_log", spec)
        self.assertIn("OPEX_PROBE_MASK <- 2;", _read("globals_pre.nut"))


class Groups(unittest.TestCase):
    def test_dedicated_bits_are_unique(self):
        bits = [bit for bit, _ in DEDICATED_BITS.values()]
        self.assertEqual(len(bits), 20)
        self.assertEqual(bits, [1 << i for i in (*range(9, 24), *range(26, 31))])

    def test_direct_bits_and_retired_settings(self):
        info = _read("info.nut")
        settings = _read("settings.nut")
        specs = parse_ai_setting_specs(AI / "info.nut")
        sources = {p.name: p.read_text(encoding="utf-8") for p in AI.rglob("*.nut")}
        for name, (bit, group) in DEDICATED_BITS.items():
            with self.subTest(name=name):
                self.assertNotIn(name, specs)
                self.assertNotIn(f'name = "{name}"', info)
                for file_name, source in sources.items():
                    self.assertNotIn(f'GetSetting("{name}")', source, (file_name, name))
                expected = f'OpexProbeEnabled({bit}' + (f', {group}' if group else '') + ')'
                self.assertIn(expected, settings, name)
        self.assertNotIn('OpexProbeSetting(', settings)
        self.assertNotIn('OPEX_PROBE_GROUPS', settings)

        for bit, variable, flags in (
            (8, "probeCandRoad", ("C41_ROAD_CANDIDATE_PROFILE", "C41_ROAD_FREIGHT_PROFILE",
                                     "C41_ROAD_FREIGHT_TOWN_PROFILE")),
            (8, "PROBE_EVENT_BACKLOG", ()),
            (32, "probeRailSearch", ("C41_RAIL_DOMINATION_PROBE", "C41_PROJECTS_FALLTHROUGH_PROBE",
                                      "C39_PROJECTS_CADENCE_PROBE")),
        ):
            with self.subTest(variable=variable):
                self.assertIn(f'{variable} = (OPEX_PROBE_MASK & {bit}) != 0;', settings)
                for flag in flags:
                    self.assertIn(f'{flag} = {variable};', settings)

        self.assertEqual(_effective(10), (True, True, {8}))
        self.assertEqual(_effective(34), (True, True, {32}))
        self.assertEqual(_effective(42), (True, True, {8, 32}))

    def test_individual_bits_do_not_activate_neighbouring_channels_or_log(self):
        settings = _read("settings.nut")
        self.assertIn("return (OPEX_PROBE_MASK & (bit | legacyGroup)) != 0;", settings)
        for name, (bit, group) in DEDICATED_BITS.items():
            with self.subTest(name=name):
                self.assertEqual(_effective(2 | bit), (True, False, set()))
                enabled = {other for other, (other_bit, other_group) in DEDICATED_BITS.items()
                           if (2 | bit) & (other_bit | other_group)}
                self.assertEqual(enabled, {name})

    def test_retired_decision_settings_remain_absent(self):
        specs = parse_ai_setting_specs(AI / "info.nut")
        for name in DECISION_CHANGING:
            self.assertIn(name, specs, name)
        for name in REMOVED_DECISION_SETTINGS:
            self.assertNotIn(name, specs, name)


class LatentProbeCrashes(unittest.TestCase):
    def test_freight_economics_mark_needs_profile(self):
        # smoke probes=511 du 13/10 : la preparation rail C121 appelle OpexBuildCandidates sans
        # profil ; la marque fret etait posee quand meme, puis profile.freightEconomicsOps plantait
        body = _function_body(_read("candidates.nut"), "OpexMakeCandidate")
        self.assertIn('local freightEconomicsMark = (profile != null && kind == "freight" && (', body)


class Loading(unittest.TestCase):
    def test_mask_read_before_first_probe(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        read = body.index('local probes = AIController.GetSetting("probes");')
        expand = body.index("if ((probes & 1) != 0) probes = 2147483647;")
        store = body.index("OPEX_PROBE_MASK = probes;")
        self.assertLess(read, expand)
        self.assertLess(expand, store)
        self.assertLess(store, body.index("OpexProbeEnabled("))
        for probe in ("AIR_FLOTTE1_SHADOW",):
            self.assertLess(store, body.index(probe + " = OpexProbeEnabled("), probe)
        self.assertIn("if (probes < 0) probes = 2;", body[read:expand])
        self.assertEqual(body.count("OPEX_PROBE_MASK ="), 1)

    def test_signs_and_log(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertIn('DEBUG_SIGNS = (probes & 2) != 0;', body)
        self.assertIn('DECISION_LOG = (probes & %d) != 0;' % LOG_BITS, body)
        self.assertEqual(body.count("DEBUG_SIGNS ="), 1)
        self.assertEqual(body.count("DECISION_LOG ="), 1)

    def test_semantics(self):
        self.assertEqual(_effective(2), (True, False, set()))            # defaut historique
        self.assertEqual(_effective(0), (False, False, set()))           # tout coupe
        self.assertEqual(_effective(1), (True, True, GROUP_BITS))  # toutes sondes
        self.assertEqual(_effective(6), (True, True, set()))             # panneaux + journal
        self.assertEqual(_effective(18), (True, True, {16}))             # AIR implique le journal
        self.assertEqual(_effective(258), (True, True, set()))  # journal seul


class Launcher(unittest.TestCase):
    def test_inject(self):
        self.assertEqual(inject_probes(None, 6), "OpexAI[probes=6]")
        self.assertEqual(inject_probes(None, 2147483647), "OpexAI[probes=2147483647]")
        self.assertEqual(inject_probes("OpexAI[mode_rail=0]", 18), "OpexAI[mode_rail=0,probes=18]")
        self.assertEqual(inject_probes("OpexAI[probes=2]", 6), "OpexAI[probes=2]")
        with self.assertRaises(ValueError):
            inject_probes("AAAHogEx", 6)
        for bad in (0, 4, 512, 2147483648, -1):
            with self.assertRaises(ValueError):
                inject_probes(None, bad)

    def test_script_debug(self):
        self.assertFalse(probes_need_script_debug(2))
        for probes in (1, 3, 6, 18, 258, 514, 2147483646):
            self.assertTrue(probes_need_script_debug(probes), probes)

    def test_bench_validation(self):
        self.assertEqual(parse_opex_variant("OpexAI[probes=6]"), (("probes", 6),))
        self.assertEqual(parse_opex_variant("OpexAI[probes=1]"), (("probes", 1),))
        self.assertEqual(parse_opex_variant("OpexAI[probes=1073741826]"), (("probes", 1073741826),))
        for bad in ("OpexAI[probes=0]", "OpexAI[probes=4]", "OpexAI[probes=512]", "OpexAI[probes=2147483648]"):
            with self.assertRaises(ValueError):
                parse_opex_variant(bad)

    def test_launcher_wiring(self):
        source = (ROOT / "sweeps" / "run_c66_reference.py").read_text(encoding="utf-8")
        main = source[source.index("def main("):]
        inject = main.index("args.reference = inject_probes(args.reference, args.probes, allow_panel_free=args.allow_panel_free)")
        self.assertIn("args.variant = inject_probes(args.variant, args.probes, allow_panel_free=args.allow_panel_free)", main)
        self.assertIn('parser.add_argument("--allow-panel-free"', source)
        self.assertIn('args.allow_panel_free and args.probes != 0', main)
        self.assertIn('"C66_ALLOW_PANEL_FREE=1"', main)
        self.assertLess(main.index("args.script_debug = True"), main.index("if args.script_debug:"))
        # injection avant toute construction de la commande du banc
        self.assertLess(inject, main.index('benchmark += ["--reference", args.reference]'))


if __name__ == "__main__":
    unittest.main()
