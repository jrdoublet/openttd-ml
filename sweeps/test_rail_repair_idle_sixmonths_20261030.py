"""Six-month no-new-line guard: OFF compatibility, triggers, and Save/Load.

These host contracts validate wiring; engine replay proves Squirrel execution.
"""

import calendar
import datetime as dt
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def calendar_threshold(day):
    """Reference behavior of the implemented Squirrel calendar arithmetic."""
    target_month = day.month + 6
    year = day.year + (target_month - 1) // 12
    month = (target_month - 1) % 12 + 1
    return dt.date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


class TestRailRepairIdleSixMonths(unittest.TestCase):
    def test_exact_calendar_boundaries(self):
        cases = [
            (dt.date(1970, 1, 1), dt.date(1970, 7, 1)),
            (dt.date(1970, 8, 31), dt.date(1971, 2, 28)),
            (dt.date(1971, 8, 31), dt.date(1972, 2, 29)),
            (dt.date(1970, 10, 30), dt.date(1971, 4, 30)),
            (dt.date(1970, 12, 31), dt.date(1971, 6, 30)),
        ]
        for last, threshold in cases:
            with self.subTest(last=last):
                self.assertEqual(calendar_threshold(last), threshold)
                self.assertLess(threshold - dt.timedelta(days=1), threshold)

        helper = read("rail_repair_idle.nut")
        for source in (
            "AIDate.GetMonth(fromDate) + 6", "if (month > 12)",
            "AIDate.GetDayOfMonth(fromDate)", "AIDate.GetDate(nextYear, nextMonth, 1)",
            "if (day > daysInMonth) day = daysInMonth",
            "now < OpexRailRepairSixMonthThreshold",
        ):
            self.assertIn(source, helper)

    def test_all_new_line_successes_reset_clock(self):
        for name in ("task_air.nut", "task_rail.nut", "task_road.nut", "task_water.nut"):
            with self.subTest(name=name):
                body = read(name)
                self.assertEqual(body.count("OpexRailRepairNoteConstruction();"), 1)
                self.assertRegex(body, r"this\._lines\.append\(\{[\s\S]*?\}\);\s+OpexRailRepairNoteConstruction\(\);")
        helper = read("rail_repair_idle.nut")
        self.assertIn("if (!OpexRailRepairAnyOptIn()) return;", helper)
        self.assertIn("RAIL_REPAIR_LAST_CONSTRUCTION_DATE = AIDate.GetCurrentDate()", helper)
        self.assertIn("if (RAIL_REPAIR_LAST_CONSTRUCTION_DATE < 0) return false", helper)
        self.assertIn('phase=reset last=', helper)
        self.assertIn('phase=enabled last=', helper)

    def test_cold_start_is_not_mistaken_for_six_months_idle(self):
        main = read("main.nut")
        self.assertIn('require("rail_repair_idle.nut")', main)
        self.assertIn("RAIL_REPAIR_LAST_CONSTRUCTION_DATE < 0", main)
        self.assertIn("RAIL_REPAIR_LAST_CONSTRUCTION_DATE > AIDate.GetCurrentDate()", main)
        self.assertIn("RAIL_REPAIR_LAST_CONSTRUCTION_DATE = AIDate.GetCurrentDate()", main)

    def test_both_save_modes_preserve_date_and_legacy_is_conservative(self):
        persist = read("persist.nut")
        self.assertIn('shortSave.railRepairLastConstructionDate <- RAIL_REPAIR_LAST_CONSTRUCTION_DATE', persist)
        self.assertIn('saveObj.railRepairLastConstructionDate <- RAIL_REPAIR_LAST_CONSTRUCTION_DATE', persist)
        self.assertIn('typeof data.railRepairLastConstructionDate == "integer"', persist)
        self.assertIn("RAIL_REPAIR_LAST_CONSTRUCTION_DATE = -1;", persist)
        self.assertLess(persist.index('RAIL_REPAIR_LAST_CONSTRUCTION_DATE = -1;'), persist.index('if (data == null) return;'))
        self.assertEqual(persist.count("if (OpexRailRepairAnyOptIn())"), 2)

    def test_all_rescue_triggers_are_conditional_and_off_unchanged(self):
        rail = read("task_rail.nut")
        builder = read("builder_rail.nut")
        v233 = read("v233_long_good.nut")
        self.assertIn('RAIL_REPAIR_ASTAR_PAIR && OpexRailRepairIdleActive() && state.kind == "primary"', rail)
        self.assertIn('RAIL_REPAIR_V131_FOCUS && !RAIL_REPAIR_V131_LEGACY_ACTIVE', rail)
        self.assertIn('&& !OpexRailRepairIdleActive()', rail)
        self.assertIn('RAIL_REPAIR_V131_LEGACY_ACTIVE = V131_RAIL_REPAIR;', read('settings.nut'))
        self.assertEqual(builder.count('RAIL_REPAIR_JOIN_SITE && OpexRailRepairIdleActive()'), 2)
        self.assertEqual(builder.count('RAIL_REPAIR_POSE_ORDER && OpexRailRepairIdleActive()'), 2)
        self.assertIn('if (V233L_CONSTRUCT == 2 && !OpexRailRepairIdleActive()) return false', v233)
        self.assertIn('return V233L_CONSTRUCT == 2 && OpexRailRepairIdleActive()', v233)
        self.assertIn('V233L_CONSTRUCT == 2', read('rail_repair_idle.nut'))

        info = read("info.nut")
        for opt in ("rail_repair_join_site", "rail_repair_v131_focus", "rail_repair_astar_pair", "rail_repair_pose_order"):
            block = re.search(r'name = "' + opt + r'"([\s\S]*?)\}\);', info)
            self.assertIsNotNone(block, opt)
            for difficulty in ("easy", "medium", "hard", "custom"):
                self.assertRegex(block.group(1), difficulty + r"_value\s*=\s*0\b", opt)


if __name__ == "__main__":
    unittest.main()
