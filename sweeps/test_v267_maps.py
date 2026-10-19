import struct
import unittest

import v267_maps as m
import v267_seeds as v

W = H = 40


def riff(tag, body):
    return tag.encode() + len(body).to_bytes(4, "big") + body


def synthetic():
    """Carte 40x40 : bord void, mer a l'ouest (x<=3), riviere de 3 tuiles (x=18..20), colline a l'est.

    Deux villes (maisons) de part et d'autre de la riviere, a 26 tuiles ; une mine et une centrale.
    """
    n = W * H
    mapt, maph, mapo, map2, map5 = [0x00] * n, [1] * n, [0] * n, [0] * n, [0] * n
    for t in range(n):
        x, y = t % W, t // W
        if x == W - 1 or y == H - 1:
            mapt[t] = m.MP_VOID << 4
        elif x <= 3:
            mapt[t], mapo[t], maph[t] = m.MP_WATER << 4, m.WATER_SEA << 5, 0
        elif x == 4:
            mapt[t], map5[t], maph[t] = m.MP_WATER << 4, m.WATER_TILE_COAST << 4, 0
        elif 18 <= x <= 20:
            mapt[t], mapo[t] = m.MP_WATER << 4, m.WATER_RIVER << 5
        elif x >= 30:
            maph[t] = 4
    for town, (x, y) in ((0, (8, 10)), (1, (34, 10))):
        t = y * W + x
        mapt[t], map2[t] = m.MP_HOUSE << 4, town
    raw = {"MAPT": bytes(mapt), "MAPH": bytes(maph), "MAPO": bytes(mapo),
           "MAP2": struct.pack(f">{n}H", *map2), "MAP5": bytes(map5)}
    data = b"OTTN" + struct.pack(">HH", 362, 0) + b"".join(riff(k, b) for k, b in raw.items()) + b"\0" * 4
    chunks = {
        "MAPS": {"records": {"0": {"dim_x": W, "dim_y": H}}},
        "CITY": {"records": {"0": {"xy": 10 * W + 8}, "1": {"xy": 10 * W + 34}}},
        "INDY": {"records": {"0": {"type": m.COAL_MINE, "location.tile": 20 * W + 7},
                             "1": {"type": m.POWER_STATION, "location.tile": 20 * W + 33}}},
    }
    return data, chunks


class MapFeatureTests(unittest.TestCase):
    def setUp(self):
        self.f = m.map_features(*synthetic())

    def test_water_classes(self):
        land = (W - 1) * (H - 1)
        self.assertEqual(self.f["tiles"], land)
        self.assertAlmostEqual(self.f["sea_share"], 4 * (H - 1) / land)
        self.assertAlmostEqual(self.f["river_share"], 3 * (H - 1) / land)
        self.assertAlmostEqual(self.f["coast_share"], (H - 1) / land)

    def test_towns_and_industries(self):
        self.assertEqual(self.f["towns"], 2)
        self.assertEqual(self.f["town_tiles_max"], 1)
        self.assertEqual(self.f["coastal_towns"], 1)  # mer a moins de 8 tuiles de la ville de l'ouest
        self.assertEqual((self.f["industries"], self.f["power_stations"]), (2, 1))

    def test_river_crossing_is_a_bridge_not_sea(self):
        self.assertEqual(self.f["town_pairs"], 1)
        self.assertEqual(self.f["town_river_cross_share"], 1.0)
        self.assertEqual(self.f["town_river_run_max"], 3)
        self.assertEqual(self.f["town_sea_cross_share"], 0.0)
        self.assertEqual(self.f["town_climb_mean"], 3)  # de 1 (plaine) a 4 (colline)
        self.assertEqual(self.f["coal_river_run_max"], 3)

    def test_relief(self):
        self.assertEqual(self.f["height_max"], 4)
        self.assertGreater(self.f["slope_share"], 0)

    def test_segment_endpoints(self):
        pts = m.segment(0, 0, 5, 2)
        self.assertEqual((pts[0], pts[-1], len(pts)), ((0, 0), (5, 2), 6))


class CoverageTests(unittest.TestCase):
    def test_quotas_cover_both_tails_then_mmd_completes(self):
        feats = {s: {"a": float(s), "b": float(s % 7)} for s in range(1, 101)}
        quotas = v.tail_quotas(feats, ["a", "b"], 0.1, 2)
        self.assertEqual(quotas[("a", "haut")], set(range(91, 101)))
        first, unmet = v.coverage_seeds(quotas, 2, 10)
        self.assertEqual(unmet, [])
        z = v.standardize(feats, ["a", "b"])
        chosen = v.greedy_mmd(z, 20, initial=first)
        self.assertEqual(chosen[:len(first)], first)
        self.assertEqual(len(set(chosen)), 20)

    def test_constant_variable_has_no_quota(self):
        feats = {s: {"c": 1.0} for s in range(20)}
        self.assertEqual(v.tail_quotas(feats, ["c"], 0.1, 1), {})


if __name__ == "__main__":
    unittest.main()
