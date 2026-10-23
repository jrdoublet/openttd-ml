"""Contrats statiques DIST-BORNES-1 ; aucune compilation Squirrel ni partie."""
import hashlib
import re
import unittest

from test_v261_forum_behaviours import body, source


class EpochBoundsCostContracts(unittest.TestCase):
    def test_guard_and_single_refresh_call(self):
        probe = body('candidates.nut', 'OpexLogEpochBoundsCost')
        self.assertTrue(probe.lstrip('{').strip().startswith('if (!DECISION_LOG) return;'))
        refresh = body('candidates.nut', 'OpexRefreshEpochBounds')
        self.assertRegex(refresh, r'if \(DECISION_LOG\) \{\s*OpexDecide\("EPOCH_BOUNDS",[\s\S]+?'
                                 r'OpexLogEpochBoundsCost\(catalog\);\s*\}\s*\}$')
        self.assertEqual(source('candidates.nut').count('OpexLogEpochBoundsCost(catalog);'), 1)
        self.assertNotIn('catalog.bounds', probe)
        self.assertNotRegex(probe, r'catalog\.[\w.]+\s*(?:=(?!=)|<-|\+\+|\+=)')

    def test_bounded_estimators_and_signed_crossover(self):
        probe = body('candidates.nut', 'OpexLogEpochBoundsCost')
        self.assertIn('for (local d = 20; d <= 400; d += 20)', probe)
        self.assertEqual(len(re.findall(r'\b(?:for|foreach|while)\s*\(', probe)), 1)
        self.assertIn('OpexLineEconomics(catalog, catalog.paxCargo, d, monthly, "pax",', probe)
        self.assertIn('0, null, null, cruiseCache)', probe)
        self.assertIn('maintenance, 0, 2, 0, 1)', probe)
        self.assertIn('+ catalog.costRailDepot + rail.vehicleCost', probe)
        self.assertIn('2 * rail.platformLength * catalog.costStation', probe)
        self.assertIn('1000.0 * rail.profitAnnual / capitalRail', probe)
        self.assertIn('1000.0 * air.profitAnnual / capitalAir', probe)
        self.assertIn('if (crossover < 0 && roiAir >= roiRail) crossover = d;', probe)
        self.assertIn('local crossover = -1;', probe)
        self.assertIn('" crossover=" + crossover', probe)
        self.assertIn('roi_rail=NA roi_air=NA', probe)
        for forbidden in ('.Valuate(', '.find(', 'function(', 'catalog.bounds'):
            self.assertNotIn(forbidden, probe)

    def test_existing_candidates_unchanged_after_removing_probe(self):
        # Exact pre-probe source fingerprint, retaining DIST_AIR_MIN already on branch.
        code = source('candidates.nut')
        start = code.index('/* DIST-BORNES-1 : diagnostic seulement,')
        end = code.index('function OpexRefreshEpochBounds(catalog)', start)
        restored = (code[:start] + code[end:]).replace('    OpexLogEpochBoundsCost(catalog);\n', '')
        self.assertEqual(hashlib.sha256(restored.encode()).hexdigest(),
                         '3744db72515531e36ca24d3cd600e73a539c265dae4246289499056e7b0d0fb5')
