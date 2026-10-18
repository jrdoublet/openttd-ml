from pathlib import Path
import unittest
from rva_distribution import distribution


class Distribution(unittest.TestCase):
    def test_manual_and_per_cargo_automatic_modes(self):
        for mode in ('manual', 'symmetric', 'asymmetric'):
            r=distribution(mode,new_link=False,graph_ready=True,local_offer=50,
                           capacity=100,planned_via=20,waiting_via=1000)
            self.assertEqual(r['carried_month'], 50 if mode=='manual' else 20)

    def test_new_graph_not_zero_demand(self):
        for mode in ('symmetric','asymmetric','unknown'):
            r=distribution(mode,new_link=True,graph_ready=False,local_offer=50,capacity=100)
            self.assertTrue(r['fallback']);self.assertIsNone(r['carried_month'])
            self.assertEqual(r['bounds_month'],[0,50])

    def test_detection_settings_and_origin_via(self):
        p=Path(__file__).resolve().parents[1]/'ai/OpexAI/rva_distribution.nut'
        s=p.read_text()
        for token in ('AIGameSettings.IsValid', 'linkgraph.distribution_pax',
                      'linkgraph.distribution_mail', 'AICargo.GetDistributionType',
                      'GetCargoPlannedFromVia', 'GetCargoWaitingFromVia'):
            self.assertIn(token,s)
