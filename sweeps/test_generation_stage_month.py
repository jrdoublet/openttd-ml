"""UR-16b: calendar boundaries of the actual first-year stamp readers.

These offline checks evaluate the integer expressions extracted from Squirrel;
they do not compile Squirrel or replace an engine smoke / Save-Load run.
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
READER_COUNTS = {
    "scheduler_tasks.nut": 2,
    "task_projects.nut": 2,
    "task_rail.nut": 1,
}
# Accept the old expression too, so the calendar assertions detect the bug.
YEAR_READER = re.compile(
    r"(?:\((?:owner|this)\._generationStageMonth\s*-\s*1\)"
    r"|(?:owner|this)\._generationStageMonth)\s*/\s*12"
)


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def readers():
    return [(name, match.group()) for name in READER_COUNTS
            for match in YEAR_READER.finditer(source(name))]


def decoded_year(expression, stamp):
    # All operands tested here are nonnegative integers: Python // and
    # Squirrel integer / give the same result. Never decode sentinel -1.
    expression = re.sub(r"(?:owner|this)\._generationStageMonth",
                        str(stamp), expression)
    return eval(expression.replace("/", "//"), {"__builtins__": {}})


class TestGenerationStageMonth(unittest.TestCase):
    def test_all_five_readers_are_covered(self):
        for name, count in READER_COUNTS.items():
            with self.subTest(module=name):
                self.assertEqual(len(YEAR_READER.findall(source(name))), count)

    def test_every_month_retains_its_calendar_year(self):
        for name, expression in readers():
            for year in (0, 1970, 1999, 2000):
                for month in range(1, 13):
                    with self.subTest(module=name, reader=expression,
                                      year=year, month=month):
                        self.assertEqual(decoded_year(expression, year * 12 + month), year)

    def test_december_start_is_active_in_december_not_next_january(self):
        for name, expression in readers():
            with self.subTest(module=name, reader=expression):
                first_year = decoded_year(expression, 1970 * 12 + 12)
                self.assertTrue(1970 == first_year)
                self.assertFalse(1971 == first_year)

    def test_january_start_remains_active_through_december(self):
        for name, expression in readers():
            with self.subTest(module=name, reader=expression):
                first_year = decoded_year(expression, 1970 * 12 + 1)
                self.assertTrue(1970 == first_year)
                self.assertFalse(1971 == first_year)

    def test_consecutive_december_january_stamps_decode_to_distinct_years(self):
        for name, expression in readers():
            with self.subTest(module=name, reader=expression):
                self.assertEqual(decoded_year(expression, 1999 * 12 + 12), 1999)
                self.assertEqual(decoded_year(expression, 2000 * 12 + 1), 2000)

    def test_uninitialized_stamp_is_guarded_or_initialized(self):
        scheduler = source("scheduler_tasks.nut")
        projects = source("task_projects.nut")
        rail = source("task_rail.nut")
        self.assertRegex(scheduler, r"owner\._generationStageMonth >= 0\s*\?")
        self.assertRegex(projects, r"this\._generationStageMonth >= 0\s*&& year ==")
        self.assertRegex(rail, r"!stillFirstYear && this\._generationStageMonth >= 0\s*&&")
        self.assertIn("if (this._generationStageMonth < 0)", scheduler)
        self.assertIn("if (this._generationStageMonth < 0)", projects)
        self.assertIn("_generationStageMonth = -1;", source("main.nut"))

    def test_persisted_stamp_keeps_one_based_month_encoding(self):
        self.assertIn("owner._generationStageMonth = ym;", source("scheduler_tasks.nut"))
        for name in ("scheduler_tasks.nut", "task_projects.nut"):
            writers = re.findall(r"this\._generationStageMonth = ([^;]+);", source(name))
            self.assertTrue(writers)
            for expression in writers:
                self.assertIn("* 12 + AIDate.GetMonth(", expression)
                self.assertNotIn("- 1", expression)
        persist = source("persist.nut")
        self.assertEqual(persist.count("generationStageMonth = this._generationStageMonth,"), 2)
        self.assertIn('if ("generationStageMonth" in data) '
                      'this._generationStageMonth = data.generationStageMonth;', persist)


if __name__ == "__main__":
    unittest.main()
