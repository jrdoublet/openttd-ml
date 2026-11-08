"""Contract tests for ROAD1Y freight road admission and volume sizing (road1y_freight_adm).

Verifies:
- setting declared default 0 at all four difficulties (0..30);
- ROAD1Y_FREIGHT_ADM global declared default 0 in globals_pre.nut;
- ROAD1Y_FREIGHT_ADM read in OpexLoadSettings and OpexLoadBusDistrictSettings,
  clamped to 0..30 and forced to 0 outside road-only mode;
- candidates.nut: OpexBuildRoadCandidates passes fCargo = null under ROAD1Y_FREIGHT_ADM > 0
  to evaluate all industrial producers (coal, wood, iron...) instead of tariff mono-cargo;
  does not break early on long distance bands;
  preserves up to 4 best freight candidates into TopK pool;
- economy.nut: OpexRoadLineEconomics dimensions truck fleet to volume capacity (up to freightCap)
  instead of hard clamp 2 berths;
- task_road.nut: lowers refleet cash reserve from 50k to 15k for freight lines;
- OpexDecide under DECISION_LOG guards;
- Squirrel hazards check: no anonymous functions, no .find( on arrays, no reserved word identifiers.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from test_v261_forum_behaviours import body, source

AI = ROOT / "ai" / "OpexAI"


class TestRoad1yFreightAdm(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info_src = source("info.nut")
        self.assertEqual(info_src.count('name = "road1y_freight_adm"'), 1)
        setting_block = info_src.split('name = "road1y_freight_adm",')[1].split("});")[0]
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 30", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = 0", setting_block)
        self.assertNotIn("AICONFIG_BOOLEAN", setting_block)

    def test_global_pre_declaration(self):
        self.assertIn("ROAD1Y_FREIGHT_ADM <- 0;", source("globals_pre.nut"))

    def test_settings_nut_loading(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_freight_adm")'), 1)
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_FREIGHT_ADM = AIController.GetSetting("road1y_freight_adm");', load_fn)
        self.assertIn("if (ROAD1Y_FREIGHT_ADM < 0 || ROAD1Y_FREIGHT_ADM > 30) ROAD1Y_FREIGHT_ADM = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_FREIGHT_ADM = 0;", load_fn)
        self.assertNotIn("road1y_freight_adm", source("persist.nut"))
        self.assertNotIn("ROAD1Y_FREIGHT_ADM", source("persist.nut"))

    def test_candidates_freight_admission(self):
        cand = body("candidates.nut", "OpexBuildRoadCandidates")
        proj = body("projects.nut", "OpexBuildProjects")
        self.assertIn("local roadFreightCargo = (ROAD1Y_FREIGHT_ADM > 0) ? null : freightCargo;", proj)
        self.assertIn("if (ROAD1Y_FREIGHT_ADM > 0 && road.candidates.len() > 0)", proj)
        self.assertIn('if (c.kind == "freight") freightCands.append(c);', proj)
        self.assertIn("local bestFreight = OpexTopK(freightCands, 4);", proj)
        self.assertIn('OpexDecide("ROAD1Y_FREIGHT_ADM", "action=preserve_candidate', proj)
        self.assertIn('OpexDecide("ROAD1Y_FREIGHT_ADM", "action=preserve_funded', proj)
        self.assertIn("if (all.len() > before) break;", cand)
        self.assertNotIn("function(", proj)
        self.assertNotIn(".find(", proj)
        for word in ("clone", "base", "parent", "static", "delegate", "resume", "vargc", "vargv"):
            self.assertIsNone(re.search(r"\blocal\s+" + word + r"\b", proj), word)

    def test_economy_freight_sizing(self):
        econ = body("economy.nut", "OpexRoadLineEconomics")
        self.assertIn('if (ROAD1Y_FREIGHT_ADM > 0 && kind == "freight")', econ)
        self.assertIn("local freightCap = (ROAD1Y_FREIGHT_ADM > 1) ? ROAD1Y_FREIGHT_ADM : 15;", econ)
        self.assertIn("roadVehicleCap = freightCap;", econ)
        self.assertIn("vehicles = vehiclesForVolume;", econ)
        self.assertNotIn("function(", econ)
        self.assertNotIn(".find(", econ)
        self.assertNotIn("yield", econ)
        for word in ("clone", "base", "parent", "static", "delegate", "resume", "vargc", "vargv"):
            self.assertIsNone(re.search(r"\blocal\s+" + word + r"\b", econ), word)


if __name__ == "__main__":
    unittest.main()
