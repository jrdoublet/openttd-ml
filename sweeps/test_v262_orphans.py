"""V262 T10/T15 : contrats de la sonde passive des infrastructures orphelines.

Sous DECISION_LOG seulement, une fois par an au 1er decembre. Aucune demolition,
aucun nouveau reglage, aucun cout « orphelin » invente. Le releve n'est pas
persiste.
"""
from pathlib import Path
import gzip
import re
import tempfile
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
MODULE = AI / "probe_v262_orphans.nut"
TYPES = ("train", "truck", "bus", "airport", "dock")
INFRA = ("rail", "signals", "road", "canal", "station", "airport")


class TestV262Orphans(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = MODULE.read_text(encoding="utf-8")
        cls.sources = {p.name: p.read_text(encoding="utf-8")
                       for p in AI.glob("*.nut")}

    def test_single_guarded_hook(self):
        hooks = [(n, l) for n, t in self.sources.items() if n != MODULE.name
                 for l in t.splitlines() if "OpexV262OrphanSurvey(" in l]
        self.assertEqual(hooks, [("scheduler.nut",
                                  "  if (DECISION_LOG) OpexV262OrphanSurvey(this._lines);")])
        self.assertIn('require("probe_v262_orphans.nut");', self.sources["main.nut"])
        main = self.sources["main.nut"]
        self.assertLess(main.index('require("probes.nut");'),
                        main.index('require("probe_v262_orphans.nut");'))
        self.assertLess(main.index('require("probe_v262_orphans.nut");'),
                        main.index('require("scheduler.nut");'))

    def test_december_first_once_per_year_before_any_walk(self):
        survey = self.module.split("function OpexV262OrphanSurvey(lines)", 1)[1]
        self.assertIn("if (!DECISION_LOG) return;", survey)
        self.assertLess(survey.index("if (now == V262_ORPHAN_DATE) return;"),
                        survey.index("AIDate.GetMonth(now) != 12"))
        self.assertIn("AIDate.GetMonth(now) != 12 || AIDate.GetDayOfMonth(now) != 1", survey)
        self.assertLess(survey.index("AIDate.GetDayOfMonth(now) != 1"),
                        survey.index('GetValue("economy.timekeeping_units")'))
        self.assertLess(survey.index("if (year == V262_ORPHAN_YEAR) return;"),
                        survey.index("AIStationList("))
        self.assertIn("V262_ORPHAN_YEAR <- -1;", self.sources["globals_pre.nut"])
        self.assertIn("V262_ORPHAN_DATE <- -1;", self.sources["globals_pre.nut"])

    def test_settings_read_once_per_survey(self):
        self.assertEqual(self.module.count('GetValue("economy.timekeeping_units")'), 1)
        self.assertEqual(self.module.count('GetValue("economy.infrastructure_maintenance")'), 1)
        self.assertEqual(self.module.count("AIGameSettings.GetValue("), 2)

    def test_counts_stations_depots_and_maintenance_without_an_orphan_share(self):
        for name in TYPES:
            self.assertIn('["' + name + '"', self.module)
        self.assertIn("AIVehicleList_Station(st).Count() == 0", self.module)
        self.assertIn("AIBaseStation.GetConstructionDate(station)", self.module)
        self.assertIn("timekeeping != 0", self.module)
        for transport in ("TRANSPORT_RAIL", "TRANSPORT_ROAD", "TRANSPORT_WATER", "TRANSPORT_AIR"):
            self.assertIn("AITile." + transport, self.module)
        self.assertIn("AIVehicleList_Depot(tile).Count() == 0", self.module)
        self.assertIn("hangar_empty=", self.module)
        self.assertNotIn("depot_air", self.module)
        for name, enum in (
            ("rail", "INFRASTRUCTURE_RAIL"),
            ("signals", "INFRASTRUCTURE_SIGNALS"),
            ("road", "INFRASTRUCTURE_ROAD"),
            ("canal", "INFRASTRUCTURE_CANAL"),
            ("station", "INFRASTRUCTURE_STATION"),
            ("airport", "INFRASTRUCTURE_AIRPORT"),
        ):
            self.assertIn('["' + name + '", AIInfrastructure.' + enum + "]", self.module)
        self.assertIn("GetInfrastructurePieceCount(company, row[1])", self.module)
        self.assertIn("GetMonthlyInfrastructureCosts(company, row[1])", self.module)
        self.assertNotIn("orphan_cost", self.module)
        self.assertNotIn("cost_orphan", self.module)
        for field in ("stationA", "stationB", "stationA2", "stationB2"):
            self.assertIn('"' + field + '"', self.module)

    def test_never_commands_or_persists(self):
        code = re.sub(r"/\*.*?\*/", "", self.module, flags=re.S)
        calls = set(re.findall(r"\bAI\w+\.(\w+)\(", code))
        forbidden = [c for c in calls
                     if re.match(r"(Build|Remove|Demolish|Set|Sell|Clone|Start|Stop|Skip|Send|"
                                 r"Append|Insert|Delete|Change|Refit|Found|Fund|Buy|Pay)", c)]
        self.assertEqual(forbidden, [])
        self.assertNotIn("V262_ORPHAN", self.sources["persist.nut"])
        self.assertNotIn("v262_orphan", self.sources["info.nut"])
        for name, text in self.sources.items():
            if name in (MODULE.name, "globals_pre.nut", "scheduler.nut"):
                continue
            self.assertNotIn("V262_ORPHAN_YEAR", text, name)
            self.assertNotIn("V262_ORPHAN_DATE", text, name)


class TestAnalyzeV262Orphans(unittest.TestCase):
    def test_groups_by_seed_and_year_and_sums_maintenance(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import analyze_v262_orphans as a
        self.assertNotIn("orphan_cost", Path(a.__file__).read_text(encoding="utf-8"))
        pre = "[t] dbg: [script:4] [0] [I] OPEX "
        station = (pre + "1972-12-1 V262_ORPHAN_STATION station=4 train=1 truck=1 bus=0 "
                   "airport=0 dock=0 age=400 built=100 in_lines=0\n"
                   + pre + "1972-12-1 V262_ORPHAN_STATION station=9 train=0 truck=0 bus=1 "
                   "airport=0 dock=0 age=-1 built=-1 in_lines=1\n"
                   + pre + "1972-12-1 V262_ORPHAN_STATION station=4 train=1 truck=0 bus=0 "
                   "airport=0 dock=0 age=401 built=100 in_lines=0\n")
        costs = " ".join(f"cost_{name}={i + 1}" for i, name in enumerate(INFRA))
        pieces = " ".join(f"pieces_{name}=10" for name in INFRA)
        summary = (pre + "1972-12-1 V262_ORPHAN_SUM year=1972 timekeeping=0 maint=1 "
                   "stations_train=3 stations_truck=1 stations_bus=2 stations_airport=0 "
                   "stations_dock=0 orphan_train=1 orphan_truck=0 orphan_bus=1 "
                   "orphan_airport=0 orphan_dock=0 orphan_n=2 "
                   "depot_rail_empty=1 depot_rail_n=2 depot_road_empty=0 depot_road_n=1 "
                   "depot_water_empty=0 depot_water_n=0 hangar_empty=1 hangar_n=1 "
                   "depot_empty=1 depot_n=3 " + pieces + " " + costs + "\n")
        later = (pre + "1973-12-1 V262_ORPHAN_SUM year=1973 timekeeping=0 maint=0 "
                 "orphan_n=0 " + " ".join(f"cost_{name}=0" for name in INFRA) + "\n")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "b1_seed42_r0.log"
            first.write_text(station + summary + later + "noise\n", encoding="utf-8")
            second = root / "b1_seed7_r0.log.gz"
            with gzip.open(second, "wt", encoding="utf-8") as fh:
                fh.write(pre + "1974-12-1 V262_ORPHAN_STATION station=3 train=0 truck=0 "
                         "bus=0 airport=1 dock=1 age=10 built=20 in_lines=0\n")
                fh.write(pre + "1974-12-1 V262_ORPHAN_SUM year=1974 timekeeping=1 maint=0 "
                         "orphan_n=1 " + " ".join(f"cost_{name}=0" for name in INFRA) + "\n")
            grouped = a.games_by_seed(a.log_paths(str(root)))
        self.assertEqual(set(grouped), {42, 7})
        years = grouped[42][0][1]
        self.assertEqual(sorted(years), [1972, 1973])
        self.assertEqual(a.orphans_by_type(years[1972]),
                         {"train": 1, "truck": 0, "bus": 1, "airport": 0, "dock": 0})
        self.assertEqual(years[1972]["stations"][4]["age"], 401)
        self.assertEqual(a.total_maintenance(years[1972]["sum"]), sum(range(1, 7)))
        self.assertEqual(a.total_maintenance(years[1973]["sum"]), 0)
        self.assertIsNone(a.total_maintenance(None))
        seed7 = grouped[7][0][1][1974]
        self.assertEqual(a.orphans_by_type(seed7),
                         {"train": 0, "truck": 0, "bus": 0, "airport": 1, "dock": 1})
        self.assertEqual(a.total_maintenance(seed7["sum"]), 0)


if __name__ == "__main__":
    unittest.main()
