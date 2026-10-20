"""V278: contrats sans moteur et modele executable de la frontiere de paires."""
from pathlib import Path
import hashlib
import random
import re
import unittest

from campaign_freeze import parse_ai_setting_specs

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai/OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def function(source, name):
    start = source.index("function " + name + "(")
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def scan_initializers():
    body = function(read("air_lazy_sites.nut"), "OpexV278ExtendSites")
    literal = body.split("lazy.scan = {", 1)[1].split("};", 1)[0]
    return dict(re.findall(r"(\w+)\s*=\s*([^,]+)", literal))


class Frontier:
    """Traduction du tas Squirrel, avec suspension entre chaque ville cherchee.

    Les populations sont figees, les echecs de sites restent observes, chaque
    paire depilee l'est une fois. Aucune geometrie ni economie simulee ici.
    """

    def __init__(self, populations, unavailable=()):
        self.pops = sorted(populations, reverse=True)
        self.heap = []
        self.covered = 0
        self.end = min(8, len(self.pops))
        self.unavailable = set(unavailable)
        self.visited = []
        self.evaluated = []
        self.pending = None
        for a in range(len(self.pops) - 1):
            self.push(self.pair(a, a + 1))

    def pair(self, a, b):
        return (-float(self.pops[a]) * self.pops[b], a, b)

    def push(self, item):
        self.heap.append(item)
        at = len(self.heap) - 1
        while at > 0:
            up = (at - 1) // 2
            if not item < self.heap[up]:
                break
            self.heap[at] = self.heap[up]
            at = up
        self.heap[at] = item

    def pop(self):
        first = self.heap[0]
        last = self.heap.pop()
        if not self.heap:
            return first
        at = 0
        while at * 2 + 1 < len(self.heap):
            down = at * 2 + 1
            if down + 1 < len(self.heap) and self.heap[down + 1] < self.heap[down]:
                down += 1
            if not self.heap[down] < last:
                break
            self.heap[at] = self.heap[down]
            at = down
        self.heap[at] = last
        return first

    def step(self):
        if self.heap:
            _, a, b = self.heap[0]
            if b >= self.end:
                self.end = min((b // 8 + 1) * 8, len(self.pops))
        else:
            self.end = len(self.pops)  # tous les sites restent accessibles aux hubs
        if self.covered < self.end:
            self.covered += 1
            return True  # suspension au milieu d'une extension, sommet intact
        if not self.heap:
            return False
        item = self.pop()
        _, a, b = item
        if b + 1 < len(self.pops):
            self.push(self.pair(a, b + 1))
        self.visited.append(item)
        if a not in self.unavailable and b not in self.unavailable:
            self.evaluated.append(item)
        return True


class TestV278Source(unittest.TestCase):
    def test_scan_initializes_every_historical_resume_access(self):
        source = read("air_planning.nut")
        initialized = scan_initializers()
        for name in ("OpexAirPlansFindSites", "OpexAirPlansNewPairs"):
            body = function(source, name)
            writes = set(re.findall(r"resumeState\.(\w+)\s*=(?!=)", body))
            # Includes += and all reads, even guarded ones: stronger than the
            # requested write contract. c83Repair is tested only with `in`.
            accesses = set(re.findall(r"resumeState\.(\w+)", body))
            self.assertLessEqual(writes, initialized.keys(), name)
            self.assertLessEqual(accesses, initialized.keys(), name)

    def test_work_context_inputs_and_outputs(self):
        source = read("air_planning.nut")
        driver = function(source, "OpexAirPlans")
        initial = driver.split("local ctx = {", 1)[1].split("};", 1)[0]
        fields = set(re.findall(r"(\w+)\s*=", initial))
        lazy = read("air_lazy_sites.nut")
        for callee, caller in (("OpexAirPlansFindSites", "OpexV278ExtendSites"),
                               ("OpexAirPlansNewPairs", "OpexV278LazyPairs")):
            body = function(source, callee)
            accesses = set(re.findall(r"ctx\.(\w+)", body))
            self.assertLessEqual(accesses - {"v278ScanEnd"}, fields)
            outputs = set(re.findall(r"ctx\.(\w+)\s*=(?!=)", body))
            wrapper = function(lazy, caller)
            for key in outputs - {"sites"}:
                self.assertIn(f"ctx.{key} = work.{key};", wrapper)
            self.assertIn('if ("v133Skip" in work) ctx.v133Skip <- work.v133Skip;', wrapper)
        extension = function(lazy, "OpexV278ExtendSites")
        self.assertLess(extension.index("ctx.bestPlan = work.bestPlan"),
                        extension.index("if (!ok) return false"))
        self.assertIn("foreach (site in work.sites)", extension)
        self.assertIn("lazy.sites.append(site)", extension)
        self.assertIn("ctx.sites = lazy.sites", lazy)

    def test_scan_and_rank_suspension_with_strict_existing_slots(self):
        # Execute the actual initializer expressions and the two checkpoint
        # assignment blocks. This models Squirrel `=` (no implicit new slot),
        # not the engine's geometry/economics or automatic tick suspension.
        from types import SimpleNamespace
        ctx = SimpleNamespace(bestPlan=None, stationLimitedTowns={},
                              perfOpsSites=0, perfOpsEval=0, perfProbesCount=0,
                              perfCheapSkip=0, perfSitesFound=0)
        lazy = SimpleNamespace(covered=0, probes={"left": 20, "tested": 0})
        env = dict(ctx=ctx, lazy=lazy, comboIndex=0, null=None)
        state = {key: eval(expr, {"__builtins__": {}}, env)
                 for key, expr in scan_initializers().items()}
        source = function(read("air_planning.nut"), "OpexAirPlansFindSites")
        checkpoints = re.findall(
            r"resumeState.bestPlan = bestPlan;(.*?)return false;", source, re.S)
        self.assertEqual(len(checkpoints), 2)
        winner = object()
        ctx.bestPlan = winner  # winner from a pair before an extended batch
        for pass_index, block in enumerate(checkpoints, 1):
            values = dict(bestPlan=ctx.bestPlan, stationLimitedTowns=ctx.stationLimitedTowns,
                          perfOpsSites=10 * pass_index, perfOpsEval=7,
                          perfProbesCount=pass_index, perfCheapSkip=0,
                          perfSitesFound=pass_index, scanSliceOps=100, rankSliceOps=100)
            assignments = "resumeState.bestPlan = bestPlan;" + block
            for key, op, rhs in re.findall(r"resumeState\.(\w+)\s*(\+=|=)\s*(\w+);", assignments):
                self.assertIn(key, state)  # Python dict assignment alone hides the bug
                state[key] = state[key] + values[rhs] if op == "+=" else values[rhs]
            for key, rhs in re.findall(r"ctx\.(\w+) = (\w+);", block):
                setattr(ctx, key, values[rhs])
            # RestorePrepare reads the outer checkpoint on the next call.
            self.assertIs(state["bestPlan"], winner)
            self.assertEqual(state["perfOpsSites"], ctx.perfOpsSites)
            self.assertIs(state["scanProbes"], lazy.probes)
        self.assertEqual(state["totalOps"], 200)

    def test_setting_auto_equal_difficulties_and_loaded_once(self):
        # Defaut 2 = auto depuis le 20/10 (decision utilisateur) : actif des 1024x1024 tuiles.
        spec = parse_ai_setting_specs(AI / "info.nut")["v278_air_lazy_sites"]
        self.assertEqual((spec["min_value"], spec["max_value"], spec["default"]), (0, 2, 2))
        block = read("info.nut").split('name = "v278_air_lazy_sites"', 1)[1].split("});", 1)[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 2", block)
        self.assertIn("V278_AIR_LAZY_SITES = v278 == 1 || (v278 == 2 && bigMap);", read("settings.nut"))
        self.assertIn("V278_AIR_LAZY_SITES <- false;", read("globals_pre.nut"))
        self.assertEqual(read("settings.nut").count('GetSetting("v278_air_lazy_sites")'), 1)

    def test_dispatch_off_retains_historical_calls(self):
        source = read("air_planning.nut")
        for name in ("OpexAirPlansStepFindSites", "OpexAirPlansStepNewPairs"):
            body = function(source, name)
            self.assertIn("V278_AIR_LAZY_SITES && OpexV278LazyEnabled(ctx)", body)
            self.assertIn(": OpexAirPlans", body)
        self.assertIn('require("air_lazy_sites.nut");', read("builder_air.nut"))

    def test_historical_driver_and_economics_fingerprint(self):
        # Empreintes de master au depart de V278, corps entier du driver et
        # de NewPairs. Seuls les panneaux de premiere paire sont desarmes
        # pour les appels atomiques V278, sans retoucher aucun filtre C121.
        source = read("air_planning.nut")
        pairs = function(source, "OpexAirPlansNewPairs").replace(
            'a == 0 && b == 1 && !(V278_AIR_LAZY_SITES && ("v278SinglePair" in ctx))',
            "a == 0 && b == 1")
        self.assertEqual(hashlib.sha256(pairs.encode()).hexdigest(), PAIRS_HASH)
        driver = function(source, "OpexAirPlans")
        self.assertEqual(hashlib.sha256(driver.encode()).hexdigest(), DRIVER_HASH)

    def test_population_potential_and_bounded_frontier(self):
        source = read("air_lazy_sites.nut")
        self.assertIn("OpexAirSortedTowns(pool)", source)
        self.assertIn("towns[a].pop.tofloat() * towns[b].pop", source)
        self.assertIn("a + 1 < towns.len()", source)
        self.assertIn("pair.b + 1 < lazy.towns.len()", source)
        self.assertIn("local pair = lazy.heap[0]", source)

    def test_extension_precedes_pop_and_preserves_probes(self):
        source = read("air_lazy_sites.nut")
        pairs = function(source, "OpexV278LazyPairs")
        self.assertLess(pairs.index("OpexV278ExtendSites"), pairs.index("OpexV278HeapPop"))
        self.assertIn("((pair.b / 8) + 1) * 8", pairs)
        self.assertIn("lazy.end = lazy.towns.len()", pairs)
        self.assertIn("scanProbes = lazy.probes", source)
        self.assertEqual(source.count("left = AIR_MAX_SITE_PROBES"), 1)
        self.assertIn("local scanEnd = limit;", read("air_planning.nut"))
        self.assertIn("probes.townsLeft = limit - i;", read("air_planning.nut"))

    def test_resume_and_progress(self):
        source = read("air_lazy_sites.nut")
        self.assertIn("scanIndex = lazy.covered", source)
        self.assertIn("rankIndex = 0, rankSites = []", source)
        self.assertIn("state.v278Lazy <- lazy", source)
        self.assertIn("if (progress && OpexV278BudgetSpent(ctx))", source)
        self.assertIn("work.sites = [siteA, siteB]", source)
        self.assertIn("OpexAirPlansNewPairs(work,", source)
        self.assertIn("if (lazy.pairsDone) return true", source)
        self.assertIn("delete ctx.resumeState.v278Lazy", read("air_planning.nut"))

    def test_targeted_repair_and_synchronous_paths_preserved(self):
        body = function(read("air_lazy_sites.nut"), "OpexV278LazyEnabled")
        self.assertIn("ctx.sliced && ctx.targetTownId < 0", body)
        self.assertIn('!("c83Repair" in ctx.resumeState)', body)

    def test_tick_proof_and_invalidation(self):
        source = read("air_coverage.nut")
        body = function(source, "OpexV278SiteOk")
        self.assertIn("AIController.GetTick() == memo.tick", body)
        self.assertIn("V278_AIR_VALIDITY == memo", body)
        self.assertIn("site.town.id in limited", body)
        self.assertIn("OpexAirSiteStillBuildable", body)
        self.assertNotIn("OpexAir0310SiteValidityBegin", body)
        for name in ("OpexAirResetSiteCache", "OpexAir0310InvalidateSiteValidity", "OpexAirInvalidateCachedSite"):
            self.assertIn("if (V278_AIR_LAZY_SITES) OpexV278InvalidateSites();", function(source, name))
        found = function(source, "OpexV278RememberFoundSite")
        for guard in ("GetTick() != started", "OpexAirRecoveryOwnsAirport", "c83SlotTown"):
            self.assertIn(guard, found)

    def test_prepare_dynamic_inputs_and_monthly_memos(self):
        prepare = function(read("air_planning.nut"), "OpexAirPlansPrepare")
        # v287 : V263b a retire les memos mensuels C80 ; plus rien a placer avant la reprise V278.
        self.assertNotIn("AIR_MEMO_MONTH", prepare)
        self.assertIn("OpexV278RestorePrepare", prepare)
        restore = function(read("air_lazy_sites.nut"), "OpexV278RestorePrepare")
        for guard in ("memo.catalog != ctx.catalog", "OpexV278LinesSignature", "V278_AIR_EPOCH", "AIController.GetTick()"):
            self.assertIn(guard, restore)
        for dynamic in ("state.bestPlan", "state.combo", "state.perfOpsSites", "state.c121EndpointCache", "infrastructure_maintenance"):
            self.assertIn(dynamic, restore)

    def test_transient_state_does_not_enter_save(self):
        self.assertNotIn("v278", read("persist.nut").lower())
        persist = read("persist.nut")
        self.assertNotIn("c78AirRebuild", persist)
        self.assertIn("taskDue[task.name] <- task.dueCycle", persist)


class TestV278Frontier(unittest.TestCase):
    def test_resume_after_every_operation_matches_uninterrupted_order(self):
        # Les rendus de main possibles sont materialises par step() ; reprendre
        # un etat copie ne doit ni depiler le sommet en attente ni rejouer une paire.
        import copy
        frontier = Frontier([1000] + list(range(30, 1, -1)))
        while frontier.step():
            frontier = copy.deepcopy(frontier)
        self.assertEqual(frontier.visited, sorted(frontier.visited))
        self.assertEqual(len(set(frontier.visited)), 30 * 29 // 2)

    def test_exhaustive_order_random_and_ties(self):
        rng = random.Random(278)
        for count in (0, 1, 2, 7, 8, 9, 16, 17, 64, 256):
            for _ in range(4):
                frontier = Frontier([rng.randint(1, 30) for _ in range(count)])
                while frontier.step():
                    self.assertLessEqual(len(frontier.heap), max(count - 1, 0))
                expected = sorted(frontier.pair(a, b) for a in range(count) for b in range(a + 1, count))
                self.assertEqual(frontier.visited, expected)
                self.assertEqual(frontier.covered, count)

    def test_extension_cannot_bypass_higher_potential_pair(self):
        frontier = Frontier([1000] + [10] * 7 + [9] * 9)
        while len(frontier.visited) < 8:
            frontier.step()
        self.assertEqual(frontier.visited[-1][1:], (0, 8))
        self.assertEqual(frontier.covered, 16)
        self.assertTrue(all(item[1] == 0 for item in frontier.visited))

    def test_initial_batch_and_resume_mid_extension(self):
        frontier = Frontier(range(1, 65))
        for _ in range(8):
            frontier.step()
            self.assertEqual(frontier.visited, [])
        self.assertEqual(frontier.covered, 8)
        frontier.step()
        self.assertEqual(len(frontier.visited), 1)
        self.assertEqual(frontier.covered, 8)

    def test_missing_sites_do_not_drop_other_pairs(self):
        frontier = Frontier([100, 99, 98, 97, 96, 95, 94, 93, 92], unavailable=(0, 7))
        while frontier.step():
            pass
        expected = [item for item in frontier.visited if item[1] not in (0, 7) and item[2] not in (0, 7)]
        self.assertEqual(frontier.evaluated, expected)
        self.assertEqual(len(frontier.visited), 36)

    def test_float_product_above_integer_limit(self):
        frontier = Frontier([100000, 99999, 80000])
        while frontier.step():
            pass
        self.assertEqual(-frontier.visited[0][0], 9999900000)


PAIRS_HASH = "13fc6cfea57750b91c9a927f944c90eb192460214df5f530a9b851caceb94058"  # v287 : NewPairs de master apres V263b (C80_AIR_EVAL_FAST retire)
DRIVER_HASH = "839151bc21f858e455f8021e54e8913dfe7f278421ec3ef1d086ec7ed9795b56"

if __name__ == "__main__":
    unittest.main()
