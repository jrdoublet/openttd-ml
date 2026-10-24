"""Contrats source et modele executable pour air_hub_cursor_keep (defaut 0).

Ne compile pas Squirrel et ne lance aucune partie OpenTTD.
Verifie :
- declaration et chargement unique de air_hub_cursor_keep (0..3, step 1, defaut 0) ;
- identite octet pour octet des fonctions modifiees apres retrait des seuls crochets opt-in ;
- bit 1 : maintien des curseurs a l'invalidation, rafraichissement des hubs/sites,
  gestion des indices hors bornes, borne explicite et terminaison du scan lorsque
  la signature topologique change a chaque pas ;
- filtres existants empechant toute republication/reconstruction d'une paire deja batie ;
- bit 2 : reselection au plus mensuelle dans _dispatchAirFleet quand airCount == 0
  et que la caisse depasse next_capital ou qu'aucun candidat n'est selectionne ;
- compatibilite Save/Load avec ou sans les nouveaux champs ;
- journaux AIR_HUB_CURSOR et FLEET_RESELECT strictement sous DECISION_LOG.
"""
from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"

RESERVED_IDENTIFIERS = (
    "clone", "base", "parent", "static", "delegate",
    "vargc", "vargv", "resume", "yield", "constructor", "instanceof",
)


def read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def function_body(text: str, signature: str) -> str:
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1 : pos]
    raise AssertionError(f"corps non ferme: {signature}")


def body(name: str, signature: str) -> str:
    return function_body(read(name), "function " + signature)


def clamp_and_bound_model(state: dict, num_sites: int, num_hubs: int,
                          action: str | None, keep_bit: bool,
                          max_hubs: int = 64, max_sites: int = 24,
                          max_steps: int = 3552) -> tuple[int, int]:
    """Modele exact de OpexAirHubCursorInvalidate + OpexAirHubCursorBeforeStore."""
    num_sites = min(max(num_sites, 0), max_sites)
    num_hubs = min(max(num_hubs, 0), max_hubs)
    if action == "invalidate":
        if keep_bit:
            state.setdefault("hubPhase", 0)
            state.setdefault("hubSiteI", 0)
            state.setdefault("hubSiteJ", 0)
            state.setdefault("hubHubI", 0)
            state.setdefault("hubHubJ", 1)
            state.setdefault("hubCursorSteps", 0)
        else:
            state["hubPhase"] = 0
            state["hubSiteI"] = 0
            state["hubSiteJ"] = 0
            state["hubHubI"] = 0
            state["hubHubJ"] = 1
            return num_sites, num_hubs

    if not keep_bit:
        return num_sites, num_hubs

    if action is None or action == "discover":
        state["hubCursorSteps"] = 0
        return num_sites, num_hubs

    steps = state.get("hubCursorSteps", 0) + 1
    state["hubCursorSteps"] = steps
    phase = max(state.get("hubPhase", 0), 0)
    site_i = max(state.get("hubSiteI", 0), 0)
    site_j = max(state.get("hubSiteJ", 0), 0)
    hub_i = max(state.get("hubHubI", 0), 0)
    hub_j = max(state.get("hubHubJ", 1), 1)

    if steps >= max_steps:
        phase = 1
        site_i = num_hubs
        site_j = 0
        hub_i = num_hubs
        hub_j = 0
    else:
        if phase < 1:
            if num_sites <= 0 or num_hubs <= 0:
                site_i = num_hubs
                site_j = 0
                phase = 1
            else:
                if site_j >= num_sites:
                    site_i += 1
                    site_j = 0
                if site_i >= num_hubs:
                    site_i = num_hubs
                    site_j = 0
                    phase = 1
        if phase >= 1:
            if hub_j <= hub_i:
                hub_j = hub_i + 1
            if num_hubs < 2:
                hub_i = num_hubs
                hub_j = 0
            else:
                if hub_j >= num_hubs:
                    hub_i += 1
                    hub_j = hub_i + 1
                if hub_i >= num_hubs - 1:
                    hub_i = num_hubs
                    hub_j = 0

    state["hubPhase"] = phase
    state["hubSiteI"] = site_i
    state["hubSiteJ"] = site_j
    state["hubHubI"] = hub_i
    state["hubHubJ"] = hub_j
    return num_sites, num_hubs


def run_hub_scan_slice(state: dict, hubs: list[int], sites: list[int],
                       sig: str, keep_bit: bool, pairs_per_slice: int = 1,
                       published: set[tuple[str, int, int]] | None = None) -> bool:
    """Simule une tranche de OpexAirPlansHubDiscoveryPhase + HubToSitePhase + HubToHub."""
    if published is None:
        published = set()
    snap = state.get("air0310HubSnap")
    if snap is not None and snap["sig"] == sig:
        action = "reuse"
        cur_hubs = list(snap["hubs"])
        cur_sites = list(snap["sites"])
    elif snap is not None:
        action = "invalidate"
        ns, nh = clamp_and_bound_model(state, len(sites), len(hubs), "invalidate", keep_bit)
        cur_sites = list(sites[:ns])
        cur_hubs = list(hubs[:nh])
        state["air0310HubSnap"] = {"sig": sig, "hubs": cur_hubs, "sites": cur_sites}
        state["air0310HubSkip"] = set(published)
    else:
        action = "discover"
        ns, nh = clamp_and_bound_model(state, len(sites), len(hubs), "discover", keep_bit)
        cur_sites = list(sites[:ns])
        cur_hubs = list(hubs[:nh])
        state["air0310HubSnap"] = {"sig": sig, "hubs": cur_hubs, "sites": cur_sites}

    skip = state.get("air0310HubSkip", set())
    budget_left = max(pairs_per_slice, 1)

    if state.get("hubPhase", 0) < 1:
        progressed = False
        resume_hub = state.get("hubSiteI", 0)
        resume_site = state.get("hubSiteJ", 0)
        for hi in range(resume_hub, len(cur_hubs)):
            start_sj = resume_site if hi == resume_hub else 0
            for sj in range(start_sj, len(cur_sites)):
                if progressed and budget_left <= 0:
                    state["hubSiteI"] = hi
                    state["hubSiteJ"] = sj
                    return False
                progressed = True
                budget_left -= 1
                assert 0 <= hi < len(cur_hubs)
                assert 0 <= sj < len(cur_sites)
                a, b = sorted((cur_hubs[hi], cur_sites[sj]))
                key = ("hubsite", a, b)
                if key in skip:
                    continue
                published.add(key)
        state["hubSiteI"] = len(cur_hubs)
        state["hubSiteJ"] = 0
        state["hubPhase"] = 1

    progressed = False
    resume_i = state.get("hubHubI", 0)
    resume_j = state.get("hubHubJ", 1)
    for i in range(resume_i, len(cur_hubs)):
        start_j = resume_j if i == resume_i else i + 1
        for j in range(start_j, len(cur_hubs)):
            if progressed and budget_left <= 0:
                state["hubHubI"] = i
                state["hubHubJ"] = j
                return False
            progressed = True
            budget_left -= 1
            assert 0 <= i < j < len(cur_hubs)
            a, b = sorted((cur_hubs[i], cur_hubs[j]))
            key = ("hubhub", a, b)
            if key in skip:
                continue
            published.add(key)
    state["hubHubI"] = len(cur_hubs)
    state["hubHubJ"] = 0
    return True


class TestAirHubCursor(unittest.TestCase):
    def test_off_paths_match_starting_branch_after_removing_only_opt_in_hooks(self):
        # Branche de depart air-load-guard (9b3bd86d).
        for name, signature, digest in (
            ("air_planning.nut", "OpexAir0310HubSnapshotPrepare(",
             "958f05e1cd4d1ae983abbe85c43ccd883ae4cdb60c0e6a4f0648460b597e7aec"),
            ("air_planning.nut", "OpexAir0310HubSnapshotStore(",
             "e63ebb956ca111221e66a2370a6da55c351a03459e536197a1fc748fff8374c1"),
            ("scheduler_tasks.nut", "OpexAI::_dispatchAirFleet(",
             "a4cfd26cc7e75cab0f7ce3264994857fb61b0383b6bfc10b3233f5bbefdfc267"),
        ):
            with self.subTest(name=name, signature=signature):
                code = body(name, signature)
                match = re.search(r"(?m)^ +if \(\(AIR_HUB_CURSOR_KEEP & [12]\) != 0[^\n]*\{", code)
                self.assertIsNotNone(match)
                inner = function_body(code[match.start():], "if (")
                end = code.index("{", match.start()) + len(inner) + 2
                self.assertEqual(code[end], "\n")
                code = code[:match.start()] + code[end + 1:]
                self.assertEqual(hashlib.sha256(code.encode("utf-8")).hexdigest(), digest)

    def test_setting_bounds_step_four_defaults_and_single_read(self):
        setting = re.search(r'AddSetting\(\{ name = "air_hub_cursor_keep",(.*?)\}\);',
                            read("info.nut"), re.S).group(1)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(level + "_value = 0", setting)
        self.assertIn("min_value = 0, max_value = 3, step_size = 1", setting)
        self.assertIn("flags = 0", setting)
        globals_pre = read("globals_pre.nut")
        self.assertIn("AIR_HUB_CURSOR_KEEP <- 0;", globals_pre)
        self.assertIn("AIR_FLEET_RESELECT_LAST_MONTH <- -1;", globals_pre)
        settings = read("settings.nut")
        self.assertEqual(settings.count('GetSetting("air_hub_cursor_keep")'), 1)
        self.assertIn("if (AIR_HUB_CURSOR_KEEP == null || AIR_HUB_CURSOR_KEEP < 0) AIR_HUB_CURSOR_KEEP = 0;", settings)
        self.assertIn("if (AIR_HUB_CURSOR_KEEP > 3) AIR_HUB_CURSOR_KEEP = 3;", settings)
        self.assertIn("AIR_FLEET_RESELECT_LAST_MONTH = -1;", settings)

    def test_bit1_invalidation_keeps_cursors_refreshes_and_bounds(self):
        inv = body("air_planning.nut", "OpexAirHubCursorInvalidate(")
        before_store = body("air_planning.nut", "OpexAirHubCursorBeforeStore(")
        prepare = body("air_planning.nut", "OpexAir0310HubSnapshotPrepare(")
        store = body("air_planning.nut", "OpexAir0310HubSnapshotStore(")
        discovery_phase = body("air_planning.nut", "OpexAirPlansHubDiscoveryPhase(")

        self.assertIn("delete resumeState.air0310HubSnap;", inv)
        self.assertIn("if ((AIR_HUB_CURSOR_KEEP & 1) != 0)", inv)
        self.assertIn('ctx.airHubCursorAction <- "keep";', inv)
        self.assertIn('ctx.airHubCursorAction <- "reset";', inv)
        self.assertIn("OpexAir0310RememberPublishedHubPairs(ctx, airport);", inv)
        self.assertIn('return "invalidate";', inv)

        # En mode invalidate, reuseHubs est faux donc DiscoverHubs et SnapshotStore rafraichissent hubs/sites.
        self.assertIn('reuseHubs = hubSnapAction == "reuse";', discovery_phase)
        self.assertIn("if (!reuseHubs)", discovery_phase)
        self.assertIn("OpexAirPlansDiscoverHubs(ctx, combo, airport, plane);", discovery_phase)
        self.assertIn("if (ctx.sliced) OpexAir0310HubSnapshotStore(ctx, comboIndex);", discovery_phase)
        self.assertIn("OpexAirHubCursorInvalidate(ctx, comboIndex, airport)", prepare)
        self.assertIn("OpexAirHubCursorBeforeStore(ctx, comboIndex)", store)

        # Bornes explicites et gestion des indices hors bornes.
        self.assertIn("const AIR_HUB_CURSOR_MAX_HUBS = 64;", read("air_planning.nut"))
        self.assertIn("const AIR_HUB_CURSOR_MAX_STEPS = 3552;", read("air_planning.nut"))
        for guard in (
            "ctx.sites.resize(AIR_HUB_NEW_SITE_POOL)",
            "ctx.hubs.resize(AIR_HUB_CURSOR_MAX_HUBS)",
            "steps >= AIR_HUB_CURSOR_MAX_STEPS",
            "if (siteJ >= numSites)",
            "if (siteI >= numHubs)",
            "if (hubJ >= numHubs)",
            "if (hubI >= numHubs - 1)",
        ):
            self.assertIn(guard, before_store)

    def test_scan_termination_when_signature_changes_every_step(self):
        hubs = [100 + i for i in range(6)]
        sites = [200 + j for j in range(8)]

        # A 0 : si la signature change a chaque tranche (budget=1 paire), le scan remet
        # sans cesse (hubSiteI, hubSiteJ) a (0, 0) et ne termine pas.
        state_off: dict = {}
        published_off: set = set()
        finished_off = False
        for step_idx in range(120):
            if run_hub_scan_slice(state_off, hubs, sites, f"sig:{step_idx}",
                                  keep_bit=False, pairs_per_slice=1, published=published_off):
                finished_off = True
                break
        self.assertFalse(finished_off)
        self.assertEqual((state_off["hubPhase"], state_off["hubSiteI"], state_off["hubSiteJ"]), (0, 0, 1))

        # Sous bit 1 : avec la meme signature qui change a chaque pas, le scan progresse
        # de facon strictement monotone, ne republie aucune paire deja admise et se termine.
        state_on: dict = {}
        published_on: set = set()
        steps_taken = 0
        for step_idx in range(500):
            steps_taken += 1
            if run_hub_scan_slice(state_on, hubs, sites, f"sig:{step_idx}",
                                  keep_bit=True, pairs_per_slice=1, published=published_on):
                break
        else:
            self.fail("Scan under bit 1 did not terminate")

        expected_pairs = len(hubs) * len(sites) + len(hubs) * (len(hubs) - 1) // 2
        # La derniere paire de HubToSite termine la boucle sans yield et chaine
        # immediatement la premiere paire de HubToHub dans la meme tranche : expected_pairs - 1 tranches.
        self.assertEqual(steps_taken, expected_pairs - 1)
        self.assertEqual(len(published_on), expected_pairs)
        self.assertEqual(state_on["hubPhase"], 1)
        self.assertEqual((state_on["hubHubI"], state_on["hubHubJ"]), (len(hubs), 0))

    def test_out_of_bounds_and_adversarial_hub_site_churn_terminate(self):
        # Le nombre de hubs et de sites fluctue (croissance et contraction) a chaque tranche
        # pendant que la signature change a chaque pas.
        state: dict = {}
        published: set = set()
        for step_idx in range(4000):
            nh = 1 + (step_idx * 7) % 90  # depasse parfois AIR_HUB_CURSOR_MAX_HUBS=64 ou tombe a 1
            ns = (step_idx * 5) % 30      # depasse parfois AIR_HUB_NEW_SITE_POOL=24 ou tombe a 0
            hubs = [1000 + i for i in range(nh)]
            sites = [2000 + j for j in range(ns)]
            if run_hub_scan_slice(state, hubs, sites, f"churn:{step_idx}",
                                  keep_bit=True, pairs_per_slice=1, published=published):
                self.assertLessEqual(step_idx + 1, 3553)
                break
        else:
            self.fail("Churn scan did not terminate within explicit bound")

    def test_existing_application_filters_prevent_duplicate_built_pairs(self):
        # 1. Pendant le scan : air0310HubSkip + alreadyConnected
        hub_site = body("air_planning.nut", "OpexAirPlansHubToSite(")
        hub_hub = body("air_planning.nut", "OpexAirPlansHubToHub(")
        self.assertIn('OpexAir0310SkipRestoredPair(ctx, airport, "hubsite", hub, null, site, plane)', hub_site)
        self.assertIn('OpexAir0310SkipRestoredPair(ctx, airport, "hubhub", hub1, hub2, null, plane)', hub_hub)
        self.assertIn("alreadyConnected = (st1 + \"|\" + st2) in hubIndex.pairs;", hub_hub)

        # 2. A la reselection / publication : OpexFilterAirAlternativesStillValid / V279Memo
        reselect = body("projects_selection.nut", "OpexReselectProjects(")
        self.assertIn("OpexFilterAirAlternativesV279Memo(alternatives, abandonedPairs, lines)", reselect)
        self.assertIn("OpexFilterAirAlternativesStillValid(alternatives, abandonedPairs, lines)", reselect)

        # 3. A l'execution du chantier : OpexAirBatchPlanStillLive verifie les lignes existantes et capacites
        live = body("task_air.nut", "OpexAirBatchPlanStillLive(")
        self.assertIn("local servedA = OpexAirTownServed(plan.siteA.town, lines);", live)
        self.assertIn("local servedB = OpexAirTownServed(plan.siteB.town, lines);", live)
        self.assertIn("if (reuseA && !OpexAirBatchHubHasCapacity(plan.siteA.anchor, plan.plane, lines)) return false;", live)
        self.assertIn("if (reuseB && !OpexAirBatchHubHasCapacity(plan.siteB.anchor, plan.plane, lines)) return false;", live)
        self.assertIn("if ((line.originA == plan.siteA.town.tile && line.originB == plan.siteB.town.tile) ||", live)
        try_air = body("task_air.nut", "OpexAI::_tryBuildAirProject(")
        self.assertIn("if (!OpexAirBatchPlanStillLive(plan, this._lines))", try_air)

    def test_bit2_fleet_reselect_conditions_and_monthly_cadence(self):
        dispatch = body("scheduler_tasks.nut", "OpexAI::_dispatchAirFleet(")
        helper = body("scheduler_tasks.nut", "OpexAI::_maybeReselectIdleAirFleet(")
        self.assertIn("if ((AIR_HUB_CURSOR_KEEP & 2) != 0 && airCount == 0)", dispatch)
        self.assertIn("this._maybeReselectIdleAirFleet(year);", dispatch)

        for fragment in (
            "if ((AIR_HUB_CURSOR_KEEP & 2) == 0 || this._projects == null) return;",
            "local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());",
            "if (AIR_FLEET_RESELECT_LAST_MONTH == ym) return;",
            'reason = "no_selected";',
            "else if (nextCap > 0 && budgetNow > nextCap)",
            'reason = "cash_above_next";',
            "if (reason == null) return;",
            "AIR_FLEET_RESELECT_LAST_MONTH = ym;",
            "OpexReselectProjects(\n      this._projects, budgetNow, this._abandonedPairs, this._lines);",
            "this._ranked = this._projects.rail;",
        ):
            self.assertIn(fragment, helper)
        # Le verrou mensuel ne doit etre pose qu'apres validation d'une raison de reselection.
        self.assertLess(helper.index("if (reason == null) return;"),
                        helper.index("AIR_FLEET_RESELECT_LAST_MONTH = ym;"))

    def test_decision_log_gating_and_formats(self):
        before_store = body("air_planning.nut", "OpexAirHubCursorBeforeStore(")
        helper = body("scheduler_tasks.nut", "OpexAI::_maybeReselectIdleAirFleet(")

        self.assertIn("if (DECISION_LOG && action != null)", before_store)
        self.assertIn(
            'OpexDecide("AIR_HUB_CURSOR", "action=" + action\n'
            '        + " combo=" + comboIndex\n'
            '        + " phase=" + logPhase\n'
            '        + " siteI=" + logSiteI\n'
            '        + " hubI=" + logHubI\n'
            '        + " sites=" + logSites\n'
            '        + " hubs=" + logHubs);',
            before_store,
        )
        self.assertIn("if (DECISION_LOG)", helper)
        self.assertIn(
            'OpexDecide("FLEET_RESELECT", "reason=" + reason\n'
            '        + " cash=" + budgetNow\n'
            '        + " next_capital=" + nextCap);',
            helper,
        )

    def test_save_load_compatibility_with_or_without_new_fields_and_squirrel_traps(self):
        persist = read("persist.nut")
        self.assertNotIn("AIR_FLEET_RESELECT_LAST_MONTH", persist)
        self.assertNotIn("hubCursorSteps", persist)
        self.assertNotIn("c78AirRebuild", persist)

        # Etat de scan restaure sans erreur avec ou sans hubCursorSteps / hubPhase / hubSiteI / hubHubI
        empty_state: dict = {}
        clamp_and_bound_model(empty_state, 5, 3, "invalidate", keep_bit=True)
        self.assertEqual(empty_state["hubPhase"], 0)
        self.assertEqual(empty_state["hubSiteI"], 0)
        self.assertEqual(empty_state["hubHubJ"], 1)
        self.assertEqual(empty_state["hubCursorSteps"], 1)

        with_fields = {
            "hubPhase": 0, "hubSiteI": 1, "hubSiteJ": 4,
            "hubHubI": 0, "hubHubJ": 1, "hubCursorSteps": 7,
        }
        clamp_and_bound_model(with_fields, 3, 3, "invalidate", keep_bit=True)
        self.assertEqual((with_fields["hubPhase"], with_fields["hubSiteI"], with_fields["hubSiteJ"]), (0, 2, 0))
        self.assertEqual(with_fields["hubCursorSteps"], 8)

        # Pieges Squirrel sur les nouvelles fonctions
        for fname, sig in (
            ("air_planning.nut", "OpexAirHubCursorInvalidate("),
            ("air_planning.nut", "OpexAirHubCursorBeforeStore("),
            ("scheduler_tasks.nut", "OpexAI::_maybeReselectIdleAirFleet("),
        ):
            code = body(fname, sig)
            self.assertNotIn(".find(", code)
            self.assertNotIn(".Valuate(", code)
            self.assertNotIn("function(", code)
            tokens = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", code))
            for reserved in RESERVED_IDENTIFIERS:
                self.assertNotIn(reserved, tokens)


if __name__ == "__main__":
    unittest.main()
