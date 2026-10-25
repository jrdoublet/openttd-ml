"""Static CARTO-1 shadow runtime contracts (no engine, Docker or .nut writes).

These checks guard the actual Squirrel entry points and safety gates. They
cannot establish a runtime opcode ceiling or economic neutrality; those need
separate instrumented games.
"""

from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
BIT25 = 1 << 25


def source(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def uncomment(text: str) -> str:
    """Remove Squirrel comments without altering quoted string literals."""
    token = re.compile(
        r'(?P<quoted>"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')'
        r'|(?P<comment>/\*.*?\*/|//[^\n]*)',
        re.DOTALL,
    )
    return token.sub(lambda match: match.group("quoted") or "", text)


def function_body(text: str, name: str) -> str:
    """Return one named Squirrel function, never neighboring functions."""
    text = uncomment(text)
    match = re.search(
        r"\bfunction\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{", text
    )
    if not match:
        raise AssertionError(f"Missing Squirrel function {name}")
    opening = match.end() - 1
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1:index]
    raise AssertionError(f"Unclosed Squirrel function {name}")


class Carto1RuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe = uncomment(source("probe_carto1.nut"))
        cls.globals = uncomment(source("globals_pre.nut"))
        cls.settings = uncomment(source("settings.nut"))
        cls.info = uncomment(source("info.nut"))
        cls.main = uncomment(source("main.nut"))
        cls.profiled = uncomment(source("probes.nut"))
        cls.rail = uncomment(source("task_rail.nut"))
        cls.persist = uncomment(source("persist.nut"))

    def body(self, name: str, path: str = "probe_carto1.nut") -> str:
        return function_body(source(path), name)

    def test_bit25_is_off_by_default_and_isolated_from_default_probe_mask(self):
        self.assertEqual(BIT25, 33554432)
        self.assertRegex(self.globals, r"\bCARTO1_SHADOW\s*<-\s*false\s*;")
        get_settings = function_body(self.info, "GetSettings")
        probes = re.search(
            r'\bAddSetting\s*\(\s*\{\s*name\s*=\s*"probes"\s*,(.*?)\}\s*\)',
            get_settings, re.DOTALL,
        )
        self.assertIsNotNone(probes, "Missing probes AddSetting")
        for setting in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(probes.group(1), rf"\b{setting}\s*=\s*2\b")
        self.assertEqual(2 & BIT25, 0)
        self.assertRegex(
            self.settings,
            rf"\bCARTO1_SHADOW\s*=\s*OpexProbeEnabled\(\s*{BIT25}\s*\)\s*;",
        )
        probe_enabled = function_body(self.settings, "OpexProbeEnabled")
        self.assertRegex(
            probe_enabled,
            r"return\s+\(\s*OPEX_PROBE_MASK\s*&\s*\(\s*bit\s*\|\s*legacyGroup"
            r"\s*\)\s*\)\s*!=\s*0\s*;",
        )

    def test_bit25_has_one_owner_in_master_settings(self):
        owners = []
        assignments = []
        alternate_bit_masks = []
        for path in sorted(AI.rglob("*.nut")):
            code = uncomment(path.read_text(encoding="utf-8"))
            for match in re.finditer(rf"(?<!\d){BIT25}(?!\d)", code):
                owners.append((path.relative_to(AI).as_posix(), match.start()))
            for match in re.finditer(r"\bCARTO1_SHADOW\s*(?:<-|(?<![=!<>])=(?!=))", code):
                assignments.append(path.relative_to(AI).as_posix())
            if re.search(r"\b(?:1\s*<<\s*25|0x0*2000000)\b", code, re.I):
                alternate_bit_masks.append(path.name)
        self.assertEqual(
            [file for file, _ in owners], ["settings.nut"],
            "Bit 25 must be uniquely assigned in the current master-derived tree",
        )
        self.assertEqual(
            sorted(assignments), ["globals_pre.nut", "settings.nut"],
            "CARTO1_SHADOW may only be declared OFF and loaded from probes",
        )
        self.assertEqual(alternate_bit_masks, [], "Duplicate bit-25 spelling")

    def test_both_main_loops_call_same_guarded_step_before_sleep(self):
        self.assertEqual(
            len(re.findall(r'\brequire\("probe_carto1\.nut"\)\s*;', self.main)), 1
        )
        self.assertLess(
            self.main.index('require("probe_v308.nut")'),
            self.main.index('require("probe_carto1.nut")'),
            "CARTO1 uses the V308 full6 sampler",
        )
        plain = function_body(self.main, "OpexAI::Start")
        profiled = function_body(self.profiled, "OpexAI::_mainLoopProfiled")
        guarded = (r"if\s*\(\s*CARTO1_SHADOW\s*&&\s*!CARTO2_SHADOW\s*\)"
                   r"\s*OpexCarto1Step\(\s*this\s*\)\s*;")
        for name, body in (("main", plain), ("profiled", profiled)):
            with self.subTest(loop=name):
                self.assertEqual(len(re.findall(guarded, body)), 1)
                self.assertLess(body.index("OpexCarto1Step(this)"),
                                body.rindex("AIController.Sleep(1)"))
                self.assertLess(body.index("OpexV309IdleTick(this)"),
                                body.index("OpexCarto1Step(this)"))
        self.assertRegex(
            self.body("OpexCarto1Step"),
            r"^\s*if\s*\(\s*!CARTO1_SHADOW\s*\)\s*return\s*;",
        )

    def test_probe_module_issues_no_construction_or_world_mutation_commands(self):
        forbidden = (
            # Production builders belong to task_rail/builder_* and are not
            # allowed in a shadow probe even inside AITestMode.
            r"\b(?:AITile|AIRail|AIRoad|AIAirport|AIIndustry|AITown|AIStation|"
            r"AIVehicle|AIBridge|AITunnel|AIWater|AICompany)\s*\.\s*"
            r"(?:Build\w*|Remove\w*|Demolish\w*|Terraform\w*|"
            r"Set\w*|Move\w*|Sell\w*|DoCommand\w*)\s*\(",
            r"\bOpex(?:Build|Demolish|Remove|Terraform)\w*\s*\(",
            r"\b(?:AIController\.)?Sleep\s*\(",
            r"\bAITestMode\s*\(",
        )
        for command in forbidden:
            with self.subTest(command=command):
                self.assertNotRegex(self.probe, command)
        self.assertIn("OpexDecide(", self.probe)

    def test_full6_sampler_from_v308_is_memoized_by_physical_block_id(self):
        read = self.body("OpexCarto1ReadBlock")
        scan = self.body("OpexCarto1ScanStep")
        initial = self.body("OpexCarto1Init")
        self.assertRegex(read, r"\bOpexV308Arm\(\s*bx\s*,\s*by\s*,\s*1\s*\)")
        self.assertRegex(read, r"\bstate\.cache\s*\[\s*id\s*\]\s*<-\s*record\s*;")
        self.assertRegex(read, r"\bstate\.blocks\s*\+\+")
        self.assertRegex(
            scan,
            r"if\s*\(\s*!\(\s*id\s+in\s+state\.cache\s*\)\s*\)\s*\{\s*"
            r"if\s*\(\s*AIController\.GetOpsTillSuspend\(\)\s*<\s*5000\s*\)"
            r"\s*return\s*;\s*OpexCarto1ReadBlock\(\s*state\s*,\s*id\s*\)\s*;",
        )
        self.assertEqual(
            len(re.findall(r"\bOpexCarto1ReadBlock\(", self.probe)), 2,
            "Block sampling must only occur in the cache-miss branch",
        )
        self.assertRegex(initial, r"\bcache\s*=\s*\{\s*\}")
        self.assertNotRegex(self.probe, r"\bdelete\s+state\.(?:cache|seen)\s*\[")
        self.assertNotRegex(self.probe, r"\bstate\.(?:cache|seen)\s*=\s*(?!\{)")

    def test_v308_mode_one_really_samples_four_peripheral_and_two_central_tiles(self):
        v308 = uncomment(source("probe_v308.nut"))
        arm = function_body(v308, "OpexV308Arm")
        for points, expected in (("V308_PERIPHERAL", 4), ("V308_CENTRAL", 2)):
            definition = re.search(
                rf"\b{points}\s*<-\s*\[(.*?)\]\s*;", v308, re.DOTALL,
            )
            self.assertIsNotNone(definition, points)
            self.assertEqual(
                len(re.findall(r"\[\s*\d+\s*,\s*\d+\s*\]", definition.group(1))),
                expected,
                f"{points} should have {expected} sample positions",
            )
        self.assertRegex(arm, r"if\s*\(\s*mode\s*==\s*0\s*\)")
        self.assertRegex(arm, r"local\s+delta\s*=\s*\(\s*mode\s*==\s*3")
        self.assertRegex(arm, r"foreach\s*\(\s*p\s+in\s+V308_PERIPHERAL\s*\)")
        self.assertRegex(arm, r"local\s+centers\s*=\s*true\s*;")
        self.assertRegex(arm, r"if\s*\(\s*mode\s*==\s*2\s*\)")
        self.assertRegex(arm, r"else\s+if\s*\(\s*mode\s*==\s*4\s*\)")
        self.assertRegex(
            arm, r"if\s*\(\s*centers\s*\)\s*\{\s*"
                 r"foreach\s*\(\s*p\s+in\s+V308_CENTRAL\s*\)",
        )

    def test_queue_de_duplicate_and_bounded_corridor_per_request(self):
        request = self.body("OpexCarto1Request")
        corridor = self.body("OpexCarto1CorridorStep")
        step = self.body("OpexCarto1Step")
        self.assertRegex(request, r"if\s*\(\s*key\s+in\s+state\.seen\s*\)\s*return")
        self.assertRegex(request, r"state\.seen\s*\[\s*key\s*\]\s*<-\s*true")
        self.assertRegex(
            request, r"state\.requests\s*>=\s*72\s*\|\|\s*state\.queue\.len\(\)\s*>=\s*16",
        )
        self.assertRegex(request, r"\bstate\.requests\s*\+\+")
        self.assertRegex(step, r"if\s*\(\s*considered\s*\+\+\s*>=\s*6\s*\)\s*break")
        self.assertRegex(corridor, r"for\s*\(\s*local\s+n\s*=\s*0\s*;\s*n\s*<\s*2\b")
        self.assertRegex(
            corridor, r"job\.ids\.len\(\)\s*>\s*420\s*\?\s*\"skip\"\s*:\s*\"scan\"",
        )
        self.assertRegex(corridor, r"if\s*\(\s*id\s+in\s+job\.member\s*\)\s*continue")
        self.assertRegex(corridor, r"job\.member\s*\[\s*id\s*\]\s*<-\s*true")

    def test_opcode_gates_and_bounded_work_across_phases(self):
        scan = self.body("OpexCarto1ScanStep")
        route = self.body("OpexCarto1RouteStep")
        step = self.body("OpexCarto1Step")
        self.assertRegex(scan, r"GetOpsTillSuspend\(\)\s*<\s*5000\s*\)\s*return")
        self.assertRegex(route, r"GetOpsTillSuspend\(\)\s*<\s*6000\s*\)\s*return")
        self.assertRegex(
            step,
            r"for\s*\(\s*local\s+n\s*=\s*0\s*;\s*n\s*<\s*3\s*&&\s*"
            r"AIController\.GetOpsTillSuspend\(\)\s*>=\s*6500\s*;",
        )
        self.assertRegex(step, r"GetOpsTillSuspend\(\)\s*>=\s*7500")
        self.assertRegex(step, r"GetOpsTillSuspend\(\)\s*>=\s*2700")
        self.assertRegex(step, r"if\s*\(\s*phase\s*==\s*\"route\"\s*\|\|\s*"
                         r"state\.current\s*==\s*null\s*\)\s*break")
        # A coarse Dijkstra step expands one best frontier block per call.
        self.assertRegex(route, r"delete\s+job\.frontier\s*\[\s*best\s*\]")
        self.assertRegex(route, r"job\.visited\s*\[\s*best\s*\]\s*<-\s*true")
        self.assertNotRegex(route, r"\b(?:while\s*\(\s*true|for\s*\(\s*;\s*;)")
        self.assertRegex(step, r"state\.scans\s*\+=\s*spent\s*;")
        self.assertRegex(step, r"AIController\.GetTick\(\)\s*!=\s*mark\.tick")

    def test_direct_and_stock_astar_have_shadow_guarded_hooks(self):
        direct = self.body("OpexAI::_startRailSearch", "task_rail.nut")
        continuation = self.body("OpexAI::_continueRailSearch", "task_rail.nut")
        stock = self.body("OpexAI::_startRailStockSearch", "task_rail.nut")
        probe_astar = self.body("OpexCarto1Astar")
        self.assertRegex(
            direct, r'if\s*\(\s*CARTO1_SHADOW\s*&&\s*!CARTO2_SHADOW\s*\)\s*'
                    r'OpexCarto1Request\(\s*candidate\s*,\s*"astar"\s*\)',
        )
        self.assertRegex(
            direct, r'OpexCarto1Astar\(\s*candidate\s*,\s*"start"\s*,\s*"SEARCH"\s*,\s*0\s*\)',
        )
        self.assertGreaterEqual(
            len(re.findall(r'OpexCarto1Astar\(\s*candidate\s*,\s*"end"\s*,\s*"NOPA"', direct)),
            2,
        )
        self.assertRegex(
            continuation,
            r'if\s*\(\s*CARTO1_SHADOW\s*&&\s*state\.kind\s*==\s*"primary"\s*\)'
            r'\s*\{\s*OpexCarto1Astar\(\s*state\.candidate\s*,\s*"end"\s*,\s*'
            r'slice\.stop\s*,\s*state\.spent\s*\)',
        )
        self.assertRegex(
            stock,
            r'if\s*\(\s*CARTO1_SHADOW\s*&&\s*'
            r'AIController\.GetOpsTillSuspend\(\)\s*>=\s*3000\s*\)'
            r'\s*\{\s*OpexCarto1Request\(\s*candidate\s*,\s*"astar"\s*\)',
        )
        self.assertRegex(
            probe_astar, r"if\s*\(\s*!CARTO1_SHADOW\s*\|\|\s*"
                         r"candidate\s*==\s*null\s*\)\s*return",
        )
        self.assertIn('OpexDecide("CARTO1_ASTAR"', probe_astar)

    def test_save_load_do_not_persist_carto_cache_or_jobs(self):
        save = self.body("OpexAI::Save", "persist.nut")
        load = self.body("OpexAI::Load", "persist.nut")
        reconcile = self.body("OpexAI::_reconcileAfterLoad", "persist.nut")
        for phase, body in (("Save", save), ("Load", load), ("reconcile", reconcile)):
            with self.subTest(phase=phase):
                self.assertNotRegex(body, r"\b(?:CARTO1|OpexCarto1)\w*\b")
                self.assertNotRegex(body, r"\bcarto1\w*\b")
        start = self.body("OpexAI::Start", "main.nut")
        self.assertRegex(
            start,
            r"\bOpexLoadSettings\(\)\s*;\s*"
            r"if\s*\(\s*CARTO1_SHADOW\s*\)\s*CARTO1_STATE\s*=\s*null\s*;",
        )
        self.assertLess(start.index("CARTO1_STATE = null"),
                        start.index("this._reconcileAfterLoad()"))
        self.assertRegex(
            self.body("OpexCarto1Init"),
            r"\bCARTO1_STATE\s*=\s*\{[^}]*cache\s*=\s*\{\s*\}"
            r"[^}]*seen\s*=\s*\{\s*\}[^}]*queue\s*=\s*\[\s*\]",
        )


if __name__ == "__main__":
    unittest.main()
