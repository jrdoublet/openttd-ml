#!/usr/bin/env python3
"""Tests pour V161 — marge nette des renforts de flotte AIR à l'échelle des aéroports.

Couvre :
1. Contrats statiques : réglages (info.nut ↔ globals_pre.nut ↔ settings.nut), défaut 0,
   chaque point d'entrée gardé par V161_FLEET_NET_MARGINAL, exemption C70/C82 levée
   seulement pour un projet marqué v161Calibrate, champs de ligne scalaires ou tableaux.
2. Modèle Python des fonctions de air_fleet.nut : témoins de tendance, grappe, observation
   nette, régression de partie sur le nombre de voisines, choix de la valeur par avion.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


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


def _setting_block(name: str) -> str:
    info = _read("info.nut")
    start = info.index('name = "' + name + '"')
    return info[start:info.index("});", start)]


# --- Modèle Python de air_fleet.nut (V161) ---------------------------------------------

def report_line(line, year, st_a, st_b, profit, veh, trend):
    contiguous = line.get("v161RepYear") == year - 1
    if (contiguous and "v161P2" in line and line["v161V2"] == line["v161V1"]
            and line["v161V1"] == veh and veh > 0 and line["v161P2"] > 0
            and line.get("year", 10**9) <= year - 4 and not line.get("scrapping", False)):
        trend[0] += profit
        trend[1] += line["v161P2"]
        trend[2] += 1
    if contiguous and "v161P1" in line:
        line["v161P2"] = line["v161P1"]
        line["v161V2"] = line["v161V1"]
    else:
        line.pop("v161P2", None)
        line.pop("v161V2", None)
    line["v161P1"] = profit
    line["v161V1"] = veh
    line["v161RepYear"] = year
    line["v161StA"] = st_a if st_a is not None and st_a >= 0 else -1
    line["v161StB"] = st_b if st_b is not None and st_b >= 0 else -1


def shares_station(line, other):
    a, b = line["v161StA"], line["v161StB"]
    oa, ob = other["v161StA"], other["v161StB"]
    return (a >= 0 and (oa == a or ob == a)) or (b >= 0 and (oa == b or ob == b))


def cluster_snapshot(line, lines, year):
    if line.get("v161RepYear") != year or line.get("year", 10**9) > year - 2:
        return None
    ids = [line["lineId"]]
    profit = line["v161P1"]
    vehicles = line["v161V1"]
    young = touches = 0
    a, b = line["v161StA"], line["v161StB"]
    for other in lines:
        if other is line or other.get("mode") != "air":
            continue
        if other.get("v161RepYear") != year or other["v161V1"] <= 0:
            continue
        if other.get("scrapping", False) or not shares_station(line, other):
            continue
        if a >= 0 and (other["v161StA"] == a or other["v161StB"] == a):
            touches += 1
        if b >= 0 and b != a and (other["v161StA"] == b or other["v161StB"] == b):
            touches += 1
        if other.get("year", 10**9) > year - 2:
            young += 1
            continue
        ids.append(other["lineId"])
        profit += other["v161P1"]
        vehicles += other["v161V1"]
    return dict(ids=ids, profit=profit, vehicles=vehicles, young=young, neighbours=touches)


class Pool:
    def __init__(self):
        self.n = self.s = self.sx = self.sxx = self.sxy = 0

    def add(self, x, net):
        self.n += 1
        self.s += net
        self.sx += x
        self.sxx += x * x
        self.sxy += x * net

    def predict(self, neighbours):
        if self.n < 3:
            return None
        n = float(self.n)
        mean = self.s / n
        if self.n >= 8:
            mx = self.sx / n
            vxx = self.sxx / n - mx * mx
            if vxx > 0.25:
                slope = (self.sxy / n - mx * mean) / vxx
                slope = min(slope, 0.0)
                return int(mean + slope * (neighbours - mx))
        return int(mean)


def sq_div(a, b):
    """Division entière Squirrel (troncature vers zéro)."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def observe(line, by_id, g_pm, pool):
    after = veh_after = 0
    for i in line["v161ClusterIds"]:
        if i not in by_id:
            return None
        after += by_id[i]["v161P1"]
        veh_after += by_id[i]["v161V1"]
    added = veh_after - line["v161BaseVehicles"]
    if added <= 0:
        return None
    expected = int(line["v161BaseProfit"] * g_pm / 1000.0)
    net = sq_div(after - expected - line["v161AmortPerPlane"] * added, added)
    pool.add(line["v161Neighbours"], net)
    return net


def trend_pm(trend):
    if trend[2] >= 5 and trend[1] > 0:
        return max(750, min(1333, int(trend[0] * 1000.0 / trend[1])))
    return 1000


def per_plane(line, entry, model, pool, mode):
    neighbours = entry.get("v161Neighbours", 0)
    pred = pool.predict(neighbours)
    samples = line.get("v161NetSamples", 0)
    if samples > 0:
        value = (sq_div(line["v161NetAvg"] * samples + pred * 2, samples + 2)
                 if pred is not None else line["v161NetAvg"])
        return None if value <= 0 else (value, "line")
    value, source = model, "model"
    if pred is not None:
        if pred <= 0:
            return None
        if pred < value:
            value, source = pred, "pool"
    elif mode >= 2:
        prior = 13000 - 2600 * neighbours
        if prior <= 0:
            return None
        if prior < value:
            value, source = prior, "prior"
    return None if value <= 0 else (value, source)


class StaticContracts(unittest.TestCase):
    def test_settings_declared_with_default_off(self):
        block = _setting_block("v161_fleet_net_marginal")
        self.assertIn("min_value = 0, max_value = 2", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r" = 0\b")
        self.assertIn("custom_value = 13000", _setting_block("v161_prior_own"))
        self.assertIn("custom_value = 2600", _setting_block("v161_prior_neighbour"))
        globals_pre = _read("globals_pre.nut")
        self.assertIn("V161_FLEET_NET_MARGINAL <- 0;", globals_pre)
        self.assertIn("V161_PRIOR_OWN <- 13000;", globals_pre)
        self.assertIn("V161_PRIOR_NEIGHBOUR <- 2600;", globals_pre)
        settings = _read("settings.nut")
        for name, glob in (("v161_fleet_net_marginal", "V161_FLEET_NET_MARGINAL"),
                           ("v161_prior_own", "V161_PRIOR_OWN"),
                           ("v161_prior_neighbour", "V161_PRIOR_NEIGHBOUR")):
            m = re.search(r'local (\w+) = AIController\.GetSetting\("' + name + r'"\);\s*'
                          r'if \(\1 >= 0\) ' + glob + r' = \1;', settings)
            self.assertIsNotNone(m, name)
        self.assertIn("V161_POOL_N = 0;", settings)

    def test_every_hook_is_gated(self):
        report = _function_body(_read("task_report.nut"), "OpexAI::_reportLines")
        self.assertIn("local v161ById = V161_FLEET_NET_MARGINAL > 0 ? {} : null;", report)
        self.assertIn("if (v161ById != null && (\"mode\" in line) && line.mode == \"air\") {", report)
        self.assertIn("if (v161ById != null) OpexV161ObserveClusters(", report)
        # le releve V161 precede l'ecrasement de lastProfit, l'observation suit la boucle
        self.assertLess(report.index("OpexV161ReportLine("), report.index("line.lastProfit <- profit;"))
        self.assertGreater(report.index("OpexV161ObserveClusters("),
                           report.index("OpexUpdateAirLineHealth(line, year, anchor, profit);"))
        build = _function_body(_read("task_projects.nut"), "OpexAI::_tryBuildFleetProject")
        self.assertIn("if (V161_FLEET_NET_MARGINAL > 0 && added > 0) {\n"
                      "    OpexV161ArmObservation(line, this._lines, year, entry.planePrice);", build)
        resize = _function_body(_read("task_air.nut"), "OpexAI::_resizeAirFleets")
        self.assertIn("if (V161_FLEET_NET_MARGINAL > 0) {", resize)
        self.assertIn("fleetEntry.v161Neighbours <-", resize)
        builder = _function_body(_read("projects_builders.nut"), "OpexProjectFromFleet")
        self.assertIn("if (V161_FLEET_NET_MARGINAL > 0 && !c84BelowTarget) {", builder)
        self.assertIn("if (v161Source != null) {", builder)
        self.assertIn("project.v161Calibrate <- true;", builder)

    def test_calibration_exemption_lifted_only_for_v161_projects(self):
        models = _read("projects_models.nut")
        for fn in ("OpexC70Profit", "OpexC82Profit"):
            body = _function_body(models, fn)
            self.assertIn('project.mode == "fleet"\n      && !("v161Calibrate" in project)\n'
                          "      && OpexC121ProjectHasRealization(project)) return project.profitAnnual;",
                          body, fn)
            # une valeur observee (ligne, partie, a priori) reste brute
            self.assertLess(body.index("profitIsObserved"), body.index("v161Calibrate"))
        builder = _function_body(_read("projects_builders.nut"), "OpexProjectFromFleet")
        self.assertIn('profitIsObserved = v161Source != "model";', builder)

    def test_line_fields_are_save_safe(self):
        fleet = _read("air_fleet.nut")
        v161 = fleet[fleet.index("/* V161 : marge nette d'un renfort AIR"):]
        assigned = set(re.findall(r"line\.(v161\w+) <-", v161))
        self.assertEqual(assigned, {
            "v161P1", "v161P2", "v161V1", "v161V2", "v161RepYear", "v161StA", "v161StB",
            "v161ClusterIds", "v161BaseProfit", "v161BaseVehicles", "v161Neighbours",
            "v161AmortPerPlane", "v161ObserveYear", "v161NetAvg", "v161NetLast",
            "v161NetSamples"})
        # amortissement force en entier : aucun flottant n'entre dans les cumuls de ligne
        self.assertIn("line.c121VehicleAmortPerPlane.tointeger() : 0;", v161)
        self.assertNotIn(".tofloat()", _function_body(fleet, "OpexV161ArmObservation"))

    def test_no_reserved_identifiers(self):
        fleet = _read("air_fleet.nut")
        v161 = fleet[fleet.index("/* V161 : marge nette d'un renfort AIR"):]
        code = re.sub(r"/\*.*?\*/", "", v161, flags=re.S)
        for word in ("clone", "base", "parent"):
            self.assertIsNone(re.search(r"\b(local|function)\s+" + word + r"\b", code), word)
            self.assertIsNone(re.search(r"\(\s*" + word + r"\s*[,)]", code), word)

    def test_decision_log_events_gated(self):
        fleet = _read("air_fleet.nut")
        v161 = fleet[fleet.index("/* V161 : marge nette d'un renfort AIR"):]
        for m in re.finditer(r"OpexDecide\(", v161):
            prefix = v161[max(0, m.start() - 20):m.start()]
            self.assertIn("if (DECISION_LOG)", prefix)


class TrendAndCluster(unittest.TestCase):
    def _line(self, lid, built, a, b):
        return {"lineId": lid, "mode": "air", "year": built, "_a": a, "_b": b}

    def test_trend_controls_need_three_equal_reports_and_full_year(self):
        old = self._line(1, 1970, 10, 11)
        young = self._line(2, 1972, 10, 12)
        grown = self._line(3, 1970, 13, 14)
        trend = [0, 0, 0]
        for year, profits, vehs in ((1972, (100, 50, 80), (2, 2, 2)),
                                    (1973, (110, 60, 90), (2, 2, 3)),
                                    (1974, (120, 70, 150), (2, 2, 3))):
            trend = [0, 0, 0]
            for line, p, v in zip((old, young, grown), profits, vehs):
                report_line(line, year, line["_a"], line["_b"], p, v, trend)
        # seul old : flotte stable sur 3 releves et annee 1971 pleine (construite <= 1970)
        self.assertEqual(trend, [120, 100, 1])
        self.assertEqual(trend_pm(trend), 1000)  # moins de 5 temoins
        self.assertEqual(trend_pm([1300, 1000, 5]), 1300)
        self.assertEqual(trend_pm([2000, 1000, 5]), 1333)
        self.assertEqual(trend_pm([500, 1000, 5]), 750)

    def test_gap_in_reports_resets_shift_register(self):
        line = self._line(1, 1970, 1, 2)
        trend = [0, 0, 0]
        report_line(line, 1972, 1, 2, 10, 1, trend)
        report_line(line, 1973, 1, 2, 10, 1, trend)
        report_line(line, 1975, 1, 2, 10, 1, trend)
        self.assertNotIn("v161P2", line)

    def test_cluster_excludes_young_and_counts_touches_like_routes_index(self):
        year = 1973
        lines = [self._line(1, 1970, 10, 11), self._line(2, 1971, 10, 20),
                 self._line(3, 1972, 11, 21), self._line(4, 1970, 10, 11),
                 self._line(5, 1970, 30, 31), {"lineId": 6, "mode": "road", "year": 1970}]
        trend = [0, 0, 0]
        for i, line in enumerate(lines[:5]):
            report_line(line, year, line["_a"], line["_b"], 1000 * (i + 1), i + 1, trend)
        snap = cluster_snapshot(lines[0], lines, year)
        self.assertEqual(snap["ids"], [1, 2, 4])          # 3 trop jeune, 5 sans gare commune
        self.assertEqual(snap["young"], 1)
        self.assertEqual(snap["profit"], 1000 + 2000 + 4000)
        self.assertEqual(snap["vehicles"], 1 + 2 + 4)
        self.assertEqual(snap["neighbours"], 4)            # 2 (A) + 3 (B) + 4 (A et B)
        self.assertIsNone(cluster_snapshot(lines[2], lines, year))  # ligne d'un an
        self.assertIsNone(cluster_snapshot(lines[0], lines, year + 1))  # releve pas fait


class ObservationAndScoring(unittest.TestCase):
    def _armed(self, ids, base_profit, base_veh, neighbours, amort=0):
        return {"lineId": ids[0], "v161ClusterIds": ids, "v161BaseProfit": base_profit,
                "v161BaseVehicles": base_veh, "v161Neighbours": neighbours,
                "v161AmortPerPlane": amort}

    def test_net_counts_neighbour_losses_and_trend(self):
        pool = Pool()
        line = self._armed([1, 2, 3], 300_000, 6, 2, amort=2000)
        by_id = {1: {"v161P1": 140_000, "v161V1": 3}, 2: {"v161P1": 95_000, "v161V1": 2},
                 3: {"v161P1": 90_000, "v161V1": 2}}
        # la ligne gagne +40 k, les voisines perdent -5 k et -10 k ; tendance +5 %
        net = observe(line, by_id, 1050, pool)
        self.assertEqual(net, (325_000 - 315_000 - 2000) // 1)
        self.assertEqual(pool.n, 1)

    def test_vanished_member_or_no_growth_drops_observation(self):
        pool = Pool()
        line = self._armed([1, 2], 100, 2, 1)
        self.assertIsNone(observe(line, {1: {"v161P1": 1, "v161V1": 2}}, 1000, pool))
        self.assertIsNone(observe(line, {1: {"v161P1": 1, "v161V1": 1},
                                         2: {"v161P1": 1, "v161V1": 1}}, 1000, pool))
        self.assertEqual(pool.n, 0)

    def test_pool_regression_on_neighbours(self):
        pool = Pool()
        self.assertIsNone(pool.predict(0))
        for x, net in ((0, 13000), (0, 13400), (2, 8000)):
            pool.add(x, net)
        self.assertEqual(pool.predict(5), int((13000 + 13400 + 8000) / 3))  # moyenne sous 8
        for x in (1, 2, 3, 4, 5):
            pool.add(x, 13000 - 2600 * x)
        self.assertAlmostEqual(pool.predict(0), 13000, delta=600)
        self.assertAlmostEqual(pool.predict(4), 13000 - 2600 * 4, delta=600)
        # une pente positive (bruit) est ramenee a zero : moyenne pour tous
        flat = Pool()
        for x, net in ((0, 1000), (1, 2000), (2, 3000), (3, 4000)) * 2:
            flat.add(x, net)
        self.assertEqual(flat.predict(0), flat.predict(3))

    def test_per_plane_value_selection(self):
        empty = Pool()
        line = {}
        # mode 1 sans observation : valeur du modele (calibree C70 ensuite)
        self.assertEqual(per_plane(line, {"v161Neighbours": 4}, 39000, empty, 1), (39000, "model"))
        # mode 2 : a priori 13 000 - 2 600 x voisines
        self.assertEqual(per_plane(line, {"v161Neighbours": 4}, 39000, empty, 2), (2600, "prior"))
        self.assertIsNone(per_plane(line, {"v161Neighbours": 5}, 39000, empty, 2))
        self.assertEqual(per_plane(line, {"v161Neighbours": 0}, 9000, empty, 2), (9000, "model"))
        pool = Pool()
        for net in (3000, 3500, 2500):
            pool.add(3, net)
        self.assertEqual(per_plane(line, {"v161Neighbours": 3}, 39000, pool, 1), (3000, "pool"))
        self.assertEqual(per_plane(line, {"v161Neighbours": 3}, 2000, pool, 1), (2000, "model"))
        neg = Pool()
        for net in (-3000, -1000, -2000):
            neg.add(3, net)
        self.assertIsNone(per_plane(line, {}, 39000, neg, 1))
        # ligne observee : retrecie vers la partie (poids 2)
        observed = {"v161NetSamples": 1, "v161NetAvg": 12000}
        self.assertEqual(per_plane(observed, {"v161Neighbours": 3}, 39000, pool, 1),
                         ((12000 + 3000 * 2) // 3, "line"))
        bad = {"v161NetSamples": 1, "v161NetAvg": -9000}
        self.assertIsNone(per_plane(bad, {"v161Neighbours": 3}, 39000, pool, 1))

    def test_model_mirrors_squirrel_source(self):
        fleet = _read("air_fleet.nut")
        pred = _function_body(fleet, "OpexV161PoolPredict")
        self.assertIn("if (V161_POOL_N < 3) return null;", pred)
        self.assertIn("if (V161_POOL_N >= 8) {", pred)
        self.assertIn("if (vxx > 0.25) {", pred)
        self.assertIn("if (slope > 0.0) slope = 0.0;", pred)
        per = _function_body(fleet, "OpexV161PerPlaneProfit")
        self.assertIn("(line.v161NetAvg * samples + pool * 2) / (samples + 2)", per)
        self.assertIn("local prior = V161_PRIOR_OWN - V161_PRIOR_NEIGHBOUR * neighbours;", per)
        self.assertIn("} else if (V161_FLEET_NET_MARGINAL >= 2) {", per)
        obs = _function_body(fleet, "OpexV161ObserveClusters")
        self.assertIn("if (trend[2] >= 5 && trend[1] > 0) {", obs)
        self.assertIn("if (gPm < 750) gPm = 750;", obs)
        self.assertIn("if (gPm > 1333) gPm = 1333;", obs)
        self.assertIn("local net = (after - expected - line.v161AmortPerPlane * added) / added;", obs)
        rep = _function_body(fleet, "OpexV161ReportLine")
        self.assertIn("&& (\"year\" in line) && line.year <= year - 4", rep)
        snap = _function_body(fleet, "OpexV161ClusterSnapshot")
        self.assertIn("if (!(\"year\" in line) || line.year > year - 2) return null;", snap)


if __name__ == "__main__":
    unittest.main()
