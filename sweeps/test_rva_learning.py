import unittest
from rva_learning import DwellModel


class Learning(unittest.TestCase):
    def test_cold_and_no_future_leak(self):
        m=DwellModel();m.observe('engineA/routeX',20,[4,6])
        self.assertEqual(m.predict('engineA/routeX',20,3)['dwell'],3)
        self.assertEqual(m.predict('engineA/routeX',21,3)['dwell'],5)
        self.assertEqual(m.predict('engineB/routeX',21,3)['status'],'cold_physics')

    def test_only_comparable_observable_dwell(self):
        m=DwellModel();m.observe('manual/routeX',10,[4,6]);m.observe('manual/routeX',20,[6,8])
        p=m.predict('manual/routeX',30,3)
        self.assertEqual(p['bounds'],[5,7]);self.assertEqual(p['n'],2)
        self.assertEqual(m.predict('symmetric/routeX',30,3)['n'],0)
        self.assertNotIn('revenue',p)
