"""V257 : consist de sauvegarde, journal LINE_FLEET et BuildTrain AAAHogEx."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from bench_1v1_5y_20seeds import (  # noqa: E402
    build_line_telemetry_report,
    extract_line_telemetry,
    keep,
)
import bench_1v1_5y_20seeds as bench  # noqa: E402
from campaign_freeze import parse_ai_settings  # noqa: E402
from line_fleet import (  # noqa: E402
    annotate_line_telemetry_logs,
    attach_opex_line_fleet,
    parse_aaahogex_build_trains,
    parse_opex_line_fleet,
    summarize_build_trains_by_year,
)


COAL = (
    "dbg: [script:4] [1] [I] 1970-3-17 BuildTrain 669 roi:669(70292) "
    "route:50770(10437) speed:114(25,15d) TD:101(101) DRCI:0 ARC:0 BT:365 "
    "wt:15,4(104) acc:154,4(2) (120/150/71[Coal])x1 UU '37' (Diesel)-Coal Truckx5(single) "
    "0002Punttown Power Station<-0001Nonfingpool Coal Mine[Coal]Rail maxVehicles:1"
)
MIXED = (
    "dbg: [script:4] [1] [I] 1970-7-1 BuildTrain 9 roi:9 speed:114(34,8d) "
    "(492/240/62[Passengers],259/120/94[Mail])x6 "
    "UU '37' (Diesel)-Passenger Carriagex6-Mail Vanx4 "
    "0003Little Sintburg<->0049Linnwell[Passengers]Rail maxVehicles:16"
)
GRAIN = (
    "[I] 1970-11-2 BuildTrain 663 roi:663 speed:111(44,20d) "
    "(84/125/86[Livestock],168/240/95[Grain])x1 "
    "UU '37' (Diesel)-Grain Hopperx8-Livestock Vanx5(single) "
    "0015Fontbourne Factory<-0014New Chinfingford Farm[Grain]Rail maxVehicles:1"
)
HENDRY = (
    "[I] 1972-6-12 BuildTrain 1018 roi:1018 speed:106(10+42,11d) "
    "(76/80/52[Passengers],39/30/81[Mail])x1 "
    "SH/Hendry '25' (Diesel)-Passenger Carriagex2-Mail Vanx1(single) "
    "T:0049Linnwell<-0058Wunninghall[Passengers]Rail maxVehicles:1"
)
STEAM = (
    "[I] 1972-8-9 BuildTrain 10 roi:10 speed:80(10,5d) "
    "(1/1/1[Coal])x2 SH '8P' (Steam)x2-Coal Truckx10 "
    "0008TownA<-0009TownB[Coal]Rail maxVehicles:2"
)
FAILED = (
    "[I] 1970-3-18 BuildTrain failed. Clear cache and retry. (rail) "
    "0002Punttown<-0001Mine[Coal]Rail"
)
NO_ROUTE = (
    "[I] 1970-3-19 BuildTrain 1 roi:1 speed:10 (1/1/1[Coal])x1 "
    "UU '37' (Diesel)-Coal Truckx5 maxVehicles:1"
)


def _train(common):
    return {"type": 0, "train": {"common": common}}


def _common(**fields):
    base = {
        "owner": 0,
        "unitnumber": 1,
        "subtype": 9,
        "engine_type": 23,
        "orders": 1,
        "next": 0,
        "cargo_cap": 0,
        "value": 1,
        "profit_this_year": 0,
        "profit_last_year": 0,
        "vehstatus": 0,
    }
    base.update(fields)
    return base


def _station(town, xy, facilities=1, owner=0):
    return {"normal": {"base": {
        "owner": owner, "town": town, "facilities": facilities, "xy": xy,
    }}}


def _fleet_chunks():
    """Deux trains charbon, une loco seule, deux moteurs differents, air et route."""
    stations = {}
    for sid, town in enumerate(range(10, 22)):
        facilities = 1
        if sid in (8, 9):
            facilities = 8
        elif sid in (10, 11):
            facilities = 2
        stations[sid] = _station(town, 1000 + sid, facilities)
    return {
        "STNN": stations,
        "ORDL": {
            "0": {"orders": [{"type": 1, "dest": 0}, {"type": 1, "dest": 1}]},
            "1": {"orders": [{"type": 1, "dest": 2}, {"type": 1, "dest": 3}]},
            "2": {"orders": [{"type": 1, "dest": 6}, {"type": 1, "dest": 7}]},
            "3": {"orders": [{"type": 1, "dest": 8}, {"type": 1, "dest": 9}]},
            "4": {"orders": [{"type": 1, "dest": 10}, {"type": 1, "dest": 11}]},
        },
        "VEHS": {
            0: _train(_common(unitnumber=1, subtype=9, engine_type=23, next=2, orders=1)),
            1: _train(_common(unitnumber=0, subtype=4, engine_type=29, next=3, orders=0)),
            2: _train(_common(unitnumber=0, subtype=1, engine_type=99, next=0, orders=0)),
            3: _train(_common(unitnumber=2, subtype=9, engine_type=23, next=5, orders=1)),
            4: _train(_common(unitnumber=0, subtype=4, engine_type=29, next=0, orders=0)),
            5: _train(_common(unitnumber=3, subtype=9, engine_type=40, next=0, orders=2)),
            7: _train(_common(unitnumber=4, subtype=9, engine_type=23, next=0, orders=3)),
            8: _train(_common(unitnumber=5, subtype=9, engine_type=30, next=0, orders=3)),
            9: {"type": 3, "aircraft": {"common": _common(
                unitnumber=1, subtype=0, engine_type=None, next=11, orders=4,
            )}},
            10: {"type": 3, "aircraft": {"common": _common(
                unitnumber=0, subtype=4, engine_type=77, next=0, orders=0,
            )}},
            11: {"type": 1, "roadveh": {"common": _common(
                unitnumber=1, subtype=1, engine_type=8, next=0, orders=5,
            )}},
        },
    }


def _by_stations(lines, *station_ids):
    wanted = set(station_ids)
    found = [line for line in lines if set(line["station_ids"]) == wanted]
    if len(found) != 1:
        raise AssertionError("ligne %s introuvable (%d)" % (station_ids, len(found)))
    return found[0]


class LineFleetSaveTests(unittest.TestCase):
    def test_rail_consist_ignores_second_engine_and_air_shadow(self):
        diag = extract_line_telemetry(_fleet_chunks(), 0)
        self.assertTrue(diag["ok"], diag.get("error"))
        coal = _by_stations(diag["lines"], 0, 1)
        self.assertEqual(coal["engine_id"], 23)
        self.assertEqual(coal["engine_ids"], [23])
        self.assertEqual(coal["train_count"], 2)
        self.assertEqual(coal["wagon_count"], 1)
        self.assertEqual(coal["wagon_engine_id"], 29)
        self.assertEqual(coal["wagon_engine_ids"], [29])
        self.assertIsNone(coal["engine_name"])
        self.assertIsNone(coal["opex_line_id"])
        for consist in coal["consists"]:
            self.assertEqual(consist["wagon_count"], 1)
            self.assertEqual(consist["wagon_engine_ids"], [29])
            self.assertNotIn(99, consist["wagon_engine_ids"])

        solo = _by_stations(diag["lines"], 2, 3)
        self.assertEqual(solo["engine_id"], 40)
        self.assertEqual(solo["wagon_count"], 0)
        self.assertEqual(solo["wagon_engine_ids"], [])
        self.assertIsNone(solo["wagon_engine_id"])
        self.assertEqual(solo["train_count"], 1)

        mixed = _by_stations(diag["lines"], 6, 7)
        self.assertIsNone(mixed["engine_id"])
        self.assertEqual(mixed["engine_ids"], [23, 30])
        self.assertEqual(mixed["wagon_count"], 0)
        self.assertEqual(mixed["train_count"], 2)

        air = _by_stations(diag["lines"], 8, 9)
        self.assertEqual(air["mode"], "air")
        self.assertIsNone(air["engine_id"])
        self.assertEqual(air["engine_ids"], [])
        self.assertIsNone(air["wagon_count"])
        self.assertIsNone(air["wagon_engine_id"])
        self.assertIsNone(air["wagon_engine_ids"])
        self.assertIsNone(air["train_count"])
        self.assertEqual(len(air["consists"]), 1)
        self.assertIsNone(air["consists"][0]["wagon_count"])

        road = _by_stations(diag["lines"], 10, 11)
        self.assertEqual(road["engine_id"], 8)
        self.assertIsNone(road["wagon_count"])
        self.assertIsNone(road["train_count"])

    def test_missing_wagon_engine_is_not_zero(self):
        chunks = {
            "STNN": {0: _station(1, 10), 1: _station(2, 20)},
            "ORDL": {"0": {"orders": [{"type": 1, "dest": 0}, {"type": 1, "dest": 1}]}},
            "VEHS": {
                0: _train(_common(next=2, orders=1)),
                1: _train(_common(unitnumber=0, subtype=4, engine_type=None, next=0)),
            },
        }
        diag = extract_line_telemetry(chunks, 0)
        self.assertTrue(diag["ok"], diag.get("error"))
        line = diag["lines"][0]
        self.assertEqual(line["wagon_count"], 1)
        self.assertIsNone(line["wagon_engine_id"])
        self.assertEqual(line["wagon_engine_ids"], [])
        self.assertIsNone(line["consists"][0]["wagon_engine_ids"][0])

    def test_invalid_consist_is_unknown_not_zero(self):
        from bench_1v1_5y_20seeds import _vehicle_consist_fields
        fields = _vehicle_consist_fields({}, {
            "index": 4, "mode": "rail", "engine_type": 23,
            "consist_valid": False, "consist_indices": [4, 5],
        })
        self.assertIsNone(fields["wagon_count"])
        self.assertIsNone(fields["wagon_engine_ids"])
        missing = _vehicle_consist_fields({"VEHS": {}}, {
            "index": 4, "mode": "rail", "engine_type": 23,
            "consist_valid": True, "consist_indices": [4, 9],
        })
        self.assertIsNone(missing["wagon_count"])


class LineFleetLogTests(unittest.TestCase):
    def test_name_is_last_and_missing_power_stays_absent(self):
        text = "\n".join([
            "dbg: [script:4] [0] [I] OPEX 1970-3-17 LINE_FLEET mode=rail line=4 "
            "engine=23 vmax=112 power=1500 wagons=5 wagon=31 trains=1 vehs=12,40 "
            "name=UU '37' (Diesel)",
            "OPEX 1970-4-1 LINE_FLEET mode=road line=2 engine=8 vmax=80 trains=3 "
            "vehs=1,2,3 name=Balogh",
            "OPEX 1970-5-1 LINE_FLEET mode=rail line=6 engine=23 vmax=90 power=800 "
            "wagons=4 wagon=31 wagons2=2 wagon2=44 trains=1 vehs=9 "
            "name=Chaney 'Jubilee'",
        ])
        events = parse_opex_line_fleet(text)
        self.assertEqual(len(events), 3)
        coal = events[0]
        self.assertEqual(coal["name"], "UU '37' (Diesel)")
        self.assertEqual(coal["line"], 4)
        self.assertEqual(coal["engine"], 23)
        self.assertEqual(coal["vmax"], 112)
        self.assertEqual(coal["power"], 1500)
        self.assertEqual(coal["wagons"], 5)
        self.assertEqual(coal["wagon"], 31)
        self.assertEqual(coal["vehs"], [12, 40])
        road = events[1]
        self.assertIsNone(road["power"])
        self.assertIsNone(road["wagons"])
        self.assertIsNone(road["wagon"])
        self.assertNotEqual(road["power"], 0)
        self.assertEqual(road["name"], "Balogh")
        self.assertNotIn("wagons2", road)
        self.assertEqual(events[2]["wagons2"], 2)
        self.assertEqual(events[2]["wagon2"], 44)
        self.assertEqual(events[2]["name"], "Chaney 'Jubilee'")

    def test_join_matches_engine_and_filters_date(self):
        diag = extract_line_telemetry(_fleet_chunks(), 0)
        text = "\n".join([
            "OPEX 1970-6-1 LINE_FLEET mode=rail line=4 engine=23 vmax=112 power=1500 "
            "wagons=1 wagon=29 trains=2 vehs=0,3 name=UU '37' (Diesel)",
            "OPEX 1973-1-2 LINE_FLEET mode=rail line=9 engine=23 vmax=1 power=1 "
            "wagons=1 wagon=29 trains=2 vehs=0,3 name=TOO LATE",
            "OPEX 1971-2-2 LINE_FLEET mode=rail line=7 engine=99 vmax=50 power=9 "
            "wagons=0 trains=1 vehs=5 name=Wrong Engine",
            "OPEX 1970-1-1 LINE_FLEET mode=road line=1 engine=8 vmax=40 trains=1 "
            "vehs=11 name=Old Name",
            "OPEX 1971-4-4 LINE_FLEET mode=road line=3 engine=8 vmax=80 trains=1 "
            "vehs=11 name=Balogh",
            "OPEX 1971-3-3 LINE_FLEET mode=air line=2 engine=223 vmax=600 power=0 "
            "trains=1 vehs=9 name=Darwin 300",
            "OPEX 1971-5-5 LINE_FLEET mode=rail line=8 engine=23 vmax=10 power=10 "
            "wagons=0 trains=1 vehs=7 name=One",
            "OPEX 1971-5-6 LINE_FLEET mode=rail line=8 engine=30 vmax=11 power=11 "
            "wagons=0 trains=1 vehs=8 name=Two",
        ])
        attach_opex_line_fleet(
            diag["lines"], parse_opex_line_fleet(text), up_to="1972-12-01",
        )
        coal = _by_stations(diag["lines"], 0, 1)
        self.assertEqual(coal["opex_line_id"], 4)
        self.assertEqual(coal["engine_name"], "UU '37' (Diesel)")
        self.assertEqual(coal["max_speed"], 112)
        self.assertEqual(coal["power"], 1500)
        self.assertEqual(coal["engine_id"], 23)
        self.assertEqual(coal["wagon_count"], 1)

        solo = _by_stations(diag["lines"], 2, 3)
        self.assertEqual(solo["opex_line_id"], 7)
        self.assertEqual(solo["engine_id"], 40)
        self.assertIsNone(solo["engine_name"])
        self.assertIsNone(solo["max_speed"])
        self.assertIsNone(solo["power"])

        road = _by_stations(diag["lines"], 10, 11)
        self.assertEqual(road["engine_name"], "Balogh")
        self.assertEqual(road["max_speed"], 80)
        self.assertIsNone(road["power"])
        self.assertEqual(road["opex_line_id"], 3)
        self.assertIsNone(road["train_count"])

        air = _by_stations(diag["lines"], 8, 9)
        self.assertEqual(air["engine_id"], 223)
        self.assertEqual(air["engine_ids"], [223])
        self.assertEqual(air["engine_name"], "Darwin 300")
        self.assertEqual(air["power"], 0)
        self.assertEqual(air["opex_line_id"], 2)
        self.assertIsNone(air["wagon_count"])

        mixed = _by_stations(diag["lines"], 6, 7)
        self.assertEqual(mixed["opex_line_id"], 8)
        self.assertIsNone(mixed["engine_id"])
        self.assertIsNone(mixed["engine_name"])
        self.assertIsNone(mixed["max_speed"])
        self.assertIsNone(mixed["power"])


class BuildTrainTests(unittest.TestCase):
    def test_real_formats_and_absent_fields(self):
        purchases = parse_aaahogex_build_trains("\n".join([
            COAL, MIXED, GRAIN, HENDRY, STEAM, FAILED, NO_ROUTE,
            "[I] 1970-1-1 BuildTrain HasVehicleEngineSet == false somewhere",
            "PreEstimation:591 (51/80/52[Passengers])x1 Floss '47' (Diesel) "
            "0001A<-0002B[Passengers]",
        ]))
        by_date = {item["date"]: item for item in purchases}
        self.assertEqual(set(by_date), {
            "1970-3-17", "1970-7-1", "1970-11-2", "1972-6-12", "1972-8-9",
        })
        coal = by_date["1970-3-17"]
        self.assertEqual(coal["name"], "UU '37' (Diesel)")
        self.assertEqual(coal["locos"], 1)
        self.assertEqual(coal["wagons"], 5)
        self.assertEqual(coal["wagons_by_name"], [{"name": "Coal Truck", "count": 5}])
        self.assertTrue(coal["single"])
        self.assertEqual(coal["vehicles_per_route"], 1)
        self.assertEqual(coal["cruise_speed"], 114)
        self.assertNotIn("power", coal)
        self.assertNotIn("engine_id", coal)
        self.assertNotIn("EngineID", coal)

        mixed = by_date["1970-7-1"]
        self.assertEqual(mixed["wagons"], 10)
        self.assertEqual(mixed["wagons_by_name"], [
            {"name": "Passenger Carriage", "count": 6},
            {"name": "Mail Van", "count": 4},
        ])
        self.assertFalse(mixed["single"])
        self.assertEqual(mixed["vehicles_per_route"], 6)
        self.assertEqual(mixed["cruise_speed"], 114)

        grain = by_date["1970-11-2"]
        self.assertEqual(grain["wagons"], 13)
        self.assertEqual(grain["wagons_by_name"], [
            {"name": "Grain Hopper", "count": 8},
            {"name": "Livestock Van", "count": 5},
        ])
        self.assertTrue(grain["single"])

        hendry = by_date["1972-6-12"]
        self.assertEqual(hendry["name"], "SH/Hendry '25' (Diesel)")
        self.assertEqual(hendry["wagons"], 3)
        self.assertTrue(hendry["single"])
        self.assertEqual(hendry["cruise_speed"], 106)
        self.assertEqual(hendry["wagons_by_name"][0]["name"], "Passenger Carriage")

        steam = by_date["1972-8-9"]
        self.assertEqual(steam["name"], "SH '8P' (Steam)")
        self.assertEqual(steam["locos"], 2)
        self.assertEqual(steam["wagons"], 10)
        self.assertEqual(steam["vehicles_per_route"], 2)
        self.assertEqual(steam["cruise_speed"], 80)

    def test_summary_keeps_earlier_years_up_to_snapshot(self):
        purchases = parse_aaahogex_build_trains("\n".join([COAL, MIXED, HENDRY, STEAM]))
        summary = summarize_build_trains_by_year(purchases, up_to="1971-12-01")
        self.assertEqual(set(summary), {"1970"})
        self.assertEqual(len(summary["1970"]), 2)
        self.assertEqual(summary["1970"][0]["name"], "UU '37' (Diesel)")
        later = summarize_build_trains_by_year(purchases, up_to="1972-12-01")
        self.assertEqual(len(later["1972"]), 2)
        self.assertEqual(summarize_build_trains_by_year([]), {})

    def test_keep_joins_december_checkpoint_only(self):
        chunks = _fleet_chunks()
        output = "\n".join([
            COAL,
            "OPEX 1970-6-1 LINE_FLEET mode=rail line=4 engine=23 vmax=112 power=1500 "
            "wagons=1 wagon=29 trains=2 vehs=0,3 name=UU '37' (Diesel)",
        ])
        experiment = {"seed": 42, "repeat": 0, "policy_id": "reference"}
        previous = bench.LINE_TELEMETRY
        bench.LINE_TELEMETRY = True
        try:
            early = keep({
                "chunks": chunks, "date": "1972-11-01", "output": output,
                "experiment": experiment,
            })
            self.assertNotIn("line_telemetry", early[0])
            self.assertNotIn("line_telemetry", early[1])
            december = keep({
                "chunks": chunks, "date": "1972-12-01", "output": output,
                "experiment": experiment,
            })
        finally:
            bench.LINE_TELEMETRY = previous
        coal = _by_stations(december[0]["line_telemetry"]["lines"], 0, 1)
        self.assertEqual(coal["engine_name"], "UU '37' (Diesel)")
        self.assertEqual(coal["opex_line_id"], 4)
        self.assertEqual(coal["train_count"], 2)
        aaa = december[1]["line_telemetry"]["build_trains_by_year"]
        self.assertEqual(aaa["1970"][0]["name"], "UU '37' (Diesel)")
        self.assertEqual(aaa["1970"][0]["wagons"], 5)
        self.assertNotIn("build_trains_by_year", december[0]["line_telemetry"])
        report = build_line_telemetry_report([
            {"date": "1972-12-01", "line_telemetry": december[1]["line_telemetry"],
             "run": ["AAAHogEx", 42, 0], "duel_policy_id": "reference"},
        ])
        self.assertIn("engine_id", report["observed_fields"])
        self.assertIn("opex_line_id", report["observed_fields"])
        self.assertIn("build_trains_by_year", report["observed_fields"])
        self.assertEqual(report["snapshots"][0]["build_trains_by_year"]["1970"][0]["wagons"], 5)
        self.assertIn("revenue", report["unavailable_fields"])

    def test_defaults_and_annotation_without_log(self):
        defaults = parse_ai_settings(ROOT / "ai" / "OpexAI" / "info.nut")
        self.assertEqual(defaults["decision_log"], 0)
        self.assertEqual(defaults["probes"], 2)
        rec = {"line_telemetry": {"ok": True, "lines": []}}
        aaa = {"line_telemetry": {"ok": True, "lines": []}}
        annotate_line_telemetry_logs(rec, aaa, "", "1972-12-01")
        self.assertEqual(aaa["line_telemetry"]["build_trains_by_year"], {})
        self.assertNotIn("build_trains_by_year", rec["line_telemetry"])


def _function_body(source, name):
    marker = "function %s(" % name
    start = source.find(marker)
    if start < 0:
        raise AssertionError(marker)
    brace = source.find("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[brace:index + 1]
    raise AssertionError("accolades de %s" % name)


def _inside_decision_log(source, index):
    depth = 0
    cursor = index - 1
    while cursor >= 0:
        char = source[cursor]
        if char == "}":
            depth += 1
        elif char == "{":
            if depth == 0:
                head = source[max(0, cursor - 180):cursor]
                if re.search(r"if\s*\(\s*DECISION_LOG\s*\)\s*$", head):
                    return True
            else:
                depth -= 1
        cursor -= 1
    return False


class LineFleetSquirrelTests(unittest.TestCase):
    def test_logger_is_guarded_and_has_no_reserved_word(self):
        source = (ROOT / "ai" / "OpexAI" / "probes.nut").read_text(encoding="utf-8")
        reserved = ("clone", "base", "parent", "resume")
        for name in ("OpexVehicleIdList", "OpexLineFleetLog", "OpexLogStoredRailFleet"):
            body = _function_body(source, name)
            self.assertNotIn("function", body)
            self.assertEqual(body.count("{"), body.count("}"))
            for word in reserved:
                tokens = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", body)
                self.assertNotIn(word, tokens, name)
        for name in ("OpexLineFleetLog", "OpexLogStoredRailFleet"):
            body = _function_body(source, name)
            first = ""
            for line in body.splitlines()[1:]:
                stripped = line.strip()
                if stripped and not stripped.startswith(("/*", "*", "//")):
                    first = stripped
                    break
            self.assertEqual(first, "if (!DECISION_LOG) return;")
        helper = _function_body(source, "OpexVehicleIdList")
        for api in ("AIEngine", "AIVehicle", "AILog", "OpexDecide", "OpexSign"):
            self.assertNotIn(api, helper)

        calls = {
            "task_rail.nut": ("OpexLineFleetLog(", "OpexLogStoredRailFleet("),
            "task_road.nut": ("OpexLineFleetLog(",),
            "task_water.nut": ("OpexLineFleetLog(",),
        }
        for filename, needles in calls.items():
            text = (ROOT / "ai" / "OpexAI" / filename).read_text(encoding="utf-8")
            for needle in needles:
                start = 0
                found = 0
                while True:
                    index = text.find(needle, start)
                    if index < 0:
                        break
                    self.assertTrue(
                        _inside_decision_log(text, index),
                        "%s:%s hors DECISION_LOG" % (filename, needle),
                    )
                    found += 1
                    start = index + len(needle)
                self.assertGreater(found, 0, needle)
