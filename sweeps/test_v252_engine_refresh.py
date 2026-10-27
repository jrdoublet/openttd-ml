"""V252 : contrats statiques de la modernisation de la flotte aerienne.

Mode 2 fige par V263b : meilleur avion sur renfort/crash et remplacement
actif mensuel quand riche, sans montant fixe en livres.
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _body(source, signature):
    match = re.search(re.escape(signature) + r"\n\{(.*?)\n\}", source, re.S)
    return match.group(1) if match else ""


class TestV252EngineRefresh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.task = cls.sources["task_v252.nut"]
        cls.dispatch = _body(cls.task, "function OpexAI::_dispatchV252AirEngineRefresh(task, year)")
        cls.fleet = cls.sources["air_fleet.nut"]
        cls.add_plane = _body(cls.fleet, "function OpexAirAddPlane(line, catalog = null, lines = null)")
        cls.refleet = _body(cls.fleet, "function OpexAirRefleetCrashedPlane(line, catalog = null)")

    def test_setting_frozen_at_two(self):
        # V263 : mode 2 qualifie (portes A et B du 18/10), fige ; reglage retire.
        for name, text in self.sources.items():
            self.assertNotIn('GetSetting("v252_air_engine_refresh")', text, name)
            self.assertNotIn("V252_AIR_ENGINE_REFRESH", text, name)
        self.assertNotIn('name = "v252_air_engine_refresh"', self.sources["info.nut"])
        self.assertIn("V252_CASH_STOP <- true;", self.sources["globals_pre.nut"])

    def test_always_on(self):
        start = self.sources["main.nut"]
        appended = 'this._taskQueue.append({ name = "v252_air_engine_refresh", dueCycle = 0, enabled = true });'
        self.assertIn(appended, start)
        sched = self.sources["scheduler.nut"]
        self.assertIn('if (task.name == "v252_air_engine_refresh")', sched)
        self.assertIn("if (catalog != null) {", self.add_plane)
        self.assertIn("if (catalog != null) {", self.refleet)
        hook_v249 = 'if (V249_STATUE && c75StopReason == "cash") ::V249_CASH_STOP = true;'
        hook_v252 = 'if (c75StopReason == "cash") ::V252_CASH_STOP = true;'
        self.assertEqual(self.sources["task_projects.nut"].count(hook_v249), 1)
        self.assertEqual(self.sources["task_projects.nut"].count(hook_v252), 1)

    def test_rich_without_fixed_amount(self):
        loan = self.dispatch.index('reason=loan')
        stop = self.dispatch.index('reason=cash_stop')
        cost = self.dispatch.index('AIEngine.GetPrice(bestNewEngine)')
        self.assertLess(loan, cost)
        self.assertLess(stop, cost)
        self.assertLess(self.dispatch.index("::V252_CASH_STOP = false;"), stop)
        self.assertIn("local threshold = OpexV249MaxListedCapital(this._projects);",
                      self.dispatch)
        self.assertIn("cash - price < threshold", self.dispatch)
        # Aucun nombre a 4 chiffres ou plus dans task_v252.nut
        self.assertNotRegex(self.task, r"\b\d{4,}\b")

    def test_at_most_one_replacement_per_pass(self):
        self.assertEqual(self.dispatch.count("AIVehicle.BuildVehicleWithRefit"), 1)
        self.assertIn("AIVehicle.SendVehicleToDepot", self.dispatch)
        self.assertIn("this._vehiclesToRetire", self.dispatch)
        self.assertIn("if (this._v252RefreshMonth == ym) return false;", self.dispatch)

    def test_journal_guarded(self):
        for line in self.task.splitlines():
            if "OpexDecide(" in line:
                self.assertIn("DECISION_LOG", line, line)
        self.assertIn('OpexDecide("V252_REPLACE"', self.dispatch)
        self.assertIn('OpexDecide("V252_SKIP"', self.dispatch)

        for line in self.fleet.splitlines():
            if 'OpexDecide("V252_ENGINE"' in line:
                self.assertIn("DECISION_LOG", line, line)

    def test_air_reinforcement_failed_orders_never_validate_null_vehicle(self):
        """Regression seed 123456, 1971-08-04: IsValidVehicle(null) crashed OpexAI."""
        self.assertIn("local extra = -1;", self.add_plane)
        self.assertNotIn("extra = null;", self.add_plane)
        fail = self.add_plane.index("!AIOrder.ShareOrders(extra, template) && !AIOrder.CopyOrders(extra, template)")
        fallback = self.add_plane.index("extra = AIVehicle.CloneVehicle(hangar, template, true);", fail)
        segment = self.add_plane[fail:fallback]
        self.assertIn("AIVehicle.SellVehicle(extra);", segment)
        self.assertIn("extra = -1;", segment)
        self.assertIn("if (extra == null || !AIVehicle.IsValidVehicle(extra))", segment)
        self.assertIn("targetEngine = oldEngine;", segment)
        self.assertIn("price = AIEngine.GetPrice(oldEngine);", segment)
        # Validate all remaining IsValidVehicle(extra) calls only after a null guard.
        checks = re.findall(r"if \(([^\n]*AIVehicle\.IsValidVehicle\(extra\)[^\n]*)\)", self.add_plane)
        self.assertEqual(len(checks), 5)
        self.assertTrue(all("extra == null ||" in check or "extra != null &&" in check for check in checks))

    def test_no_saved_state(self):
        persist = self.sources["persist.nut"]
        self.assertNotIn("v252", persist.lower())
        self.assertNotIn("_v252RefreshMonth", persist)
        self.assertNotIn("V252_CASH_STOP", persist)
        self.assertIn("_v252RefreshMonth = -1;", self.sources["main.nut"])

    def test_v252_optimized_selection_contracts(self):
        # 1. Collecte des candidats avec filtres
        self.assertIn("local candidates = [];", self.dispatch)
        self.assertIn("local rank = 0;", self.dispatch)
        self.assertIn('line.mode != "air"', self.dispatch)
        self.assertIn("line.scrapping", self.dispatch)
        self.assertIn("lineProfit <= 0", self.dispatch)
        self.assertIn("AIVehicle.IsValidVehicle(v)", self.dispatch)
        self.assertIn("this._vehiclesToRetire", self.dispatch)
        self.assertIn("rank = rank++", self.dispatch)

        # 2. Ordre de tri : age decroissant, profit croissant, rang croissant
        self.assertIn("candidates.sort(function(a, b)", self.dispatch)
        self.assertIn("if (a.age != b.age) return a.age > b.age ? -1 : 1;", self.dispatch)
        self.assertIn("if (a.profit != b.profit) return a.profit < b.profit ? -1 : 1;", self.dispatch)
        self.assertIn("if (a.rank != b.rank) return a.rank < b.rank ? -1 : 1;", self.dispatch)

        # 3. Cache par ligne pour le chooser : au plus un appel par ligne
        self.assertIn("local lineTargetCache = {};", self.dispatch)
        self.assertIn("!(lineKey in lineTargetCache)", self.dispatch)
        self.assertIn("lineTargetCache[lineKey] <-", self.dispatch)
        self.assertIn("OpexAirBestEngineForLine(cand.line, this._catalog)", self.dispatch)

        # 4. Arret immediat au premier candidat retenu
        self.assertIn("bestNewEngine = targetEngine;", self.dispatch)
        self.assertIn("break;", self.dispatch)
        idx_assign = self.dispatch.index("bestVeh = cand.veh;")
        idx_break = self.dispatch.index("break;", idx_assign)
        self.assertGreater(idx_break, idx_assign)

        # 5. Pas d'appel au chooser avant le tri des candidats
        pos_sort = self.dispatch.index("candidates.sort(")
        pos_chooser = self.dispatch.index("OpexAirBestEngineForLine(")
        self.assertGreater(pos_chooser, pos_sort)


    def test_v252_selection_simulation_and_budget(self):
        import random

        def run_legacy(lines, chooser_map):
            bestLine = None
            bestVeh = -1
            bestAge = -1
            bestProfit = 0
            bestNewEngine = -1
            curEngine = -1
            nOutdated = 0
            chooser_calls = 0

            for line in lines:
                if line.get("mode") != "air":
                    continue
                if not line.get("vehicles"):
                    continue
                if line.get("scrapping"):
                    continue
                lineProfit = sum(v["profit"] for v in line["vehicles"] if v.get("valid", True))
                if lineProfit <= 0:
                    continue

                chooser_calls += 1
                targetEngine = chooser_map.get(line["lineId"])
                if targetEngine is None:
                    continue

                for v in line["vehicles"]:
                    if not v.get("valid", True):
                        continue
                    if v.get("retire"):
                        continue
                    e = v["engine"]
                    if e == targetEngine:
                        continue
                    nOutdated += 1
                    age = v["age"]
                    prof = v["profit"]
                    if bestVeh < 0 or age > bestAge or (age == bestAge and prof < bestProfit):
                        bestLine = line
                        bestVeh = v["id"]
                        bestAge = age
                        bestProfit = prof
                        bestNewEngine = targetEngine
                        curEngine = e

            return {
                "veh": bestVeh, "line": bestLine["lineId"] if bestLine else None,
                "age": bestAge, "profit": bestProfit, "engine": bestNewEngine,
                "cur": curEngine, "outdated": nOutdated, "calls": chooser_calls
            }

        def run_optimized(lines, chooser_map):
            candidates = []
            rank = 0
            for line in lines:
                if line.get("mode") != "air":
                    continue
                if not line.get("vehicles"):
                    continue
                if line.get("scrapping"):
                    continue
                lineProfit = sum(v["profit"] for v in line["vehicles"] if v.get("valid", True))
                if lineProfit <= 0:
                    continue

                for v in line["vehicles"]:
                    if not v.get("valid", True):
                        continue
                    if v.get("retire"):
                        continue
                    candidates.append({
                        "veh": v["id"],
                        "line": line,
                        "age": v["age"],
                        "profit": v["profit"],
                        "engine": v["engine"],
                        "rank": rank
                    })
                    rank += 1

            candidates.sort(key=lambda c: (-c["age"], c["profit"], c["rank"]))

            lineTargetCache = {}
            chooser_calls = 0
            bestLine = None
            bestVeh = -1
            bestAge = -1
            bestProfit = 0
            bestNewEngine = -1
            curEngine = -1
            nOutdated = 0

            for cand in candidates:
                lineKey = cand["line"]["lineId"]
                if lineKey not in lineTargetCache:
                    chooser_calls += 1
                    lineTargetCache[lineKey] = chooser_map.get(lineKey)

                targetEngine = lineTargetCache[lineKey]
                if targetEngine is None:
                    continue
                if cand["engine"] == targetEngine:
                    continue

                nOutdated = 1
                bestLine = cand["line"]
                bestVeh = cand["veh"]
                bestAge = cand["age"]
                bestProfit = cand["profit"]
                bestNewEngine = targetEngine
                curEngine = cand["engine"]
                break

            return {
                "veh": bestVeh, "line": bestLine["lineId"] if bestLine else None,
                "age": bestAge, "profit": bestProfit, "engine": bestNewEngine,
                "cur": curEngine, "outdated": nOutdated, "calls": chooser_calls
            }

        # Scenario 1 : top candidat perime -> 1 seul appel au chooser
        lines = [
            {"lineId": 1, "mode": "air", "vehicles": [{"id": 10, "engine": 1, "age": 5, "profit": 100}]},
            {"lineId": 2, "mode": "air", "vehicles": [{"id": 20, "engine": 1, "age": 10, "profit": 200}]},
            {"lineId": 3, "mode": "air", "vehicles": [{"id": 30, "engine": 1, "age": 3, "profit": 50}]},
        ]
        chooser = {1: 2, 2: 2, 3: 2}
        leg = run_legacy(lines, chooser)
        opt = run_optimized(lines, chooser)
        self.assertEqual(leg["veh"], 20)
        self.assertEqual(opt["veh"], 20)
        self.assertEqual(leg["veh"], opt["veh"])
        self.assertEqual(leg["line"], opt["line"])
        self.assertEqual(leg["engine"], opt["engine"])
        self.assertEqual(leg["calls"], 3)
        self.assertEqual(opt["calls"], 1)

        # Scenario 2 : plusieurs avions sur meme ligne -> au plus 1 appel pour cette ligne
        lines = [
            {"lineId": 1, "mode": "air", "vehicles": [
                {"id": 11, "engine": 2, "age": 12, "profit": 300},
                {"id": 12, "engine": 1, "age": 8, "profit": 200},
            ]},
            {"lineId": 2, "mode": "air", "vehicles": [
                {"id": 21, "engine": 2, "age": 10, "profit": 250},
            ]}
        ]
        chooser = {1: 2, 2: 2}
        leg = run_legacy(lines, chooser)
        opt = run_optimized(lines, chooser)
        self.assertEqual(leg["veh"], 12)
        self.assertEqual(opt["veh"], 12)
        self.assertLessEqual(opt["calls"], 2)

        # Scenario 3 : egalite d'age et de profit -> premier rencontre gagne (rank)
        lines = [
            {"lineId": 1, "mode": "air", "vehicles": [{"id": 10, "engine": 1, "age": 8, "profit": 150}]},
            {"lineId": 2, "mode": "air", "vehicles": [{"id": 20, "engine": 1, "age": 8, "profit": 150}]},
        ]
        chooser = {1: 2, 2: 2}
        leg = run_legacy(lines, chooser)
        opt = run_optimized(lines, chooser)
        self.assertEqual(leg["veh"], 10)
        self.assertEqual(opt["veh"], 10)

        # Scenario 4 : 500 configurations aleatoires (fuzz test)
        rng = random.Random(42)
        for _ in range(500):
            n_lines = rng.randint(1, 10)
            rand_lines = []
            rand_chooser = {}
            veh_id = 1
            for l_idx in range(n_lines):
                lid = l_idx + 1
                n_vehs = rng.randint(0, 4)
                vehs = []
                for _ in range(n_vehs):
                    vehs.append({
                        "id": veh_id,
                        "engine": rng.randint(1, 4),
                        "age": rng.randint(0, 20),
                        "profit": rng.randint(-50, 500),
                        "valid": rng.random() > 0.1,
                        "retire": rng.random() > 0.9,
                    })
                    veh_id += 1
                rand_lines.append({
                    "lineId": lid,
                    "mode": "air" if rng.random() > 0.2 else "road",
                    "vehicles": vehs,
                    "scrapping": rng.random() > 0.9,
                })
                rand_chooser[lid] = rng.randint(1, 4) if rng.random() > 0.2 else None

            res_leg = run_legacy(rand_lines, rand_chooser)
            res_opt = run_optimized(rand_lines, rand_chooser)
            self.assertEqual(res_leg["veh"], res_opt["veh"])
            self.assertEqual(res_leg["line"], res_opt["line"])
            self.assertEqual(res_leg["engine"], res_opt["engine"])
            self.assertLessEqual(res_opt["calls"], res_leg["calls"])


if __name__ == "__main__":
    unittest.main()
