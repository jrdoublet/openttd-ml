"""Contrats RAIL-LOOP (rail_loop, défaut 0) — 04/11/2026.

Boucle à sens unique : voie 1 existante, voie 2 neuve de l'arrière du quai
aval vers l'arrière du quai amont, PBS_ONEWAY sur les deux voies, croissance
de flotte par clones à ordres partagés. Ces tests ne compilent pas Squirrel :
ils vérifient le câblage opt-in, la projection OFF octet pour octet, l'ordre
des opérations de sûreté, et (faute de compilateur) les références et arités
des appels du module neuf.
"""

import hashlib
import re
import sys
import unittest
from pathlib import Path

SWEEPS = Path(__file__).resolve().parent
sys.path.insert(0, str(SWEEPS))
AI = SWEEPS.parent / "ai" / "OpexAI"

from rail_loop_off import INSERTIONS, off_source  # noqa: E402
from rail_fill_off import off_source as rail_fill_off  # noqa: E402
from rail_config_merge_witness import expected_off_sha  # noqa: E402

# Empreintes des six fichiers câblés AVANT RAIL-LOOP (commit 47395b4).
PRE_INTERVENTION_SHA = {
    "globals_pre.nut": "823a84e270ad88f20a68946744722447b1aa321f88de71c238e921b9aeda0f45",
    "settings.nut": "e4539ce779c0900a6fbd273c59f6f1e23e7b680f4c8dd01dd3d170fcfe2b4b5a",
    "info.nut": "0cb67a467982f588c3ef19587a11668ea8773b1068b91193fc33f167d4399c69",
    "main.nut": "05192d5730982a23382a1fb1dc3a04cf15c858d17e061715fedf732ed9f07acc",
    "task_rail.nut": "5673872724b7c1cea40b13170095a42c7c823ed5c6c3ce1e5d11321982776f6e",
    "scheduler.nut": "68edd4fb317e019d5bfffa4af50bddfdb86942aee789f575a2767d7180891d10",
}


def read(name):
    return (AI / name).read_text(encoding="utf8")


def strip_squirrel(source):
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    source = re.sub(r"//[^\n]*", "", source)
    return re.sub(r'"(\\.|[^"\\])*"', '""', source)


def function_body(source, name):
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace:i + 1]
    raise AssertionError("unterminated " + name)


def split_args(text):
    depth, args, cur = 0, [], ""
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            args.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        args.append(cur)
    return args


def call_args(source, start):
    depth = 0
    for i in range(start, len(source)):
        if source[i] == "(":
            depth += 1
        elif source[i] == ")":
            depth -= 1
            if depth == 0:
                return split_args(source[start + 1:i])
    raise AssertionError("unterminated call")


def global_signatures():
    sigs = {}
    for path in AI.rglob("*.nut"):
        text = strip_squirrel(path.read_text(encoding="utf8", errors="replace"))
        for m in re.finditer(r"\bfunction\s+(Opex\w+)\s*\(([^)]*)\)", text):
            params = [p.strip() for p in split_args(m.group(2))]
            required = sum(1 for p in params if p and "=" not in p)
            sigs.setdefault(m.group(1), []).append((required, len(params)))
    return sigs


class RailLoopSettingContracts(unittest.TestCase):
    def test_setting_default_one_boolean_four_difficulties(self):
        info = read("info.nut")
        block = info[info.index('name = "rail_loop"'):]
        block = block[:block.index("});")]
        self.assertIn("min_value = 0, max_value = 1", block)
        self.assertIn("easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1", block)
        self.assertIn("AICONFIG_BOOLEAN", block)
        self.assertEqual(info.count('name = "rail_loop"'), 1)

    def test_global_false_and_single_read(self):
        self.assertEqual(read("globals_pre.nut").count("RAIL_LOOP <- false;"), 1)
        settings = read("settings.nut")
        self.assertEqual(settings.count('GetSetting("rail_loop")'), 1)
        self.assertIn('RAIL_LOOP = AIController.GetSetting("rail_loop") == 1;', settings)

    def test_module_loaded_and_state_declared(self):
        main = read("main.nut")
        self.assertEqual(main.count('require("rail_loop.nut");'), 1)
        self.assertLess(main.index('require("double_grow_v2.nut");'), main.index('require("rail_loop.nut");'))
        self.assertIn("  _railLoopState = null;", main)

    def test_every_hook_is_guarded_by_the_setting(self):
        for name, fragments in INSERTIONS.items():
            for fragment in fragments:
                code = fragment.strip()
                if code.startswith("if (") or code.startswith("if(") :
                    self.assertTrue(code.startswith("if (RAIL_LOOP &&"), (name, code))
        rail = read("task_rail.nut")
        expand = function_body(rail, "OpexAI::_expandRailLines")
        self.assertLess(expand.index("OpexDoubleGrowV2Select"), expand.index("OpexRailLoopSelect"))
        self.assertLess(expand.index("OpexRailLoopSelect"), expand.index("foreach (line in this._lines)"))
        self.assertIn('if (RAIL_LOOP && ("railLoop" in line) && line.railLoop > 0) continue;', expand)


class RailLoopOffProjection(unittest.TestCase):
    def test_off_projection_restores_pre_intervention_bytes(self):
        for name, digest in PRE_INTERVENTION_SHA.items():
            with self.subTest(name=name):
                # RAIL-FILL, couche posterieure, est retiree d'abord.
                live = read(name)
                projected = off_source(name, rail_fill_off(name, live))
                self.assertEqual(hashlib.sha256(projected.encode("utf8")).hexdigest(),
                                 expected_off_sha(name, "rail_fill_then_loop_off", digest, live))
                self.assertEqual(off_source(name, projected), projected)

    def test_partial_hunk_fails_closed(self):
        source = read("task_rail.nut")
        damaged = source.replace("OpexRailLoopSelect(this, year)", "OpexRailLoopSelect(this, year + 0)")
        with self.assertRaises(AssertionError):
            off_source("task_rail.nut", damaged)
        duplicated = read("scheduler.nut") + INSERTIONS["scheduler.nut"][0]
        with self.assertRaises(AssertionError):
            off_source("scheduler.nut", duplicated)

    def test_historic_v181_log_tag_is_not_a_marker(self):
        builder = read("builder_rail.nut")
        self.assertIn('OpexDecide("RAIL_LOOP", "action=convert', builder)
        self.assertEqual(off_source("builder_rail.nut", builder), builder)
        self.assertNotIn('OpexDecide("RAIL_LOOP"', read("rail_loop.nut"))


class RailLoopModuleSafety(unittest.TestCase):
    def setUp(self):
        self.raw = read("rail_loop.nut")
        self.code = strip_squirrel(self.raw)

    def test_balanced_delimiters(self):
        stack = []
        pairs = {")": "(", "]": "[", "}": "{"}
        for ch in self.code:
            if ch in "([{":
                stack.append(ch)
            elif ch in ")]}":
                self.assertTrue(stack and stack[-1] == pairs[ch], "delimiteur mal imbrique")
                stack.pop()
        self.assertEqual(stack, [])

    def test_squirrel_pitfalls_absent(self):
        self.assertNotIn("getroottable", self.code)
        self.assertNotIn(".find(", self.code)
        self.assertIsNone(re.search(r"function\s*\(", self.code), "fonction anonyme")
        self.assertNotIn("Sleep(", self.code)
        self.assertNotIn(".Valuate(", self.code)
        self.assertNotIn("const ", self.code)
        for kw in ("clone", "base", "parent", "static", "delegate", "vargc", "vargv",
                   "resume", "yield", "constructor", "instanceof"):
            self.assertIsNone(re.search(r"\blocal\s+" + kw + r"\b", self.code), kw)
            self.assertIsNone(re.search(r"[(,]\s*" + kw + r"\s*[,)=]", self.code.replace("(owner, line, route", "")), kw)

    def test_never_touches_the_project_search_slot(self):
        self.assertNotIn("_railSearch", self.code)
        self.assertNotIn("_startRailSearch", self.code)
        self.assertNotIn("_startRailUpgradeSearch", self.code)

    def test_every_called_opex_function_exists_with_compatible_arity(self):
        sigs = global_signatures()
        for m in re.finditer(r"\b(Opex\w+)\s*\(", self.code):
            name = m.group(1)
            if re.search(r"function\s+$", self.code[max(0, m.start() - 12):m.start()]):
                continue
            with self.subTest(call=name):
                self.assertIn(name, sigs, "fonction inconnue")
                n = len(call_args(self.code, m.end() - 1))
                self.assertTrue(any(req <= n <= tot for req, tot in sigs[name]),
                                f"{name}: {n} arguments, signatures {sigs[name]}")

    def test_module_functions_defined_once(self):
        names = re.findall(r"\bfunction\s+(\w+)\s*\(", self.code)
        self.assertEqual(len(names), len(set(names)))


class RailLoopBehaviourContracts(unittest.TestCase):
    def setUp(self):
        self.code = strip_squirrel(read("rail_loop.nut"))

    def test_track2_is_signalled_before_it_is_connected(self):
        body = function_body(self.code, "OpexRailLoopBuildTrack2")
        interior = body.index("for (local i = 2; i <= n - 3; i++)")
        signals = body.index("OpexRailLoopSignalRun(tiles, 3, n - 4, 1, spacing, placed)")
        ends = body.index("OpexRailLoopBuildIndex(tiles, structures, 1)")
        self.assertLess(interior, signals)
        self.assertLess(signals, ends)
        self.assertIn("OpexRailLoopBuildIndex(tiles, structures, n - 2)", body[ends:])
        # Aucune depense avant certification native et devis.
        self.assertLess(body.index("OpexTestRailTrack(tiles, structures)"), interior)
        self.assertLess(body.index("OpexAvailableCapital() < trackCost + trainPrice"), interior)
        raw = function_body(read("rail_loop.nut"), "OpexRailLoopBuildTrack2")
        self.assertLess(raw.index('"end_structure"'),
                        raw.index("for (local i = 2; i <= n - 3; i++)"))

    def test_track1_is_armed_only_when_every_train_runs_downstream(self):
        step = function_body(self.code, "OpexRailLoopStep")
        self.assertLess(step.index("OpexRailLoopArmSafe(line, state.flow)"),
                        step.index("OpexRailLoopArm(owner, state)"))
        safe = function_body(self.code, "OpexRailLoopArmSafe")
        self.assertIn("AIOrder.ORDER_CURRENT", safe)
        self.assertIn("IsStoppedInDepot", safe)

    def test_guard_signal_between_upstream_station_and_depot(self):
        arm = function_body(self.code, "OpexRailLoopArm")
        self.assertIn("OpexV190Fix2PlaceSignalWindow(route, k - 1, 2, -1, 1, placed)", arm)
        self.assertIn("OpexV190Fix2PlaceSignalWindow(route, k + 1, n - 3, 1, -1, placed)", arm)
        self.assertIn("OpexV190Fix2Rollback([], placed)", arm)
        pre = function_body(self.code, "OpexRailLoopArmPrecheck")
        self.assertIn("AITestMode()", pre)
        self.assertIn("AIAccounting()", pre)
        begin = function_body(self.code, "OpexRailLoopBegin")
        self.assertIn("OpexRailLoopArmPrecheck(", begin)

    def test_failure_never_demolishes_a_connected_track(self):
        fail = function_body(self.code, "OpexRailLoopFail")
        self.assertNotIn("Demolish", fail)
        self.assertNotIn("Rollback", fail)
        build = function_body(self.code, "OpexRailLoopBuildTrack2")
        # Le retrait n'est appele qu'au sein de la pose, avant ou au raccord.
        self.assertGreaterEqual(build.count("OpexRailLoopRollbackTrack2"), 3)

    def test_fleet_growth_is_bounded_and_shares_orders(self):
        self.assertIn("RAIL_LOOP_MAX_TRAINS <- 8;", self.code)
        commit = function_body(self.code, "OpexRailLoopCommit")
        self.assertIn("local cap = blocks - 2;", commit)
        self.assertIn("if (cap > RAIL_LOOP_MAX_TRAINS) cap = RAIL_LOOP_MAX_TRAINS;", commit)
        clone = function_body(self.code, "OpexRailLoopClone")
        self.assertIn("AIVehicle.CloneVehicle(line.depot, model, true)", clone)
        self.assertIn("OpexRailVehicleSlotAvailable()", clone)
        grow = function_body(self.code, "OpexRailLoopGrow")
        self.assertIn("waiting < capacity", grow)
        self.assertIn("line.trains >= cap", grow)

    def test_cash_refusal_defers_the_line_and_keeps_scanning(self):
        select = function_body(read("rail_loop.nut"), "OpexRailLoopSelect")
        defer = select.index('"defer"')
        tail = select[defer:defer + 200]
        self.assertIn("continue;", tail)
        self.assertNotIn("return false;", tail)

    def test_search_is_bounded_per_scheduler_pass(self):
        step = function_body(self.code, "OpexRailLoopStep")
        self.assertIn("RAIL_LOOP_SLICE", step)
        self.assertIn("RAIL_LOOP_BUDGET", step)
        self.assertIn("RAIL_LOOP_SLICE <- 200;", self.code)

    def test_back_plan_follows_builder_convention(self):
        back = function_body(self.code, "OpexRailLoopBackPlan")
        self.assertIn("local endFar = platform.station_exit != platform.anchor;", back)
        self.assertIn(": platform.anchor + platform.step * (platform.length - 1);", back)
        self.assertIn("local backLead = endFar ? backExit - platform.step : backExit + platform.step;", back)
        self.assertIn("AITile.IsBuildable(backLead)", back)


if __name__ == "__main__":
    unittest.main()
