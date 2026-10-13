#!/usr/bin/env python3
"""Tests pour V167 — un seul reglage entier `probes` pilote panneaux, journal et sondes.

Contrats statiques :
1. `probes` declare (entier 0..511, defaut 2 = panneaux seuls, le comportement historique) ;
   `debug_signs` garde son defaut 1 et ne sert plus que de veto.
2. Table `OPEX_PROBE_GROUPS` : chaque sonde groupee existe dans info.nut avec un defaut nul, est
   lue une seule fois et uniquement par `OpexProbeSetting` ; tout appel a `OpexProbeSetting` vise
   une cle de la table (sinon erreur Squirrel a l'execution). Les reglages qui changent des
   decisions n'y entrent pas.
3. Le masque est lu et etendu (bit 1 = tout sauf 256) avant la premiere sonde ; tout groupe
   active le journal.
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

GROUP_BITS = {8, 16, 32, 64, 128, 256}
ALL_EXCEPT_CHECKS = 254   # 2 | 4 | 8 | 16 | 32 | 64 | 128
LOG_BITS = 508            # 4 | 8 | 16 | 32 | 64 | 128 | 256
# reglages nommes « shadow »/« diagnostic » mais qui changent des decisions : jamais groupes
DECISION_CHANGING = (
    "c111_air_c100_decision_shadow",
    "c113_air_c100_full_decision_shadow",
    "air_bfail_dispose_orphan",
    "c114_air_c100_full_replay",
    "rail_cached_proximity_gate",
    "air_site_quote_keep_legacy_margin",
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


def _groups() -> dict[str, int]:
    settings = _read("settings.nut")
    table = settings.split("OPEX_PROBE_GROUPS <- {", 1)[1].split("};", 1)[0]
    pairs = re.findall(r"^\s+(\w+) = (\d+),$", table, re.M)
    return {name: int(bit) for name, bit in pairs}


def _effective(probes: int, debug_signs: int = 1, decision_log: int = 0):
    """Modele Python de OpexLoadSettings (les constantes sont verifiees dans le source)."""
    if probes & 1:
        probes |= ALL_EXCEPT_CHECKS
    signs = bool(probes & 2) and debug_signs != 0
    log = bool(probes & LOG_BITS) or decision_log != 0
    groups = {bit for bit in GROUP_BITS if probes & bit}
    return signs, log, groups


class Declaration(unittest.TestCase):
    def test_probes_setting(self):
        spec = parse_ai_setting_specs(AI / "info.nut")
        self.assertEqual(spec["probes"]["default"], 2)
        self.assertFalse(spec["probes"]["boolean"])
        self.assertEqual((spec["probes"]["min_value"], spec["probes"]["max_value"]), (0, 511))
        block = _read("info.nut").split('name = "probes"', 1)[1].split("});", 1)[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r" = 2\b")
        # le harnais exige toujours debug_signs = 1 par defaut
        self.assertEqual(spec["debug_signs"]["default"], 1)
        self.assertIn("OPEX_PROBE_MASK <- 2;", _read("globals_pre.nut"))


class Groups(unittest.TestCase):
    def test_table_shape(self):
        groups = _groups()
        self.assertGreaterEqual(len(groups), 50)
        self.assertLessEqual(set(groups.values()), GROUP_BITS)
        self.assertEqual(set(groups.values()), GROUP_BITS, "chaque groupe a au moins une sonde")

    def test_grouped_probes_default_off_and_read_once_by_helper(self):
        specs = parse_ai_setting_specs(AI / "info.nut")
        settings = _read("settings.nut")
        sources = {path.name: path.read_text(encoding="utf-8") for path in AI.glob("*.nut")}
        for name in _groups():
            self.assertIn(name, specs, name)
            self.assertEqual(specs[name]["default"], 0, name)
            self.assertEqual(settings.count('OpexProbeSetting("' + name + '")'), 1, name)
            for file_name, src in sources.items():
                self.assertNotIn('AIController.GetSetting("' + name + '")', src, (file_name, name))

    def test_every_helper_call_has_a_group(self):
        groups = _groups()
        for path in AI.glob("*.nut"):
            for name in re.findall(r'OpexProbeSetting\("(\w+)"\)', path.read_text(encoding="utf-8")):
                self.assertIn(name, groups, (path.name, name))

    def test_decision_changing_settings_not_grouped(self):
        groups = _groups()
        specs = parse_ai_setting_specs(AI / "info.nut")
        for name in DECISION_CHANGING:
            self.assertIn(name, specs, name)
            self.assertNotIn(name, groups, name)
        # les experiences qui accompagnent une verification ne sont pas groupees
        for name in ("exp_opcode_exact", "v90_fast_pathfinder", "v129_rail_astar_exact_opt",
                     "v94_air_site_list", "v141_catalog_incremental", "c122_air_threat_retry"):
            self.assertNotIn(name, groups, name)

    def test_helper(self):
        helper = _function_body(_read("settings.nut"), "OpexProbeSetting")
        self.assertIn("local value = AIController.GetSetting(name);", helper)
        self.assertIn("if (value <= 0 && (OPEX_PROBE_MASK & OPEX_PROBE_GROUPS[name]) != 0) return 1;",
                      helper)
        self.assertIn("return value;", helper)


class Loading(unittest.TestCase):
    def test_mask_read_before_first_probe(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        read = body.index('local probes = AIController.GetSetting("probes");')
        expand = body.index("if ((probes & 1) != 0) probes = probes | %d;" % ALL_EXCEPT_CHECKS)
        store = body.index("OPEX_PROBE_MASK = probes;")
        self.assertLess(read, expand)
        self.assertLess(expand, store)
        self.assertLess(store, body.index("OpexProbeSetting("))
        self.assertIn("if (probes < 0) probes = 2;", body[read:expand])
        self.assertEqual(body.count("OPEX_PROBE_MASK ="), 1)

    def test_signs_and_log(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertIn('DEBUG_SIGNS = (probes & 2) != 0\n      && AIController.GetSetting("debug_signs") != 0;',
                      body)
        self.assertIn('DECISION_LOG = (probes & %d) != 0\n      || AIController.GetSetting("decision_log") != 0;'
                      % LOG_BITS, body)
        self.assertEqual(body.count("DEBUG_SIGNS ="), 1)
        self.assertEqual(body.count("DECISION_LOG ="), 1)

    def test_semantics(self):
        self.assertEqual(_effective(2), (True, False, set()))            # defaut historique
        self.assertEqual(_effective(0), (False, False, set()))           # tout coupe
        self.assertEqual(_effective(1), (True, True, GROUP_BITS - {256}))  # tout sauf verifications
        self.assertEqual(_effective(2, debug_signs=0), (False, False, set()))  # veto humain
        self.assertEqual(_effective(6), (True, True, set()))             # panneaux + journal
        self.assertEqual(_effective(18), (True, True, {16}))             # AIR implique le journal
        self.assertEqual(_effective(258), (True, True, {256}))
        self.assertEqual(_effective(2, decision_log=1), (True, True, set()))  # ancien reglage lu


class Launcher(unittest.TestCase):
    def test_inject(self):
        self.assertEqual(inject_probes(None, 6), "OpexAI[probes=6]")
        self.assertEqual(inject_probes("OpexAI[mode_rail=0]", 18), "OpexAI[mode_rail=0,probes=18]")
        with self.assertRaises(ValueError):
            inject_probes("OpexAI[probes=2]", 6)
        with self.assertRaises(ValueError):
            inject_probes("AAAHogEx", 6)
        for bad in (0, 4, 512, -1):
            with self.assertRaises(ValueError):
                inject_probes(None, bad)

    def test_script_debug(self):
        self.assertFalse(probes_need_script_debug(2))
        for probes in (1, 3, 6, 18, 258):
            self.assertTrue(probes_need_script_debug(probes), probes)

    def test_bench_validation(self):
        self.assertEqual(parse_opex_variant("OpexAI[probes=6]"), (("probes", 6),))
        self.assertEqual(parse_opex_variant("OpexAI[probes=1]"), (("probes", 1),))
        for bad in ("OpexAI[probes=0]", "OpexAI[probes=4]", "OpexAI[probes=512]"):
            with self.assertRaises(ValueError):
                parse_opex_variant(bad)

    def test_launcher_wiring(self):
        source = (ROOT / "sweeps" / "run_c66_reference.py").read_text(encoding="utf-8")
        main = source[source.index("def main("):]
        inject = main.index("args.reference = inject_probes(args.reference, args.probes)")
        self.assertIn("args.variant = inject_probes(args.variant, args.probes)", main)
        self.assertLess(main.index("args.script_debug = True"), main.index("if args.script_debug:"))
        # injection avant toute construction de la commande du banc
        self.assertLess(inject, main.index('benchmark += ["--reference", args.reference]'))


if __name__ == "__main__":
    unittest.main()
