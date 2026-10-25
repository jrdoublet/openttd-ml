"""PO-02 : preuve géométrique et contrat du rejet anticipé de la spirale.

Modèle à terrain figé, pas une preuve de trajectoire/opcodes en jeu.
"""
import hashlib
from itertools import product
from pathlib import Path
import random
import re
import unittest
from v233_long_good_legacy import off_source

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
INSERTION = """        /* PO-02 : base est le premier/dernier quai selon sign, sur les deux axes.
         * Le filtre historique rejette avant stats/cargo/commande/paralleles.
         * Conserver le chemin historique pour une longueur non positive. */
        if (STATION_PLAN_PRECHECK && length > 0 &&
            (!AITile.IsBuildable(base) || AITile.GetSlope(base) != AITile.SLOPE_FLAT)) continue;
"""


def geometry(tile, step, sign, length):
    anchor = tile if sign > 0 else tile - step * (length - 1)
    station_exit = anchor + step * (length - 1) if sign > 0 else anchor
    lead = station_exit + step if sign > 0 else station_exit - step
    return anchor, lead, tuple(anchor + step * i for i in range(length))


def search(tiles, length, terrain, precheck, double, limit):
    """Même ordre, filtres et points d'effets observables ; commandes simulées."""
    events, plans = [], []
    def usable(tile):
        return all(terrain.get(tile, (True, True, True)))  # valid, buildable, flat
    for tile in tiles:
        if len(plans) >= limit:
            break
        if not terrain.get(tile, (True, True, True))[0]:
            continue
        if precheck and length > 0 and not usable(tile):
            continue
        for step, sign in product((1, 256), (-1, 1)):
            anchor, lead, platform = geometry(tile, step, sign, length)
            if not usable(lead) or not all(map(usable, platform)):
                continue
            events.append(("nClear", anchor, lead))
            if anchor % 5 == 0:  # cargo refusal
                continue
            events.append(("nCargo", anchor, lead))
            if anchor % 7 == 0:  # encroachment refusal
                continue
            events.append(("BuildRailStation", anchor, lead))
            if anchor % 11 == 0:
                continue
            if double:
                events.append(("parallel", anchor, lead))
                if anchor % 13 == 0:
                    continue
            events.append(("nCmd", anchor, lead))
            plans.append((anchor, lead, step, length))
            if len(plans) >= limit:
                break
    return plans, events


class StationPlanPrecheck(unittest.TestCase):
    def test_only_guard_added_to_historical_rail_source(self):
        source = (AI / "builder_rail.nut").read_text(encoding="utf-8")
        self.assertEqual(source.count(INSERTION), 1)
        # rebasé le 24/10 : eec5db81 (revue R11 OpexBridgeSortBySpeed et eb6f26fc retrait V233)
        historical = off_source("builder_rail.nut", source).replace(INSERTION, "")
        self.assertEqual(hashlib.sha256(historical.encode()).hexdigest(),
                         "a68b8620a773b28c830ea8df3d905da1233576023c9837575a12f9ac24af4560")
        body = source[source.index("function OpexStationPlans("):]
        self.assertLess(body.index(INSERTION), body.index("foreach (axis in axes)"))
        self.assertLess(body.index("if (!AIMap.IsValidTile(base)) continue;"), body.index(INSERTION))
        self.assertLess(body.index("if (usable)"), body.index("stats.nClear++"))
        self.assertLess(body.index("stats.nClear++"), body.index("if (requireDouble)"))

    def test_setting_default_on_and_loaded_once(self):
        info = (AI / "info.nut").read_text(encoding="utf-8")
        block = re.search(r'AddSetting\(\{\s*name = "station_plan_precheck".*?\}\);', info, re.S)[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 1", block)
        self.assertIn("min_value = 0, max_value = 1", block)
        self.assertIn("STATION_PLAN_PRECHECK <- true;", (AI / "globals_pre.nut").read_text())
        settings = (AI / "settings.nut").read_text()
        self.assertEqual(settings.count('GetSetting("station_plan_precheck")'), 1)
        self.assertIn('STATION_PLAN_PRECHECK = AIController.GetSetting("station_plan_precheck") == 1;', settings)

    def test_four_orientations_base_is_filtered_platform_endpoint(self):
        for length, step, sign in product(range(1, 65), (1, 256), (-1, 1)):
            with self.subTest(length=length, step=step, sign=sign):
                _, lead, platform = geometry(100000, step, sign, length)
                self.assertEqual(platform[0 if sign > 0 else -1], 100000)
                self.assertNotEqual(lead, 100000)
                for state in ((True, False, True), (True, True, False)):
                    terrain = {100000: state}
                    for double in (False, True):
                        self.assertEqual(search([100000], length, terrain, False, double, 12), ([], []))
                        self.assertEqual(search([100000], length, terrain, True, double, 12), ([], []))

    def test_order_counters_and_commands_identical_on_mixed_terrain(self):
        rng = random.Random(190)
        tiles = [100000 + dx + 256 * dy
                 for r in range(5) for dx in range(-r, r + 1)
                 for dy in range(-r, r + 1) if abs(dx) == r or abs(dy) == r]
        for length, double, limit in product((-1, 0, 1, 2, 4, 7), (False, True), (1, 12, 36)):
            terrain = {tile + offset: rng.choice(((True, True, True),) * 8 +
                       ((False, True, True), (True, False, True), (True, True, False)))
                       for tile in tiles for offset in (0, -1, 1, -256, 256)}
            self.assertEqual(search(tiles, length, terrain, False, double, limit),
                             search(tiles, length, terrain, True, double, limit))


if __name__ == "__main__":
    unittest.main()
