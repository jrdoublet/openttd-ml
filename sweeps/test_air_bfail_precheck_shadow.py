"""Contrats statiques : la sonde de B n'est jamais une décision."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class ShadowSafety(unittest.TestCase):
    def test_four_defaults_off(self):
        info = (ROOT / "info.nut").read_text(encoding="utf-8")
        part = info.split('name = "air_bfail_precheck_shadow",', 1)[1].split("});", 1)[0]
        for name in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{name}_value = 0", part)
        self.assertIn("AIR_BFAIL_PRECHECK_SHADOW <- false;",
                      (ROOT / "globals_pre.nut").read_text(encoding="utf-8"))
        self.assertIn('AIR_BFAIL_PRECHECK_SHADOW = OpexProbeSetting("air_bfail_precheck_shadow") != 0;',
                      (ROOT / "settings.nut").read_text(encoding="utf-8"))

    def test_shadow_never_takes_preb_path(self):
        src = (ROOT / "air_construction.nut").read_text(encoding="utf-8")
        self.assertNotIn("AIR_EFFICIENCY_PREFLIGHT", src)
        probe = src.split("if (AIR_BFAIL_PRECHECK_SHADOW && !reuseA && !reuseB)", 1)[1].split("local costs = AIAccounting();", 1)[0]
        self.assertIn("local preB = OpexAirPreflightEndpoint(plan.siteB, airport, planeChoice, false);", probe)
        self.assertIn("result.preBShadow <-", probe)
        self.assertNotIn("return result;", probe)
        self.assertNotIn("OpexAirInvalidateCachedSite", probe)
        self.assertNotIn("OpexAirRollback", probe)

    def test_telemetry_intra_call_not_saved_or_used_as_choice(self):
        task = (ROOT / "task_air.nut").read_text(encoding="utf-8")
        helper = task.split("function OpexAirV126RecoveryFields(result)", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("if (AIR_BFAIL_PRECHECK_SHADOW && (\"preBShadow\" in result))", helper)
        self.assertIn('" pre_b_ok="', helper)
        self.assertIn('" real_b_err="', helper)
        self.assertIn('" real_b_stage="', helper)
        self.assertIn("return fields;", helper)

    def test_real_stage_is_recorded_only_in_newpair_shadow(self):
        src = (ROOT / "air_construction.nut").read_text(encoding="utf-8")
        self.assertIn('result.preBRealStage <- !levelB.ok ? "level" : (!okB ? "airport" : "built");', src)
        self.assertIn("if (AIR_BFAIL_PRECHECK_SHADOW && !reuseA && !reuseB)", src)


if __name__ == "__main__":
    unittest.main()
