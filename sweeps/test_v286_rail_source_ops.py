"""V286: garde OFF, flux d'industrie en unités et microprofil par passe ON.

Les contrats sont statiques ; le smoke OpenTTD valide la syntaxe Squirrel
et l'émission effective des relevés.
"""

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class V286RailSourceOpsContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        probes = read("probes.nut")
        start = probes.index("function OpexV286FlowSample(lines)")
        end = probes.index("/* V309 : observation passive", start)
        cls.function = probes[start:end]

    def test_off_default_and_both_main_loops_guarded(self):
        info = read("info.nut")
        block = re.search(
            r'AddSetting\(\{ name = "v286_rail_flow_probe".*?\}\);', info, re.S
        )
        self.assertIsNotNone(block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(), rf"{level}_value\s*=\s*0\b")
        self.assertIn(
            "if (!V286_FLOW_PROBE || lines == null || lines.len() == 0) return;",
            self.function,
        )
        self.assertEqual(read("main.nut").count(
            "if (V286_FLOW_PROBE) OpexV286FlowSample(this._lines);"
        ), 1)
        self.assertEqual(read("probes.nut").count(
            "if (V286_FLOW_PROBE) OpexV286FlowSample(this._lines);"
        ), 1)

    def test_transport_units_are_all_companies_and_not_line_deliveries(self):
        body = self.function
        self.assertIn(
            "validSrc ? AIIndustry.GetLastMonthTransported(src, cargo) : -1;",
            body,
        )
        self.assertIn('" src_transported_last_month_all=" + transportedAll', body)
        self.assertIn("delivered_by_line=unknown", body)
        self.assertIn("stock_age=unknown", body)
        self.assertLess(
            body.index("local transportedAll ="),
            body.index("src_transported_last_month_all="),
        )

    def test_opcode_measure_includes_flow_vehicle_logs_and_is_bounded(self):
        body = self.function
        self.assertLess(
            body.index("day - V286_FLOW_LAST_DAY < 30) return;"),
            body.index("local opsMark = OpexOpsMeasureBegin();"),
        )
        self.assertIn("local batch = total < 16 ? total : 16;", body)
        self.assertEqual(body.count("local opsMark = OpexOpsMeasureBegin();"), 1)
        self.assertEqual(body.count("OpexOpsMeasureEnd(opsMark)"), 1)
        self.assertLess(body.index('AILog.Info("V286_FLOW'), body.index(
            "OpexOpsMeasureEnd(opsMark)"
        ))
        self.assertLess(body.index('AILog.Info("V286_VEH'), body.index(
            "OpexOpsMeasureEnd(opsMark)"
        ))
        self.assertLess(body.index("OpexOpsMeasureEnd(opsMark)"), body.index(
            'AILog.Info("V286_SAMPLE'
        ))
        for field in ("total_lines=", "examined=", " rail=", " cargo=",
                      " vehicles_cargo="):
            self.assertIn(field, body)

    def test_vehicle_cap_applies_to_cargo_eligible_vehicles(self):
        body = self.function
        self.assertLess(
            body.index("if (cap <= 0) continue;"),
            body.index("inspected++;"),
        )
        self.assertLess(
            body.index("inspected++;"), body.index("vehicleSamples++;")
        )
        self.assertIn("if (inspected >= 4) break;", body)
        self.assertIn('line.cargo2 != line.cargo) cargos.append(line.cargo2);', body)

    def test_probe_state_not_persisted(self):
        settings = read("settings.nut")
        self.assertIn("V286_FLOW_LAST_DAY = -1;", settings)
        self.assertIn("V286_FLOW_CURSOR = 0;", settings)
        self.assertNotIn("V286_FLOW_LAST_DAY", read("persist.nut"))
        self.assertNotIn("V286_FLOW_CURSOR", read("persist.nut"))


if __name__ == "__main__":
    unittest.main()
