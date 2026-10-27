#!/usr/bin/env python3
"""Contrats air_site_funnel : defaut 0, mode 1 = spirale et predicat natif."""

from __future__ import annotations

import hashlib
import random
import re
import unittest
from pathlib import Path

from n75_mc_legacy import historical_bytes

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
AIR_SITES_SHA = "1ef05fc3b922e34d5ed800a52d9b5816e2d958492e434075bd0fe1e4e5a546f7"
PO01C_GENERATORS_SHA = "2a294f62cb19c9c20584b731df53e8a7b94ddab9389322c405b4ab4d2cfe55d2"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for idx in range(brace, len(text)):
        if text[idx] == "{":
            depth += 1
        elif text[idx] == "}":
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    raise AssertionError(signature)


def cheap_loop(tiles, buildable):
    """Boucle de OpexAirFootprintCheapOk, ancre comprise dans tiles[0]."""
    if not buildable or not tiles:
        return False
    min_h = tiles[0]["min_h"]
    max_h = tiles[0]["max_h"]
    for tile in tiles:
        if not tile["valid"]:
            return False
        if tile["water"] or tile["coast"] or tile["river"]:
            return False
        if tile["min_h"] < min_h:
            min_h = tile["min_h"]
        if tile["max_h"] > max_h:
            max_h = tile["max_h"]
        if max_h - min_h >= 2:
            return False
    return True


def cheap_native(tiles, buildable):
    """Filtres AITileList : les tuiles invalides sortent du compte, le reste
    est rejete par KeepValue, puis l'ecart de hauteur est global."""
    if not buildable or not tiles:
        return False
    if any(not tile["valid"] for tile in tiles):
        return False
    if any(tile["water"] for tile in tiles):
        return False
    if any(tile["coast"] for tile in tiles):
        return False
    if any(tile["river"] for tile in tiles):
        return False
    min_h = min(tile["min_h"] for tile in tiles)
    max_h = max(tile["max_h"] for tile in tiles)
    return max_h - min_h < 2


def _tile(valid=True, water=False, coast=False, river=False, min_h=4, max_h=4):
    return {
        "valid": valid, "water": water, "coast": coast, "river": river,
        "min_h": min_h, "max_h": max_h,
    }


class AirSiteFunnelContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = source("info.nut")
        cls.settings = source("settings.nut")
        cls.globals = source("globals_pre.nut")
        cls.sites = source("air_sites.nut")
        cls.funnel = source("air_site_funnel.nut")
        cls.builder = source("builder_air.nut")
        cls.regen = source("po01c_regen.nut")
        cls.coverage = source("air_coverage.nut")
        cls.planning = source("air_planning.nut")
        cls.generators = (AI / "po01c_generators.nut").read_bytes()

    def test_mode0_historical_bytes_and_frozen_generator(self):
        legacy = historical_bytes("air_sites.nut", (AI / "air_sites.nut").read_bytes())
        self.assertEqual(hashlib.sha256(legacy).hexdigest(), AIR_SITES_SHA)
        self.assertEqual(hashlib.sha256(self.generators).hexdigest(), PO01C_GENERATORS_SHA)
        first = body(self.sites, "function OpexAirFindSite(")
        self.assertIn("return OpexAirFindSiteCatchmentListed(", first)
        self.assertNotIn("AIR_SITE_FUNNEL", first)
        self.assertNotIn("OpexAirFootprintCheapOkNative", self.generators.decode("utf-8"))
        self.assertIn("OpexAirFootprintCheapOk(anchor, airport)", self.generators.decode("utf-8"))
        log = body(self.sites, "function OpexAirC96LogChoice(")
        self.assertIn('" probes=" + used + " ops=" + ops', log)
        self.assertIn("OpexOpsMeasureEnd(AIR_SITE_OPS_MARK)", log)

    def test_setting_default_zero_and_historical_cache_only(self):
        blocks = re.findall(
            r'AddSetting\(\{\s*name = "air_site_funnel".*?\}\);', self.info, re.S)
        self.assertEqual(len(blocks), 1)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{level}_value = 0", blocks[0])
        self.assertIn("min_value = 0, max_value = 1", blocks[0])
        self.assertIn("same spiral with a native footprint predicate", blocks[0])
        self.assertEqual(self.settings.count('GetSetting("air_site_funnel")'), 1)
        self.assertIn("AIR_SITE_FUNNEL = (airSiteFunnel == 1) ? 1 : 0;", self.settings)
        self.assertIn("if (AIR_SITE_FUNNEL > 0) OpexAirFunnelInstall();", self.settings)
        self.assertIn("AIR_SITE_FUNNEL <- 0;", self.globals)
        self.assertIn("AIR_SITE_SEARCH_OPS <- 0;", self.globals)
        self.assertIn("AIR_SITE_SEARCH_CALLS <- 0;", self.globals)
        self.assertIn("AIR_SITE_OPS_MARK <- null;", self.globals)
        for gone in (
            "AIR_SITE_FUNNEL_BATCH", "AIR_SITE_FUNNEL_DEAD", "AIR_SITE_FUNNEL_LIST",
            "AIR_SITE_FUNNEL_RAW", "AIR_SITE_FUNNEL_PEN", "AIR_SITE_FUNNEL_KEEP_TOP",
        ):
            self.assertNotIn(gone, self.globals)
            self.assertNotIn(gone, self.coverage)
            self.assertNotIn(gone, self.funnel)
        self.assertLess(
            self.builder.index('require("air_sites.nut");'),
            self.builder.index('require("air_site_funnel.nut");'),
        )
        invalidate = body(self.coverage, "function OpexAirInvalidateCachedSite(")
        self.assertIn("delete AIR_SITE_CACHE[key];", invalidate)
        self.assertNotIn("AIR_SITE_FUNNEL", invalidate)

    def test_both_modes_call_the_spiral_and_accumulate_every_call(self):
        wrap = body(self.funnel, "function OpexAirFindSite(")
        self.assertIn("OpexAirFindSiteSpiral <- OpexAirFindSite;", self.funnel)
        self.assertNotIn("AIR_SITE_FUNNEL", wrap)
        self.assertLess(wrap.index("OpexOpsMeasureBegin()"), wrap.index("OpexAirFindSiteSpiral("))
        self.assertLess(wrap.index("OpexAirFindSiteSpiral("), wrap.index("OpexOpsMeasureEnd(mark)"))
        self.assertLess(wrap.index("OpexOpsMeasureEnd(mark)"), wrap.index("AIR_SITE_SEARCH_OPS += spent"))
        self.assertLess(wrap.index("AIR_SITE_SEARCH_OPS += spent"), wrap.index('OpexAirSiteSearchNote("call")'))
        self.assertLess(wrap.index('OpexAirSiteSearchNote("call")'), wrap.index("return site;"))
        note = body(self.funnel, "function OpexAirSiteSearchNote(")
        self.assertIn('"AIR_SITE_SEARCH ops="', note)
        self.assertIn('" calls="', note)
        self.assertIn('" month="', note)
        self.assertIn('" reason="', note)
        perf = self.planning[self.planning.index('AILog.Info("AIR_PLAN_PERF:'):]
        self.assertIn('" site_search_ops=" + AIR_SITE_SEARCH_OPS', perf)
        self.assertIn('" site_search_calls=" + AIR_SITE_SEARCH_CALLS', perf)

    def test_install_rebinds_only_the_predicate_and_drops_the_po01c_adapter(self):
        install = body(self.funnel, "function OpexAirFunnelInstall(")
        self.assertIn("if (AIR_SITE_FUNNEL <= 0) return;", install)
        self.assertIn("::OpexAirFootprintCheapOk <- OpexAirFootprintCheapOkNative;", install)
        self.assertNotIn("OpexPO01C", install)
        self.assertNotIn("OpexPO01CAirFindSiteFunnel", self.regen)
        self.assertNotIn("yield", self.funnel)
        self.assertNotIn("function(", self.funnel)
        self.assertNotIn(".find(", self.funnel)
        self.assertNotRegex(
            self.funnel, r"\blocal\s+(clone|base|parent|static|delegate|vargc|vargv|resume|yield)\b")

    def test_native_filters_follow_the_tile_loop(self):
        native = body(self.funnel, "function OpexAirFootprintCheapOkNative(")
        order = [
            "if (!AITile.IsBuildableRectangle(anchor, w, h)) return false;",
            "if (!AIMap.IsValidTile(anchor) || !AIMap.IsValidTile(endTile)) return false;",
            "tiles.AddRectangle(anchor, endTile);",
            "if (tiles.Count() != need) return false;",
            "tiles.Valuate(AITile.IsWaterTile);",
            "tiles.KeepValue(0);",
            "tiles.Valuate(AITile.IsCoastTile);",
            "tiles.Valuate(AITile.IsRiverTile);",
            "tiles.Valuate(AITile.GetMinHeight);",
            "tiles.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING);",
            "tiles.Valuate(AITile.GetMaxHeight);",
            "tiles.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);",
            "if (maxH - minH >= 2) return false;",
        ]
        at = -1
        for token in order:
            found = native.index(token)
            self.assertGreater(found, at, token)
            at = found
        self.assertEqual(native.count("if (tiles.Count() != need) return false;"), 4)

    def test_native_predicate_matches_the_tile_loop(self):
        sizes = ((1, 1), (4, 3), (6, 6), (2, 5))
        cases = []
        for width, height in sizes:
            count = width * height
            cases.append([_tile() for _ in range(count)])
            coast = [_tile() for _ in range(count)]
            coast[-1] = _tile(coast=True)
            cases.append(coast)
            water = [_tile() for _ in range(count)]
            water[0] = _tile(water=True, min_h=0, max_h=1)
            cases.append(water)
            river = [_tile() for _ in range(count)]
            river[count // 2] = _tile(river=True)
            cases.append(river)
            invalid = [_tile() for _ in range(count)]
            invalid[min(1, count - 1)] = _tile(valid=False)
            cases.append(invalid)
            span1 = [_tile(min_h=3, max_h=3) for _ in range(count)]
            span1[-1] = _tile(min_h=2, max_h=4)
            cases.append(span1)
            span2 = [_tile(min_h=5, max_h=5) for _ in range(count)]
            span2[-1] = _tile(min_h=3, max_h=3)
            cases.append(span2)
            early = [_tile(min_h=8, max_h=10)] + [_tile(water=True) for _ in range(count - 1)]
            cases.append(early)
        rng = random.Random(0)
        for _ in range(200):
            count = rng.choice(sizes)[0] * rng.choice(sizes)[1]
            # Largeur et hauteur reelles : on reprend une taille du jeu.
            width, height = rng.choice(sizes)
            tiles = []
            for _tile_index in range(width * height):
                kind = rng.randrange(8)
                if kind == 0:
                    tiles.append(_tile(valid=False))
                elif kind == 1:
                    tiles.append(_tile(water=True))
                elif kind == 2:
                    tiles.append(_tile(coast=True))
                elif kind == 3:
                    tiles.append(_tile(river=True))
                else:
                    base = rng.randrange(0, 8)
                    tiles.append(_tile(min_h=base, max_h=base + rng.randrange(0, 2)))
            cases.append(tiles)
        for tiles in cases:
            for buildable in (False, True):
                self.assertEqual(
                    cheap_loop(tiles, buildable),
                    cheap_native(tiles, buildable),
                    (buildable, tiles),
                )


if __name__ == "__main__":
    unittest.main()
