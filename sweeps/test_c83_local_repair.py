"""Source contracts and fail-closed reader, supplemented by real NoAI fixtures."""
from pathlib import Path
import re
import unittest
from c83_reaction import parse_c83_repairs

ROOT = Path(__file__).resolve().parents[1]


def body(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    tokens = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|[{}]', re.S)
    depth = 0
    for token in tokens.finditer(source, brace):
        if token.group() == "{":
            depth += 1
        elif token.group() == "}":
            depth -= 1
            if depth == 0:
                return source[start:token.end()]
    raise AssertionError(f"unterminated function: {signature}")

class LocalRepairContracts(unittest.TestCase):
    def test_isolated_setting_defaults_and_loading(self):
        info = (ROOT / "ai/OpexAI/info.nut").read_text(encoding="utf-8")
        setting = info.split('name = "c83_local_repair"', 1)[1].split("});", 1)[0]
        for field in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{field} = 0", setting)
        self.assertIn('C83_LOCAL_REPAIR = AIController.GetSetting("c83_local_repair") != 0;',
                      (ROOT / "ai/OpexAI/settings.nut").read_text(encoding="utf-8"))
        worker = (ROOT / "ai/OpexAI/orchestrator.nut").read_text(encoding="utf-8")
        self.assertIn('targeted && entityKind == "town" && ("reason" in s) && s.reason == "c83_slot_race"', worker)

    def test_target_only_search_and_validated_partners(self):
        source = (ROOT / "ai/OpexAI/air_c83_repair.nut").read_text(encoding="utf-8")
        repair = body(source, "function OpexC83RepairFindSites(")
        self.assertEqual(repair.count("OpexAirFindSite("), 1)
        self.assertIn("if (target && site == null)", repair)
        self.assertIn("!target || OpexAirSlotTownId(anchor) == ctx.targetTownId", repair)
        self.assertIn("OpexAirSiteStillBuildable(known", repair)
        self.assertIn("scan.fallback = scan.partners == 0;", repair)
        self.assertIn("if (progressed &&", repair)
        self.assertIn("scan.index++;", repair)

    def test_hub_rescan_disabled_only_in_local_combo_and_save_restart_preserved(self):
        planning = (ROOT / "ai/OpexAI/air_planning.nut").read_text(encoding="utf-8")
        self.assertIn("if (!ctx.c83RepairCombo && sites.len() < AIR_HUB_NEW_SITE_POOL)", planning)
        saved = (ROOT / "ai/OpexAI/persist.nut").read_text(encoding="utf-8")
        regen = saved.split('if (worker.kind == "regen_candidates")', 1)[1].split("  return {", 2)[1]
        self.assertNotIn("airState", regen)
        self.assertNotIn("c83Repair", regen)
        generation = (ROOT / "ai/OpexAI/projects_generation.nut").read_text(encoding="utf-8")
        self.assertIn('OpexApplyGeneratedModeProjects(projects, generated, abandonedPairs, "air",', generation)

class RepairReader(unittest.TestCase):
    def log(self, **kw):
        fields = dict(enabled=1, town=8, local=1, fallback=0, kept=1, searched=0, partners=2, ops=100, ticks=74)
        fields.update(kw)
        return "C83_LOCAL_REPAIR " + " ".join(f"{key}={value}" for key,value in fields.items()) + "\n"

    def test_absence_and_malformed_remain_unknown(self):
        for text in (None, "", "other", "C83_LOCAL_REPAIR bad", self.log(enabled=2),
                     self.log() + self.log(enabled=0, local=0, kept=0, partners=0)):
            self.assertIsNone(parse_c83_repairs(text))

    def test_local_and_fallback_are_counted_without_dedup(self):
        result = parse_c83_repairs(self.log() + self.log(local=0, fallback=1, kept=0, searched=1, partners=0))
        self.assertEqual((result["completed"], result["local"], result["fallback"], result["ops"]), (2,1,1,200))

    def test_control_completed_zero_local_is_observed(self):
        result = parse_c83_repairs(self.log(enabled=0, local=0, kept=0, partners=0))
        self.assertEqual(result["completed"], 1)
        self.assertEqual(result["local"], 0)
