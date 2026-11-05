"""RAIL-LONG opt-in: platform, wagon, physical fleet and strict OFF contracts.

Pure Python behavioral model for decisions that need OpenTTD to exercise the
Squirrel calls; the source assertions make sure the model matches production.
OFF projection removes only this worker's opt-in hunks, without reverting any
other concurrent worktree changes or touching on-disk files.
"""
import hashlib
import re
import unittest
from pathlib import Path

from rail_long_source_off import off_source as rail_long_off_source
from rail_long_v2_off import off_source as rail_long_v2_off
from rail_long_merged_off import _manifest as merged_witnesses


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    # Les contrats historiques v1 s'appliquent aux sources après soustraction
    # exacte de v2 ; ils ne sont pas réécrits pour tolérer un comportement v1 altéré.
    return rail_long_v2_off(name, (AI / name).read_text(encoding="utf-8"))


def project_off(name):
    """Reconstruct pre-RAIL-LONG bytes for the three owned Squirrel files."""
    assert name in {"builder_rail.nut", "economy.nut", "task_rail.nut"}
    return rail_long_off_source(name, source(name))


def long_site_target(*, enabled, freight, monthly, short_capacity,
                     current_length, station_spread, max_train_length,
                     dedicated_long_good=False, wagon_capacity=20):
    if not enabled or not freight or dedicated_long_good or short_capacity <= 0:
        return 0
    if monthly < 1.5 * short_capacity or current_length >= 6:
        return 0
    limit = min(station_spread, max_train_length) if max_train_length > 0 else station_spread
    if limit < 6:
        return 0
    for length in range(min(7, limit), 5, -1):
        if monthly * 3 >= (2 * length - 1) * wagon_capacity:
            return length
    return 0


def choose_platform(target, historical, both_sites, positive_economics):
    if target >= 6:
        for length in range(target, 5, -1):
            if length in both_sites and length in positive_economics:
                return length
    return next((length for length in range(historical, 0, -1)
                 if length in both_sites), None)


def long_wagon_target(enabled, freight, long_site_chosen, fixed_length,
                      max_wagons, old_corrected):
    if enabled and freight and long_site_chosen and fixed_length >= 6:
        return max_wagons
    return old_corrected


class RailLongBehavior(unittest.TestCase):
    def test_config_owned_by_worker_3_is_off_at_every_difficulty(self):
        self.assertRegex(source("globals_pre.nut"), r"(?m)^RAIL_LONG\s*<-\s*false;")
        self.assertEqual(source("settings.nut").count('GetSetting("rail_long")'), 1)
        config = re.search(r'name = "rail_long",(.*?)\}\);', source("info.nut"), re.S)
        self.assertIsNotNone(config)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 0", config.group(1))

    def test_station_length_and_short_capacity_threshold(self):
        common = dict(enabled=True, freight=True, current_length=3,
                      monthly=361, short_capacity=240, station_spread=12,
                      max_train_length=7)
        self.assertEqual(long_site_target(**common), 7)
        self.assertEqual(long_site_target(**(common | {"max_train_length": 6})), 6)
        self.assertEqual(long_site_target(**(common | {"station_spread": 5})), 0)
        self.assertEqual(long_site_target(**(common | {"monthly": 359})), 0)
        self.assertEqual(long_site_target(**(common | {"current_length": 6})), 0)
        self.assertEqual(long_site_target(**(common | {"monthly": 126, "short_capacity": 60, "wagon_capacity": 30})), 6)
        self.assertEqual(long_site_target(**(common | {"monthly": 100, "short_capacity": 60, "wagon_capacity": 30})), 0)
        self.assertEqual(long_site_target(**(common | {"enabled": False})), 0)
        self.assertEqual(long_site_target(**(common | {"freight": False})), 0)
        self.assertEqual(long_site_target(**(common | {"dedicated_long_good": True})), 0)
        module = source("builder_rail.nut")
        self.assertIn('candidate.monthly.tofloat() < 1.5 * candidate.railLongShortCapacity', module)
        self.assertIn('candidate.railLongShortCapacity <- candidate.perTrain;', module)
        self.assertIn('catalog.maxTrainLength < limit', module)
        self.assertIn('candidate.monthly.tofloat() * 3.0 >= trainCapacity', module)
        self.assertIn('OpexRailNominalMaxWagons(length)', module)

    def test_tries_both_long_platforms_before_historical_fallback(self):
        self.assertEqual(choose_platform(7, 3, {7, 6, 3}, {7, 6}), 7)
        self.assertEqual(choose_platform(7, 3, {6, 3}, {6}), 6)
        self.assertEqual(choose_platform(7, 3, {7, 3}, set()), 3)
        self.assertEqual(choose_platform(7, 3, {3}, {7, 6}), 3)
        self.assertEqual(choose_platform(0, 3, {3}, set()), 3)
        module = source("builder_rail.nut")
        self.assertLess(module.index('for (local length = railLongLength; length >= 6; length--)'),
                        module.index('for (local length = wanted; length >= floor; length--)'))
        self.assertIn('local longer = OpexRailTryPlatformLength(catalog, candidate, length, statsA, statsB);',
                      module)
        self.assertIn('quote.profitAnnual > 0 && quote.roi > 0', module)
        self.assertIn('OpexAvailableCapital() >= longCashNeed', module)
        self.assertIn('OpexV163CandidateSecondary(candidate)', module)

    def test_route_failure_retries_historical_length_at_most_once(self):
        builder = source("builder_rail.nut")
        task = source("task_rail.nut")
        self.assertIn('candidate.railLongOriginalLength <- wanted;', builder)
        self.assertIn('wanted = candidate.railLongOriginalLength;', builder)
        self.assertIn('("railLongShortRetry" in candidate) && candidate.railLongShortRetry', builder)
        self.assertIn('RAIL_LONG && slice.stop != "OK"', task)
        self.assertIn('shortCandidate.railLongShortRetry <- true;', task)
        self.assertIn('this._startRailSearch(shortCandidate, state.alternativeRatio, state.hardCap, state.posPacked);', task)
        self.assertLess(task.index('shortCandidate.railLongShortRetry <- true;'),
                        task.index('this._startRailSearch(shortCandidate, state.alternativeRatio, state.hardCap, state.posPacked);'))

    def test_full_consist_needs_economic_volume_and_physical_cap(self):
        self.assertEqual(long_wagon_target(True, True, True, 7, 13, 5), 13)
        self.assertEqual(long_wagon_target(True, True, False, 7, 13, 5), 5)
        self.assertEqual(long_wagon_target(True, True, True, 5, 13, 5), 5)
        self.assertEqual(long_wagon_target(False, True, True, 7, 13, 5), 5)
        economics = source("economy.nut")
        self.assertIn('(RAIL_LONG && kind == "freight")', economics)
        self.assertIn('RAIL_LONG && railLongFill && kind == "freight"', economics)
        self.assertIn('correctedWagons = maxWagons;', economics)
        self.assertLess(economics.index('correctedWagons = maxWagons;'),
                        economics.index('if (correctedWagons != wagons)'))
        self.assertIn('RAIL_CONSIST_PCT > 100 && kind != "pax"', economics)
        builder = source("builder_rail.nut")
        self.assertIn('candidate.railLongChosen = true;', builder)
        self.assertIn('OpexV163CandidateSecondary(candidate), false, true);', builder)
        self.assertEqual(builder.count('("railLongChosen" in candidate) && candidate.railLongChosen);'), 2)

    def test_multitrain_requires_directional_pbs_certification_and_shared_orders(self):
        directional = source("v190_fix_directional.nut")
        self.assertIn('if (!ok || count1 < 1 || count2 < 1)', directional)
        self.assertIn('AIRail.SIGNALTYPE_PBS_ONEWAY', directional)
        builder = source("builder_rail.nut")
        self.assertIn('if (v190Directional) result.v190Directional <- true;', builder)
        self.assertIn('if (!OpexV233LIs(candidate) && !v190Directional) result.v190Independent <- true;', builder)
        task = source("task_rail.nut")
        allowed = task[task.index('function OpexRailLongCanShareOrders('):
                       task.index('function OpexRailLongGrowFleet(')]
        for item in ('line.v190Directional', 'line.v181Loop', 'line.v190Independent',
                     'line.doubleTrack != 1', 'AIOrder.IsGotoWaypointOrder(modelTrain, 1)',
                     'AIOrder.IsGotoWaypointOrder(modelTrain, 3)',
                     'AIOrder.OF_FULL_LOAD_ANY', 'AIOrder.GetOrderFlags(vehicle, order)'):
            self.assertIn(item, allowed)
        growth = task[task.index('function OpexRailLongGrowFleet('):
                      task.index('function OpexAI::_expandRailLines(')]
        for item in ('AIStation.GetCargoWaiting(station, line.cargo)',
                     'waiting.tofloat() < capacity * 1.5',
                     'AIVehicle.CloneVehicle(depot, line.vehicles[0], true)',
                     'AIOrder.ShareOrders(line.vehicles[i], line.vehicles[0])',
                     'AIOrder.SkipToOrder(extra, 0)',
                     'AIVehicle.StartStopVehicle(extra)', 'line.vehicles.append(extra)',
                     'OpexRailVehicleSlotAvailable()'):
            self.assertIn(item, growth)
        self.assertIn('if (RAIL_LONG && line.platformLength >= 6)', task)
        self.assertIn('if (OpexRailLongGrowFleet(this._catalog, line)) return;', task)
        self.assertIn('backlogThreshold = line.wagons * wagon.capacity * 1.5;', task)
        self.assertIn('railLongBuilt.railLong <- true;', task)
        self.assertIn('railLongBuilt.wagons = physicalWagons;', task)
        self.assertIn('OpexDecide("RAIL_LONG", "event=build line="', task)

    def test_save_load_no_new_pending_state(self):
        task = source("task_rail.nut")
        self.assertIn('line.vehicles.append(extra);', task)
        self.assertIn('line.trains = line.vehicles.len();', task)
        persistence = source("persist.nut")
        self.assertIn('local serializableLine = clone line;', persistence)
        self.assertIn('projectedLines.append(OpexSaveProjectLine(line));', persistence)
        self.assertIn('line.vehicles = liveVehicles;', persistence)
        self.assertNotIn('railLongPending', task)

    def test_off_projection_exact_hash_and_idempotence(self):
        # Frozen from the shared dirty worktree *before* this worker's changes,
        # not from HEAD (HEAD lacks unrelated authorized concurrent edits).
        expected = {
            "builder_rail.nut": "c6444cb274f2614659b30c1abb655261cee01cc7dec81a24f2b9a2f20a491eba",
            "economy.nut": "b51347bb0af25402c5027b066f238bcd4b4f8665c5b6029743432406a1c8a454",
            "task_rail.nut": "1308bcea98fca9ed7edd4a97ad804ca88a63c319aa047ecf46ec23e8d28915e5",
        }
        merged = 'name = "road1y_load_orders"' in (AI / "info.nut").read_text(encoding="utf-8")
        witnessed = merged_witnesses()["v1"] if merged else {}
        for name, digest in expected.items():
            with self.subTest(file=name):
                projection = project_off(name)
                self.assertNotIn('function OpexRailLongSiteLength(', projection)
                self.assertNotIn('function OpexRailLongGrowFleet(', projection)
                self.assertNotIn('(RAIL_LONG && kind == "freight")', projection)
                # The old hashes still describe 03/11 RAIL-only bytes;
                # ROAD1Y+RAIL has separate, fixed OFF witnesses.
                merged_digest = witnessed[name]["off_sha256"] if merged else digest
                self.assertEqual(hashlib.sha256(projection.encode("utf-8")).hexdigest(),
                                 merged_digest)
                if merged:
                    self.assertEqual(witnessed[name]["historical_off_sha256"], digest)
                    self.assertNotEqual(merged_digest, digest)
                self.assertEqual(rail_long_off_source(name, projection), projection)

    def test_off_projection_fail_closed_when_partially_removed(self):
        for name, hunk in (
            ("builder_rail.nut", "  local railLongLength = OpexRailLongSiteLength(catalog, candidate);\n"),
            ("economy.nut", "  /* RAIL-LONG : le site 6/7"),
            ("task_rail.nut", "          /* Sur les quais RAIL-LONG"),
        ):
            with self.subTest(file=name):
                damaged = source(name).replace(hunk, "", 1)
                with self.assertRaises(AssertionError):
                    rail_long_off_source(name, damaged)

    def test_projection_composes_with_frozen_preexisting_options(self):
        from rail_consist_legacy import off_source as consist_off
        from v190_fix_directional_legacy import off_source as directional_off
        from test_rail_search_prio_source_off import (
            FROZEN_OFF_SHA256, OFF_EDITS, off_search_prio_source,
        )
        # Keep every old frozen digest unchanged: RAIL-LONG is removed first.
        old_task = project_off("task_rail.nut")
        merged = 'name = "road1y_load_orders"' in (AI / "info.nut").read_text(encoding="utf-8")
        if merged:
            # SEARCH-PRIO's legacy projector would unnecessarily call the
            # already-subtracted INVEST-STALL platform layer again. Apply
            # exactly its frozen hunks at unique anchors on this reviewed
            # merged stage, then verify the dedicated composite SHA.
            before_prio = old_task
            for active, prior, count in sorted(OFF_EDITS["task_rail.nut"],
                                                key=lambda row: -len(row[0])):
                self.assertEqual(before_prio.count(active), count)
                before_prio = before_prio.replace(active, prior)
            merged_sha = merged_witnesses()["v1"]["task_rail.nut"]["search_prio_after_v1_sha256"]
            self.assertEqual(hashlib.sha256(before_prio.encode("utf-8")).hexdigest(), merged_sha)
            self.assertNotEqual(merged_sha, FROZEN_OFF_SHA256["task_rail.nut"])
            self.assertEqual(rail_long_off_source("task_rail.nut", before_prio), before_prio)
        else:
            before_prio = off_search_prio_source("task_rail.nut", old_task)
            self.assertEqual(hashlib.sha256(before_prio.encode("utf-8")).hexdigest(),
                             FROZEN_OFF_SHA256["task_rail.nut"])
        before_directional = directional_off("task_rail.nut", old_task)
        self.assertEqual(directional_off("task_rail.nut", before_directional),
                         before_directional)
        old_economy = project_off("economy.nut")
        before_consist = consist_off("economy.nut", old_economy)
        self.assertEqual(consist_off("economy.nut", before_consist), before_consist)

    def test_new_squirrel_has_no_common_parser_traps(self):
        for name in ("builder_rail.nut", "economy.nut", "task_rail.nut"):
            with self.subTest(file=name):
                content = source(name)
                self.assertEqual(content.count("{"), content.count("}"))
        for part in (
            source("builder_rail.nut")[source("builder_rail.nut").index('function OpexRailLongSiteLength('):
                                       source("builder_rail.nut").index('function OpexRailSiteReason(')],
            source("task_rail.nut")[source("task_rail.nut").index('function OpexRailLongCanShareOrders('):
                                     source("task_rail.nut").index('function OpexAI::_expandRailLines(')]
        ):
            self.assertNotIn('.find(', part)
            self.assertNotIn('function(', part)
            for reserved in ("base", "clone", "parent", "static", "yield", "resume"):
                self.assertNotRegex(part, rf"\blocal\s+{reserved}\s*=")


if __name__ == "__main__":
    unittest.main()
