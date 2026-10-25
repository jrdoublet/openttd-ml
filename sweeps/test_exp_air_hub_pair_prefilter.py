"""Contrats source et modele pur du prefiltre hub (aucune partie).

Ne compile ni n'execute Squirrel. Le raccordement du setting/global OFF est
du ressort de l'integrateur ; aucun autre module n'est modifie par ce lot.
Le cargo n'entre volontairement pas dans la cle : le rejet final existant
est independant du cargo, contrairement a une deduplication de candidats.
"""

from itertools import product
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return (ROOT / "ai" / "OpexAI" / name).read_text(encoding="utf-8")


def code(source):
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S)


def body(source, name):
    source = code(source)
    start = source.index(f"function {name}(")
    brace = source.index("{", start)
    depth = 0
    for pos in range(brace, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start:pos + 1]
    raise AssertionError(f"Unterminated function: {name}")


def pair_key(a, b):
    if a is None or b is None:
        return None
    return f"{a}|{b}" if a <= b else f"{b}|{a}"


def town_centers_linked(a, b, lines):
    """Oracle de la boucle existante, sans utiliser pair_key."""
    if lines is None or a is None or b is None:
        return False
    return any(
        line.get("mode") == "air"
        and ((line["originA"] == a and line["originB"] == b)
             or (line["originA"] == b and line["originB"] == a))
        for line in lines
    )


def prefilter_linked(ctx, a, b, enabled=True):
    """Modele du cache paresseux, distinct de l'oracle lineaire."""
    if not enabled or ctx["lines"] is None or a is None or b is None:
        return False
    if "airHubTownPairs" not in ctx:
        ctx["airHubTownPairs"] = {
            pair_key(line["originA"], line["originB"])
            for line in ctx["lines"]
            if line.get("mode") == "air"
            and pair_key(line["originA"], line["originB"]) is not None
        }
    return pair_key(a, b) in ctx["airHubTownPairs"]


def air_line(a, b, **fields):
    return dict(mode="air", originA=a, originB=b, **fields)


class HubPairSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.planning = read("air_planning.nut")
        cls.final = body(read("task_air.nut"), "OpexAirBatchPlanStillLive")

    def test_existing_final_pair_contract_remains(self):
        loop = self.final[self.final.index("foreach (line in lines)"):]
        normalized = loop.replace("plan.siteA.town.tile", "tileA").replace(
            "plan.siteB.town.tile", "tileB")
        for predicate in (
            'if (!("mode" in line) || line.mode != "air") continue;',
            "line.originA == tileA && line.originB == tileB",
            "line.originA == tileB && line.originB == tileA",
        ):
            self.assertIn(predicate, normalized)
        self.assertIn(")) return false;", normalized)
        self.assertNotIn("function OpexAirTownCentersLinked(", read("air_towns.nut"))
        for excluded in ("cargo", "deadStreak", "scrapping", "stationA", "anchor"):
            self.assertNotIn(excluded, normalized)

    def test_index_is_exact_direct_pair_set_not_candidate_reservation(self):
        self.assertNotIn("function OpexAirHubPairPrefilterLinked", self.planning)
        self.assertNotIn("function OpexAirHubTownPairKey", self.planning)
        self.assertNotIn("airHubTownPairs", self.planning)

    def test_cache_is_lazy_context_only_and_not_resumed(self):
        self.assertNotIn("airHubTownPairs", self.planning)
        entry = body(self.planning, "OpexAirPlans")
        self.assertIn("local ctx = {", entry)
        self.assertIn("lines = lines,", entry)

    def test_only_hub_arms_are_gated_before_expensive_work(self):
        source = code(self.planning)
        self.assertNotIn("EXP_AIR_HUB_PAIR_PREFILTER", source)
        self.assertNotIn("OpexAirHubPairPrefilterLinked", source)
        for name in ("OpexAirPlansHubToSite", "OpexAirPlansHubToHub",
                     "OpexAirPlansNewPairs", "OpexAirPlansFindSites", "OpexAirPlansDiscoverHubs"):
            self.assertNotIn("EXP_AIR_HUB_PAIR_PREFILTER", body(self.planning, name))

    def test_off_keeps_c83_station_topology_and_second_slot_paths(self):
        hs = body(self.planning, "OpexAirPlansHubToSite")
        hh = body(self.planning, "OpexAirPlansHubToHub")
        self.assertNotIn("C83_FIXES", hs)
        self.assertIn('c83OwnSecondSlotB = ("c83OwnSecondSlot" in site) && site.c83OwnSecondSlot', hs)
        self.assertIn("alreadyConnected = (st1 + \"|\" + st2) in hubIndex.pairs;", hh)
        self.assertIn("(oA == st1 && oB == st2) || (oA == st2 && oB == st1)", hh)
        self.assertIn("if (reuseA && !OpexAirBatchHubHasCapacity", self.final)
        self.assertIn("if (reuseB && !OpexAirBatchHubHasCapacity", self.final)
        self.assertIn("if (!servedB || !OpexAirC83SecondSlotOpen(plan.siteB.town)) return false;", self.final)
        self.assertNotRegex(code(self.planning), r"C83_FIXES\s*(?:=|<-)")

    def test_probes_expose_index_and_rejections_without_new_global_ledger(self):
        self.assertNotIn("AIR_HUB_PAIR_PREFILTER", self.planning)
        for name, reason, counter in (
            ("OpexAirPlansHubToSite", "hubsite_pair_linked", "airHubSitePairs"),
            ("OpexAirPlansHubToHub", "hubhub_pair_linked", "airHubHubPairs"),
        ):
            arm = body(self.planning, name)
            self.assertNotIn(f'OpexC73RecordRejection("air", "{reason}", 1)', arm)
            self.assertNotIn(f"outcome={reason}", arm)
            self.assertIn(f"CATALOG_COST_ACTIVE.{counter}++", arm)


class HubPairCoherenceTests(unittest.TestCase):
    def test_exhaustive_small_graphs_match_linear_predicate(self):
        edges = [(0, 1), (1, 0), (1, 2), (2, 3), (0, 0), (12, 3), (1, 23)]
        for mask in range(1 << len(edges)):
            lines = [air_line(a, b, cargo=i % 2, deadStreak=i % 3)
                     for i, (a, b) in enumerate(edges) if mask & (1 << i)]
            lines += [dict(mode="rail", originA=3, originB=0), dict(originA=3, originB=1)]
            ctx = {"lines": lines}
            for a, b in product((None, -1, 0, 1, 2, 3, 12, 23), repeat=2):
                self.assertEqual(prefilter_linked(ctx, a, b), town_centers_linked(a, b, lines),
                                 (mask, a, b))

    def test_key_symmetry_and_no_concatenation_collision(self):
        self.assertEqual(pair_key(12, 3), pair_key(3, 12))
        self.assertNotEqual(pair_key(12, 3), pair_key(1, 23))
        self.assertEqual(pair_key(0, 0), "0|0")
        self.assertIsNone(pair_key(None, 0))

    def test_station_ids_anchors_cargo_and_retirement_do_not_change_contract(self):
        lines = [air_line(100, 200, stationA=7, stationB=8, cargo=9,
                          deadStreak=2, scrapping=True)]
        ctx = {"lines": lines}
        self.assertTrue(prefilter_linked(ctx, 200, 100))
        self.assertFalse(prefilter_linked(ctx, 7, 8))
        self.assertFalse(prefilter_linked(ctx, 100, 300))
        # Le contrat final rejette aussi une autre cargaison de la meme paire.
        for cargo in (0, 1, 9):
            plan = dict(src=100, dst=200, cargo=cargo)
            self.assertTrue(prefilter_linked(ctx, plan["src"], plan["dst"]))

    def test_second_slot_and_profitable_variants_of_new_pair_are_not_reserved(self):
        ctx = {"lines": [air_line(100, 200)]}
        plans = [dict(src=100, dst=300, anchor=anchor, cargo=cargo,
                      c83OwnSecondSlotB=True, profit=profit)
                 for anchor, cargo, profit in ((11, 0, 50), (12, 0, 80), (12, 1, 60))]
        kept = [plan for plan in plans if not prefilter_linked(ctx, plan["src"], plan["dst"])]
        self.assertEqual(kept, plans)
        self.assertEqual(max(p["profit"] for p in kept), 80)
        self.assertTrue(prefilter_linked(ctx, 100, 200))
        self.assertFalse(prefilter_linked(ctx, 300, 100))

    def test_no_transitive_connection_or_other_mode_block(self):
        ctx = {"lines": [air_line(1, 2), air_line(2, 3),
                         dict(mode="road", originA=1, originB=3)]}
        self.assertFalse(prefilter_linked(ctx, 1, 3))
        self.assertFalse(prefilter_linked(ctx, 3, 1))

    def test_empty_null_and_off_do_not_block_or_build_off_index(self):
        for lines in (None, [], [air_line(1, 2)]):
            ctx = {"lines": lines}
            self.assertFalse(prefilter_linked(ctx, 1, 2, enabled=False))
            self.assertNotIn("airHubTownPairs", ctx)
        for lines in (None, []):
            self.assertFalse(prefilter_linked({"lines": lines}, 1, 2))

    def test_same_pass_reuses_index_but_new_context_observes_topology_changes(self):
        lines = [air_line(1, 2)]
        ctx = {"lines": lines}
        self.assertTrue(prefilter_linked(ctx, 1, 2))
        index = ctx["airHubTownPairs"]
        self.assertTrue(prefilter_linked(ctx, 2, 1))
        self.assertIs(ctx["airHubTownPairs"], index)
        # Changement entre appels/tranches, jamais au milieu du passage synchrone.
        lines[:] = [air_line(2, 3)]
        resumed = {"lines": lines, "resumeState": {"hubSiteI": 1}}
        self.assertFalse(prefilter_linked(resumed, 1, 2))
        self.assertTrue(prefilter_linked(resumed, 2, 3))
        self.assertEqual(resumed["resumeState"], {"hubSiteI": 1})
        self.assertIsNot(resumed["airHubTownPairs"], index)
        self.assertFalse(prefilter_linked({"lines": []}, 2, 3))


if __name__ == "__main__":
    unittest.main()
