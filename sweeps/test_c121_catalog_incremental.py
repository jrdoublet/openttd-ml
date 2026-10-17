"""Contrats statiques du catalogue AIR incremental (sans partie OpenTTD)."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from campaign_freeze import parse_ai_settings
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air
from opex_projects_source import read_projects_source

AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def squirrel_code(text):
    """Mask literals/comments, not identifiers; preserve line boundaries."""
    return re.sub(r'@"(?:""|[^"])*"|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/',
                  lambda m: re.sub(r'[^\n]', ' ', m.group()), text, flags=re.S)


class TestC121CatalogIncremental(unittest.TestCase):
    def test_settings_adopted_default_and_c121_gate(self):
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('c121_catalog_incremental', 'c121_catalog_air_first_year'))

    def test_default_chooses_original_function_without_cache_call(self):
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('c121_catalog_incremental',))

    def test_invalidation_and_transient_cache(self):
        self.assertIn('reason == "town_founded"', source("events.nut"))
        self.assertIn('reason == "engine_available"', source("events.nut"))
        self.assertIn("AIEvent.ET_ENGINE_PREVIEW", source("events.nut"))
        self.assertIn('layer == "lines"', source("orchestrator.nut"))
        self.assertIn("C121_CATALOG_TOWN_REV.rawset", source("catalog.nut"))
        self.assertIn("C121_CATALOG_HUB_LEARN_REV.rawset(stationId", source("probes.nut"))
        self.assertIn("C121_CATALOG_AIRPORT_LEARN_REV.rawset(airportType", read_builder_air())
        self.assertIn("C121_CATALOG_ARM_LEARN_REV.rawset(arm", read_projects_source())
        self.assertIn("OpexC121CatalogRefreshStationLines(this._lines)", source("orchestrator.nut"))
        self.assertIn("C121_CATALOG_AIRPORT_REV.rawset(airportType", source("catalog.nut"))
        self.assertNotIn("C121_CATALOG_LINES_REV", read_builder_air())
        self.assertNotIn("C121_CATALOG_LEARN_REV", read_builder_air())
        # Expiration historique 365 j ; candidat visible retire (Lot V232).
        self.assertNotIn("c121_air_visible_competition", parse_ai_settings(AI / "info.nut"))
        self.assertIn('date - entry.date >= 365', read_builder_air())
        self.assertNotIn("C121_AIR_VISIBLE_COMPETITION", read_builder_air())
        save = source("persist.nut").split("function OpexAI::Save()", 1)[1].split(
            "function OpexAI::Load(", 1)[0]
        self.assertNotIn("C121_CATALOG_CACHE", save)

    def test_new_squirrel_identifiers_avoid_keywords(self):
        reserved = ("static", "class", "base", "clone", "resume", "yield", "const",
                    "enum", "delegate", "in", "typeof", "instanceof")
        for name in ("catalog.nut", "main.nut", "task_projects.nut", "probes.nut"):
            src = squirrel_code(source(name))
            for word in reserved:
                self.assertNotRegex(src, rf"\blocal\s+{word}\b")
                self.assertNotRegex(src, rf"(?<![\w]){word}\s*(?:=|<-)")

    def test_keyword_check_ignores_logs_but_keeps_real_identifiers(self):
        text = 'AILog.Info(" base=1 \\\" clone=2"); /* local base = 3 */\nlocal base = 4;'
        code = squirrel_code(text)
        self.assertEqual(code.count("base"), 1)
        self.assertRegex(code, r"\blocal\s+base\s*=")
        self.assertEqual(code.count("\n"), text.count("\n"))


if __name__ == "__main__":
    unittest.main()
