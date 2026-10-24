#!/usr/bin/env python3
"""AIR-PELOTON-1 : contrats de la sonde (journal seul) et lecteur diag_air_peloton."""

from __future__ import annotations

import gzip
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import diag_air_peloton as diag  # noqa: E402


def read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def body(src: str, header: str) -> str:
    start = src.index(header)
    brace = src.index("{", start)
    depth = 0
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
    raise AssertionError(header)


PELOTON_FUNCS = (
    "function OpexAirPelotonLog(",
    "function OpexAirPelotonOnDepart(",
    "function OpexAirPelotonMedian(",
    "function OpexAirPelotonFlushYear(",
)
RESERVED = ("clone", "base", "parent", "static", "delegate", "vargc", "vargv",
            "resume", "yield", "constructor", "instanceof")


class AirPelotonContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probes = read("probes.nut")
        cls.step = body(cls.probes, "function OpexC117AirThroughputStep(")
        cls.funcs = {h: body(cls.probes, h) for h in PELOTON_FUNCS}
        cls.all_peloton = "\n".join(cls.funcs.values())

    def test_calls_only_under_decision_log(self):
        self.assertIn("if (DECISION_LOG && nowYear != AIR_PELOTON_YEAR) "
                      "OpexAirPelotonFlushYear(nowYear);", self.step)
        guarded = re.search(r"if \(DECISION_LOG\) \{\s*OpexAirPelotonOnDepart\(", self.step)
        self.assertIsNotNone(guarded)
        self.assertEqual(self.step.count("OpexAirPelotonOnDepart("), 1)
        self.assertEqual(self.step.count("OpexAirPelotonFlushYear("), 1)

    def test_no_other_call_site(self):
        for path in AI.glob("*.nut"):
            text = path.read_text(encoding="utf-8")
            for name in ("OpexAirPelotonOnDepart(", "OpexAirPelotonFlushYear("):
                expected = 0
                if path.name == "probes.nut":
                    expected = 2  # definition + appel unique dans l'echantillonnage C117
                self.assertEqual(text.count(name), expected, (path.name, name))

    def test_hook_reuses_c117_transition(self):
        hook = self.step.index("OpexAirPelotonOnDepart(")
        # apres la cloture du leg C117 et avant la bascule d'ordre de l'etat vehicule
        self.assertLess(self.step.index("state.unobservedTransitions++"), hook)
        self.assertLess(hook, self.step.index("vehicleState.order = curOrder;\n        vehicleState.legPaxMax"))
        self.assertIn("vehicleState.order, now, load, cap", self.step)

    def test_state_is_telemetry_only(self):
        # aucune ecriture hors AIR_PELOTON_* ni appel mutateur dans les fonctions de la sonde
        for header, src in self.funcs.items():
            self.assertNotRegex(src, r"\bline\.[A-Za-z_]+\s*(=|<-)(?!=)", header)
            self.assertNotRegex(src, r"\bC117_[A-Z_]+\s*(=|<-|\.rawset)", header)
            self.assertNotRegex(src, r"vehicleState|\bstate\.", header)
            for token in ("BuildVehicle", "SellVehicle", "StartStopVehicle", "SendVehicleToDepot",
                          "AppendOrder", "SkipToOrder", "AIAccount", "Valuate"):
                self.assertNotIn(token, src, header)
        # l'etat AIR_PELOTON n'est lu nulle part ailleurs (aucune decision ne le consulte)
        for path in AI.glob("*.nut"):
            if path.name in ("probes.nut", "globals_pre.nut", "settings.nut"):
                continue
            self.assertNotIn("AIR_PELOTON", path.read_text(encoding="utf-8"), path.name)
        outside = self.probes
        for src in self.funcs.values():
            outside = outside.replace(src, "")
        outside = outside.replace("if (DECISION_LOG && nowYear != AIR_PELOTON_YEAR)", "")
        self.assertNotIn("AIR_PELOTON_LINE_STATE", outside)
        self.assertNotIn("AIR_PELOTON_YEAR", outside)

    def test_save_load_rebuilt_empty(self):
        self.assertIn("AIR_PELOTON_LINE_STATE <- {};", read("globals_pre.nut"))
        self.assertIn("AIR_PELOTON_YEAR <- -1;", read("globals_pre.nut"))
        settings = body(read("settings.nut"), "function OpexLoadSettings(")
        self.assertIn("AIR_PELOTON_LINE_STATE = {};", settings)
        self.assertIn("AIR_PELOTON_YEAR = -1;", settings)
        self.assertNotIn("AIR_PELOTON", read("persist.nut"))
        # premier passage apres chargement : annee -1 => aucune synthese, pas d'erreur
        flush = self.funcs["function OpexAirPelotonFlushYear("]
        self.assertIn("if (year < 0) return;", flush)
        # le depart tolere une ligne inconnue (etat cree a la volee)
        self.assertIn("if (ls == null)", self.funcs["function OpexAirPelotonOnDepart("])

    def test_squirrel_pitfalls(self):
        src = self.all_peloton
        self.assertNotIn(".find(", src)
        self.assertNotIn("function(", src)
        for word in RESERVED:
            self.assertIsNone(re.search(r"\blocal\s+" + word + r"\b", src), word)
            self.assertIsNone(re.search(r"[(,]\s*" + word + r"\s*[,)]", src), word)
        self.assertNotIn("const ", src)

    def test_summary_fields(self):
        flush = self.funcs["function OpexAirPelotonFlushYear("]
        for field in ("line=", " planes=", " departs=", " gap_med=", " gap_min=", " gap_cv=",
                      " load_med=", " load_first=", " load_second="):
            self.assertIn(field, flush)
        self.assertIn('"AIR_PELOTON"', flush)
        dep = self.funcs["function OpexAirPelotonOnDepart("]
        for field in ("line=", " stop=", " station=", " veh=", " load=", " cap=", " gap="):
            self.assertIn(field, dep)


SAMPLE = """\
dbg: [script] [1] [I] OPEX 1971-1-3 AIR_PELOTON_DEP line=7 stop=A station=3 veh=10 load=40 cap=100 load_pm=400 gap=-1 planes=2 run=1
dbg: [script] [1] [I] OPEX 1971-1-5 AIR_PELOTON_DEP line=7 stop=A station=3 veh=11 load=5 cap=100 load_pm=50 gap=2 planes=2 run=1
dbg: [script] [1] [I] OPEX 1971-1-25 AIR_PELOTON_DEP line=7 stop=A station=3 veh=10 load=60 cap=100 load_pm=600 gap=20 planes=2 run=1
dbg: [script] [1] [I] OPEX 1971-1-27 AIR_PELOTON_DEP line=7 stop=A station=3 veh=11 load=4 cap=100 load_pm=40 gap=2 planes=2 run=1
dbg: [script] [1] [I] OPEX 1971-2-20 AIR_PELOTON_DEP line=7 stop=A station=3 veh=10 load=55 cap=100 load_pm=550 gap=24 planes=2 run=1
dbg: [script] [1] [I] OPEX 1971-2-20 AIR_PELOTON_DEP line=9 stop=B station=5 veh=20 load=30 cap=60 load_pm=500 gap=-1 planes=1 run=1
dbg: [script] [1] [I] OPEX 1972-1-1 AIR_PELOTON line=7 year=1971 planes=2 planes_last=2 departs=5 gaps=4 gap_med=11 gap_min=2 gap_cv=0.84 load_med=400 load_first=575 load_second=45 n_first=2 n_second=2
dbg: [script] [1] [I] OPEX 1972-1-1 OTHER_EVENT x=1
"""


class DiagAirPeloton(unittest.TestCase):
    def test_parse(self):
        departs, summaries = diag.parse_log_lines(SAMPLE.splitlines(), source="s")
        self.assertEqual(len(departs), 6)
        self.assertEqual(len(summaries), 1)
        self.assertEqual(departs[1]["gap"], 2)
        self.assertEqual(departs[1]["stop"], "A")
        self.assertEqual(summaries[0]["gap_cv"], 0.84)

    def test_ranks_and_correlation(self):
        departs, summaries = diag.parse_log_lines(SAMPLE.splitlines(), source="s")
        report = diag.summarize(departs, summaries)
        # line 7 : gaps 2,20,2,24 -> mediane 11 ; court = gap*4 < 11 -> 2
        ranks = [d["rank"] for d in departs if d["line"] == 7]
        self.assertEqual(ranks, [None, 2, 1, 2, 1])
        self.assertEqual(report["load_by_rank"]["1"]["median"], 575.0)
        self.assertEqual(report["load_by_rank"]["2"]["median"], 45.0)
        corr = report["correlation"]
        self.assertGreater(corr["pearson_gap_load"], 0.9)
        self.assertEqual(corr["load_short_gap"]["n"], 2)
        self.assertEqual(corr["load_long_gap"]["n"], 2)
        self.assertIn("2", report["by_planes"])
        self.assertEqual(report["annual_by_planes"]["2"]["second_below_first"], 1)
        self.assertEqual(report["gap_distribution"]["2-3"]["n"], 2)
        self.assertEqual(report["departs_with_gap"], 4)

    def test_gz_and_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a" / "game.log.gz"
            p.parent.mkdir()
            with gzip.open(p, "wt", encoding="utf-8") as fh:
                fh.write(SAMPLE)
            (Path(tmp) / "b.log").write_text(SAMPLE, encoding="utf-8")
            report = diag.analyze_paths([tmp])
            self.assertEqual(report["files"], 2)
            self.assertEqual(report["departs"], 12)
            # rangs calcules par fichier : pas de melange entre journaux
            self.assertEqual(report["load_by_rank"]["2"]["n"], 4)

    def test_empty_returns_error_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "x.log").write_text("rien\n", encoding="utf-8")
            self.assertEqual(diag.main([tmp, "--out", str(Path(tmp) / "o.json")]), 1)


if __name__ == "__main__":
    unittest.main()
