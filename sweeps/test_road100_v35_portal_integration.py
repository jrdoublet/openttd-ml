"""ROAD100-35: default-OFF, near-scanner and physical builder contracts.

No Python source inspection can establish actual Squirrel compatibility;
the complete paired OpenTTD smoke remains mandatory.
"""
import re
import unittest
from pathlib import Path

from road100_off_projection import ROOT, off_source


AI = ROOT / "ai" / "OpexAI"


def src(name):
    return (AI / name).read_text(encoding="utf-8")


def function(name, file="builder_road.nut"):
    source = src(file)
    pos = source.index("function " + name + "(")
    nxt = source.find("\nfunction ", pos + 10)
    return source[pos:nxt if nxt >= 0 else len(source)]


class Road100PortalIntegration(unittest.TestCase):
    def test_default_off_four_levels_and_road_sparse_guard(self):
        m = re.search(r'name = "road100_portal_stitch",(.*?)\n\s*\}\);',
                      src("info.nut"), re.S)
        self.assertIsNotNone(m)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(m.group(1), rf"\b{level}_value\s*=\s*0\b")
        self.assertIn("AICONFIG_BOOLEAN", m.group(1))
        self.assertIn("ROAD100_PORTAL_STITCH <- false;", src("globals_pre.nut"))
        guard = src("settings.nut").split("ROAD100_PORTAL_STITCH =", 1)[1].split(";", 1)[0]
        for required in ('GetSetting("road100_portal_stitch") == 1',
                         "ROAD100_SPARSE_CORRIDOR", "ROAD100_LONG_BUILD",
                         "MODE_ROAD", "!MODE_AIR", "!MODE_RAIL", "!MODE_WATER"):
            self.assertIn(required, guard)

    def test_near_scanner_only_under_optin_and_full_site_fallback(self):
        scanner = function("OpexRoad100LongBuildSites")
        build = function("OpexRoad100LongConstructPlan")
        self.assertIn("nearOnly = false", scanner)
        self.assertIn("nearOnly ? [3] : [3, 8, 14, 22]", scanner)
        self.assertIn("AIRoad.BuildDriveThroughRoadStation", scanner)
        self.assertIn("ROAD100_PORTAL_STITCH);", build)
        self.assertIn('buildScanA.sites.len() == 0', build)
        self.assertIn('buildScanB.sites.len() == 0', build)
        self.assertIn('buildScanA.reason != "OPCAP"', build)
        self.assertIn('buildScanB.reason != "OPCAP"', build)
        self.assertIn('OpexOpsMeasureEnd(mark) < limitOps - 100000', build)
        self.assertIn("local sitesA = buildScanA.sites;", build)
        self.assertIn("local sitesB = buildScanB.sites;", build)

    def test_total_budget_and_physical_qualification_unmodified(self):
        build = function("OpexRoad100LongConstructPlan")
        generate = src("candidates.nut")
        self.assertIn('if (ROAD100_PORTAL_STITCH && limitOps > 180000) limitOps = 180000;', build)
        self.assertIn('if (ROAD100_PORTAL_STITCH && attemptLimit > 180000)', generate)
        self.assertIn('local longCap = ROAD100_LONG_BUILD ? 400000 : 250000;', generate)
        self.assertIn('OpexRoad100PortalStitchTrace(pair.a, pair.b, mark, limitOps)', build)
        self.assertIn('OpexRoad100SparseCorridorTrace(pair.a, pair.b, mark, limitOps)', build)
        for required in (
            'OpexRoad100LongVerifyTrace(trace, pair.a, pair.b,',
            'OpexRoad100LongDepotPreflight(trace, pair.a, pair.b,',
            'missing * catalog.costRoadPerTile * 3',
            'quoteTotal = capital + capital / 4 + 50000',
            'road100Sparse = shape == -2',
            'OpexDecide("ROAD100_PORTAL"',
        ):
            self.assertIn(required, build)
        self.assertIn('OpexRoadBuildTrace(plan.trace, added)',
                      function('OpexBuildRoadRoute'))
        self.assertIn('OpexRoadRollback', function('OpexBuildRoadRoute'))
        self.assertIn('OpexRoad100LongTraceHash(longPlan.trace)', src('opcode_exact.nut'))
        self.assertIn('" detail=" + sparse.reason_detail', build)
        self.assertIn('" first_reject=" + sparse.stats.first_reject', build)
        self.assertIn('road100Portal = shape == -2 && ROAD100_PORTAL_STITCH', build)
        self.assertIn('candidate.road100PortalRequested <- true', generate)
        self.assertIn('candidate.road100PortalUnits <- true', generate)
        self.assertIn('longOps += pairOps;', generate)
        self.assertIn('pairOps >= attemptLimit', generate)
        exact = src('opcode_exact.nut')
        self.assertIn('reason = "PORTAL_SETTING"', exact)
        self.assertIn('reason = "PORTAL_DRIFT"', exact)

    def test_same_generator_po01c_sync_and_byte_exact_source_off(self):
        gen = src('candidates.nut')
        self.assertIn('function OpexRoad100SiteFirstGenerator(', gen)
        self.assertIn('OpexRoad100LongConstructPlan(catalog, preliminaryLong,', gen)
        self.assertIn('OpexRoad100SiteFirstGenerator', src('po01c_regen.nut'))
        for name in ('builder_road.nut', 'candidates.nut', 'info.nut',
                     'settings.nut', 'globals_pre.nut'):
            with self.subTest(name=name):
                current = src(name)
                off = off_source(name, current)
                self.assertNotEqual(current, off)
                self.assertEqual(off, off_source(name, off))


if __name__ == '__main__':
    unittest.main()
