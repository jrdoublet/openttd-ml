"""V259 : renouvellement des ponts rail (et route) dont la vitesse bride les vehicules.

Verifications statiques et de contrat du mecanisme :
1. Reglage v259_bridge_renew (0/1, defaut 0), zero opcode au defaut hors garde O(1).
2. Le nombre d'AddSetting correspond au catalogue nettoye (86).
3. Inventaire des ponts au fil des constructions (line.bridges), sans balayage de carte.
4. Decision economique sans nombre arbitraire :
   - v_pont < v_veh ET modele plus rapide disponible
   - gain = temps gagne par rotation * profit des vehicules (part du cycle sur le pont)
   - payer si gain * vie restante >= cout mesure (AITestMode + AIAccounting)
   - priorite aux lignes les plus rentables
5. Opcodes : declenche a l'apparition d'un nouveau type de pont (AIBridgeList),
   au plus un pont evalue/remplace par passage reactif (curseur).
6. Journal sous DECISION_LOG : V259_BRIDGE (ligne, tuiles, ancien/nouveau type et vitesse, cout, gain, decision).
7. Persistance et reconciliation au chargement.
"""
from pathlib import Path
import re
import unittest

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _body(source, signature):
    match = re.search(re.escape(signature) + r"\s*\n\{(.*?)\n\}", source, re.S)
    return match.group(1) if match else ""


class TestV259BridgeRenew(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.task = cls.sources["task_v259.nut"]
        cls.info = cls.sources["info.nut"]
        cls.settings = cls.sources["settings.nut"]
        cls.globals_pre = cls.sources["globals_pre.nut"]
        cls.main = cls.sources["main.nut"]
        cls.orchestrator = cls.sources["orchestrator.nut"]
        cls.scheduler = cls.sources["scheduler.nut"]
        cls.persist = cls.sources["persist.nut"]
        cls.builder_rail = cls.sources["builder_rail.nut"]
        cls.task_rail = cls.sources["task_rail.nut"]

    def test_setting_declared_default_zero(self):
        block = re.search(
            r'name = "v259_bridge_renew",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(block, "v259_bridge_renew doit etre declare dans info.nut")
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 1", body)
        self.assertIn("step_size = 1", body)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value", "default_value"):
            self.assertRegex(body, level + r" = 0\b", f"{level} doit etre 0")
        self.assertIn("V259_BRIDGE_RENEW <- 0;", self.globals_pre)

    def test_setting_read_once(self):
        reads = [(name, text.count('GetSetting("v259_bridge_renew")'))
                 for name, text in self.sources.items()]
        self.assertEqual(sum(count for _, count in reads), 1, "v259_bridge_renew doit etre lu une seule fois")
        self.assertIn('AIController.GetSetting("v259_bridge_renew")', self.settings)

    def test_setting_count_after_cleanup(self):
        # Le nettoyage des lots 1-6 retire des options, sans retirer V259.
        self.assertEqual(self.info.count("AddSetting("), 86)
        self.assertIn('name = "v259_bridge_renew"', self.info)

    def test_zero_opcode_guard_at_default(self):
        # 1. Garde dans scheduler.nut
        self.assertIn("if (V259_BRIDGE_RENEW > 0) this._v259CheckNewBridges();", self.scheduler)
        # 2. Garde dans _v259CheckNewBridges()
        body_check = _body(self.task, "function OpexAI::_v259CheckNewBridges()")
        self.assertTrue(body_check)
        guard1 = "if (V259_BRIDGE_RENEW == 0) return;"
        self.assertIn(guard1, body_check)
        self.assertEqual(body_check.strip().index(guard1), 0, "Garde O(1) doit etre en premiere ligne de _v259CheckNewBridges")
        # 3. Garde dans _v259StepBridgeRenew()
        body_step = _body(self.task, "function OpexAI::_v259StepBridgeRenew()")
        self.assertTrue(body_step)
        guard2 = "if (V259_BRIDGE_RENEW == 0) return true;"
        self.assertIn(guard2, body_step)
        self.assertEqual(body_step.strip().index(guard2), 0, "Garde O(1) doit etre en premiere ligne de _v259StepBridgeRenew")

    def test_triggered_on_new_bridge_type_appearance(self):
        body_check = _body(self.task, "function OpexAI::_v259CheckNewBridges()")
        self.assertIn("AIBridgeList()", body_check)
        self.assertIn("curCount > this._v259KnownBridgesCount", body_check)
        self.assertIn("this._v259PrepareBridgeQueue()", body_check)
        self.assertIn('this._enqueueReactive("v259_bridge", "v259_bridge", null)', body_check)

    def test_reactive_queue_at_most_one_bridge_per_pass(self):
        body_step = _body(self.task, "function OpexAI::_v259StepBridgeRenew()")
        # Doit evaluer un seul item a la fois
        self.assertIn("local item = this._v259Queue[this._v259Cursor];", body_step)
        self.assertIn("this._v259Cursor++;", body_step)
        self.assertIn("this._v259EvaluateAndRenew(item);", body_step)
        # Re-enfilement si le curseur n'a pas fini
        self.assertIn('if (this._v259Cursor < this._v259Queue.len())', body_step)
        self.assertIn('this._enqueueReactive("v259_bridge", "v259_bridge", null)', body_step)

    def test_vehicle_speed_uses_supported_engine_api(self):
        speed_body = _body(self.task, "function OpexV259LineMaxVehicleSpeed(line)")
        self.assertIn("AIEngine.GetMaxSpeed(AIVehicle.GetEngineType(v))", speed_body)
        self.assertNotIn("AIVehicle.GetMaxSpeed", speed_body)

    def test_economic_decision_formula(self):
        eval_body = _body(self.task, "function OpexAI::_v259EvaluateAndRenew(item)")
        self.assertTrue(eval_body)
        # 1. Condition de vitesse : vitesse pont < vitesse vehicule
        self.assertIn("oldSpeed >= maxVehSpeed", eval_body)
        # 2. Modèle plus rapide disponible
        self.assertIn("AIBridgeList_Length", eval_body)
        self.assertIn("bestSpeed <= oldSpeed", eval_body)
        # 3. Vitesse effective bornée par maxVehSpeed
        self.assertIn("(bestSpeed < maxVehSpeed) ? bestSpeed : maxVehSpeed", eval_body)
        # 4. Temps gagné par rotation et part du cycle
        self.assertIn("savedDays = oldDays - newDays", eval_body)
        self.assertIn("cycleFraction = savedDays / cycleDays", eval_body)
        # 5. Gain annuel = part du cycle * profit
        self.assertIn("gain = (cycleFraction * lineProfit).tointeger()", eval_body)
        # 6. Condition économique : gain * vie restante >= cout mesure
        self.assertIn("totalGain = gain.tofloat() * remainingYears", eval_body)
        self.assertIn("totalGain < cost.tofloat()", eval_body)
        # 7. Mesure de coût avec AIAccounting et AITestMode
        cost_body = _body(self.task, "function OpexV259MeasureBridgeCost(vtype, newBridgeType, start, end)")
        self.assertIn("AIAccounting()", cost_body)
        self.assertIn("AITestMode()", cost_body)
        self.assertIn("account.GetCosts()", cost_body)
        # 8. Réserve de trésorerie respectée
        self.assertIn("OpexCashReserve()", eval_body)
        self.assertIn("cash - cost < threshold", eval_body)

    def test_priority_to_most_profitable_lines(self):
        body_prep = _body(self.task, "function OpexAI::_v259PrepareBridgeQueue()")
        self.assertTrue(body_prep)
        self.assertIn("OpexV259LineProfit(line)", body_prep)
        self.assertIn("this._v259Queue.sort(OpexV259CompareBridges)", body_prep)
        comp_body = _body(self.task, "function OpexV259CompareBridges(a, b)")
        self.assertIn("if (a.profit > b.profit) return -1;", comp_body)

    def test_bridge_inventory_on_construction(self):
        # task_rail extrait les ponts du plan rail (structures/tiles) sans toucher builder_rail
        self.assertIn("lineBridges.append({ start = c, end = n, vtype = AIVehicle.VT_RAIL, railType = rType });", self.task_rail)
        self.assertIn("bridges = lineBridges,", self.task_rail)
        # task_road enregistre line.bridges
        self.assertIn('bridges = ("bridges" in result && result.bridges != null) ? result.bridges : [],', self.sources["task_road.nut"])

    def test_persist_and_reconciliation(self):
        # Sauvegarde conditionnelle sous v259_bridge_renew != 0
        self.assertIn("if (V259_BRIDGE_RENEW != 0)", self.persist)
        self.assertIn("v259KnownBridgesCount", self.persist)
        self.assertIn("v259Cursor", self.persist)
        self.assertIn("v259Queue", self.persist)
        # Rechargement et reconciliation
        reconcile_body = _body(self.persist, "function OpexAI::_reconcileAfterLoad()")
        self.assertIn("line.bridges = liveBridges;", reconcile_body)
        self.assertIn("AIBridge.IsBridgeTile(b.start)", reconcile_body)
        self.assertIn("AITile.GetOwner(b.start) == selfComp", reconcile_body)

    def test_decision_log_format(self):
        self.assertIn('OpexDecide("V259_BRIDGE"', self.task)
        # Tous les OpexDecide sous DECISION_LOG
        for line in self.task.splitlines():
            if "OpexDecide(" in line:
                self.assertIn("DECISION_LOG", line, f"OpexDecide non garde par DECISION_LOG: {line}")
        # Champs requis dans V259_BRIDGE
        self.assertIn('"line=" + lineId', self.task)
        self.assertIn('" tiles=" + start + "->" + end', self.task)
        self.assertIn('" old_type=" + oldBridgeType', self.task)
        self.assertIn('" old_speed=" + oldSpeed', self.task)
        self.assertIn('" new_type=" + bestBridgeType', self.task)
        self.assertIn('" new_speed=" + bestSpeed', self.task)
        self.assertIn('" cost=" + cost', self.task)
        self.assertIn('" gain=" + gain', self.task)
        self.assertIn('" decision=" + decision', self.task)

    def test_no_reserved_keywords(self):
        # Pas de clone, base, parent comme identifiants dans task_v259.nut
        noncode = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"', re.S)
        code = noncode.sub("", self.task)
        tokens = re.findall(r"\b\w+\b", code)
        reserved = {"clone", "base", "parent"}
        for t in tokens:
            self.assertNotIn(t, reserved, f"Mot reserve {t} trouve dans task_v259.nut")

    def test_delimiters_balanced(self):
        for name, text in (("task_v259.nut", self.task),
                           ("main.nut", self.main),
                           ("settings.nut", self.settings),
                           ("info.nut", self.info),
                           ("orchestrator.nut", self.orchestrator),
                           ("scheduler.nut", self.scheduler),
                           ("persist.nut", self.persist),
                           ("builder_rail.nut", self.builder_rail)):
            noncode = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"', re.S)
            code = noncode.sub("", text)
            stack = []
            pairs = {')': '(', '}': '{', ']': '['}
            for char in code:
                if char in '({[':
                    stack.append(char)
                elif char in ')}]':
                    self.assertTrue(stack, f"Delimiteur fermant inattendu {char} dans {name}")
                    expected = pairs[char]
                    actual = stack.pop()
                    self.assertEqual(actual, expected, f"Delimiteur desequilibre dans {name}: attendu {expected}, obtenu {char}")
            self.assertFalse(stack, f"Delimiteurs non fermes dans {name}: {stack}")


if __name__ == "__main__":
    unittest.main()
