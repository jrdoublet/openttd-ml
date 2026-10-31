"""Contract tests for ROAD1Y child MAIL lines on PAX bus pairs (road1y_mail_on_pax).

Verifies:
- setting declared default 0 at all four difficulties;
- ROAD1Y_MAIL_ON_PAX loaded before bus_districts_overrides.nut is required
  (same order as ROAD1Y_EXTRA_STOPS) and re-read in OpexLoadSettings;
- every live entry is guarded by ROAD1Y_MAIL_ON_PAX;
- Save/Load keeps kind/parentLineId/mailChildLineId/road1yMailTryMonth;
- no anonymous function, array .find, try/yield or nested closure.
"""
import re
import unittest

from test_v261_forum_behaviours import body, source, uncomment


ENTRY_FILES = (
    "bus_districts_overrides.nut",
    "builder_road.nut",
    "task_road.nut",
    "task_report.nut",
)


def _try_blocks(code):
    return re.findall(r"try\s*\{[^}]*\}", code, re.DOTALL)


class TestRoad1yMailOnPax(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info_src = source("info.nut")
        self.assertIn('name = "road1y_mail_on_pax"', info_src)
        setting_block = info_src.split('name = "road1y_mail_on_pax",')[1].split("});")[0]
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = AICONFIG_BOOLEAN", setting_block)

    def test_global_pre_declaration(self):
        self.assertIn("ROAD1Y_MAIL_ON_PAX <- false;", source("globals_pre.nut"))

    def test_settings_loaded_before_override_require(self):
        settings_src = source("settings.nut")
        self.assertGreaterEqual(settings_src.count('GetSetting("road1y_mail_on_pax")'), 1)
        load_settings = body("settings.nut", "OpexLoadSettings")
        self.assertIn(
            'ROAD1Y_MAIL_ON_PAX = AIController.GetSetting("road1y_mail_on_pax") == 1;',
            load_settings,
        )
        loader = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertIn(
            'ROAD1Y_MAIL_ON_PAX = AIController.GetSetting("road1y_mail_on_pax") == 1;',
            loader,
        )
        self.assertLess(
            loader.index('GetSetting("road1y_mail_on_pax")'),
            loader.index('require("bus_districts_overrides.nut")'),
        )
        extra = loader.index('GetSetting("road1y_extra_stops")')
        mail = loader.index('GetSetting("road1y_mail_on_pax")')
        require_at = loader.index('require("bus_districts_overrides.nut")')
        self.assertLess(extra, require_at)
        self.assertLess(mail, require_at)

    def test_override_install_uses_mail_flag(self):
        code = source("bus_districts_overrides.nut")
        self.assertIn(
            "if (ROAD1Y_EXTRA_STOPS > 0 || ROAD1Y_MAIL_ON_PAX) "
            "OpexAI._refleetRoadLines <- OpexRoad1yRefleetSaved;",
            code,
        )
        self.assertNotIn("OpexAI._refleetRoadLines =", code)

    def test_all_entries_guarded_by_mail_flag(self):
        calls = (
            "OpexRoad1yMailStep(",
            "OpexRoad1yRefleetMailLine(",
            "OpexRoad1yAbandonMailChild(",
            'line.kind == "mail_pax"',
        )
        for filename in ENTRY_FILES:
            code = uncomment(source(filename))
            for call in calls:
                for match in re.finditer(re.escape(call), code):
                    prefix = code[max(0, match.start() - 400):match.start()]
                    self.assertIn(
                        "ROAD1Y_MAIL_ON_PAX",
                        prefix,
                        f"{filename} call {call} at {match.start()} lacks ROAD1Y_MAIL_ON_PAX guard",
                    )

    def test_save_clones_mail_fields_and_load_defaults_old_saves(self):
        persist = source("persist.nut")
        skip_start = persist.index("OPEX_SAVE_LINE_SKIP <- {")
        skip_end = persist.index("};", skip_start)
        skip = persist[skip_start:skip_end]
        for field in ("kind", "parentLineId", "mailChildLineId", "road1yMailTryMonth"):
            self.assertNotIn(field + " =", skip)
            self.assertNotIn(field + "=", skip)
        save = body("persist.nut", "OpexSaveProjectLine")
        self.assertIn("local serializableLine = clone line;", save)
        load = body("persist.nut", "OpexAI::_reconcileAfterLoad")
        self.assertIn('if (!("parentLineId" in line)) line.parentLineId <- -1;', load)
        self.assertIn('if (!("mailChildLineId" in line)) line.mailChildLineId <- -1;', load)
        self.assertIn(
            'if (!("road1yMailTryMonth" in line)) line.road1yMailTryMonth <- -1;',
            load,
        )

    def test_squirrel_hazards_no_try_yield_or_closure(self):
        mail_helpers = source("bus_districts.nut")
        start = mail_helpers.index("ROAD1Y_MAIL_ON_PAX : ligne MAIL fille")
        snippets = {
            "bus_districts.nut": mail_helpers[start:],
            "globals_pre.nut": [ln for ln in source("globals_pre.nut").splitlines()
                                if "ROAD1Y_MAIL_ON_PAX" in ln],
            "info.nut": source("info.nut").split('name = "road1y_mail_on_pax",')[1].split("});")[0],
            "settings.nut": [
                ln for ln in source("settings.nut").splitlines()
                if "road1y_mail_on_pax" in ln or "ROAD1Y_MAIL_ON_PAX" in ln
            ],
            "persist.nut": [
                ln for ln in source("persist.nut").splitlines()
                if "parentLineId" in ln or "mailChildLineId" in ln
                or "road1yMailTryMonth" in ln or "mail_pax" in ln
            ],
        }
        for filename, code in snippets.items():
            if isinstance(code, list):
                code = "\n".join(code)
            for word in ("clone", "base", "par", "parent", "static"):
                self.assertNotRegex(
                    code,
                    r"\blocal\s+" + word + r"\b",
                    f"Found local {word} in {filename}",
                )
            self.assertNotIn("function(", code, f"Found anonymous function in {filename}")
            self.assertNotIn(".find(", code, f"Found array .find in {filename}")
            self.assertNotIn("yield", code, f"Found yield in {filename}")
            for tb in _try_blocks(code):
                self.assertNotIn("yield", tb, f"Found yield in try block in {filename}")


if __name__ == "__main__":
    unittest.main()
