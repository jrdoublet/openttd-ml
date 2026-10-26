#!/usr/bin/env python3
"""Contrat V158 : publication AIR avec resélection paresseuse (optimisation d'opcodes).

Vérifications statiques :
1. Réglage air_publish_lazy_select à 0 par défaut (les 4 difficultés à 0),
   globale AIR_PUBLISH_LAZY_SELECT dans globals_pre.nut et settings.nut.
2. Pose de projects.selectionStale dans OpexAir0310PublishIncremental quand le réglage est actif.
3. Effacement de projects.selectionStale au début d'OpexReselectProjects et dans OpexIncrementalUpdateProjects.
4. Définition d'OpexEnsureSelection(owner) et OpexAI::_ensureSelection().
5. Compteurs sous DECISION_LOG : AIR_LAZY_SELECT dans le rapport annuel.
6. Audit exhaustif des lecteurs de .best hors projects_selection.nut :
   chaque accès est soit protégé par une garde (_ensureSelection / OpexEnsureSelection)
   dans la même fonction, soit sur une liste blanche documentée (fonctions internes
   appelées exclusivement depuis un point déjà protégé, sous-structures par mode, oracles, tests).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _body(source: str, signature: str) -> str:
    start = source.index(signature)
    depth = 0
    for pos in range(source.index("{", start), len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start : pos + 1]
    raise AssertionError(signature)


class TestV158SettingsAndGlobals(unittest.TestCase):
    def test_setting_declaration(self):
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('air_publish_lazy_select',))

    def test_global_pre(self):
        globals_pre = _read("globals_pre.nut")
        self.assertNotIn("AIR_PUBLISH_LAZY_SELECT <- 0;", globals_pre)

    def test_settings_load(self):
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('air_publish_lazy_select',))

    def test_main_members(self):
        main = _read("main.nut")
        self.assertIn("_lazyPubsYear = 0;", main)
        self.assertIn("_lazyDeferredYear = 0;", main)
        self.assertIn("_lazyMaterializedYear = 0;", main)
        self.assertIn("function _ensureSelection();", main)
        self.assertIn("function _logAirLazySelect(year);", main)


class TestV158LazySelectionMechanism(unittest.TestCase):
    def test_incremental_publish_sets_stale(self):
        update = _read("projects_update.nut")
        body = _body(update, "function OpexAir0310PublishIncremental(")
        self.assertNotIn("AIR_PUBLISH_LAZY_SELECT", body)
        self.assertIn("projects.selectionStale = true", body)
        self.assertIn("_lazyDeferredYear", body)
        self.assertIn("_lazyPubsYear", body)

    def test_reselect_clears_stale(self):
        sel = _read("projects_selection.nut")
        body = _body(sel, "function OpexReselectProjects(")
        self.assertIn("selectionStale", body)
        self.assertIn("projects.selectionStale = false", body)

    def test_incremental_update_clears_stale(self):
        update = _read("projects_update.nut")
        body = _body(update, "function OpexIncrementalUpdateProjects(")
        self.assertIn("projects.selectionStale = false", body)

    def test_ensure_selection_defined(self):
        sel = _read("projects_selection.nut")
        body = _body(sel, "function OpexEnsureSelection(owner)")
        self.assertIn("selectionStale", body)
        self.assertIn("OpexReselectProjects", body)
        self.assertIn("_lazyMaterializedYear", body)
        self.assertIn("owner._ranked =", body)

    def test_opex_ai_ensure_selection(self):
        tp = _read("task_projects.nut")
        body = _body(tp, "function OpexAI::_ensureSelection()")
        self.assertIn("OpexEnsureSelection(this);", body)

    def test_decision_log_counter(self):
        report = _read("task_report.nut")
        body = _body(report, "function OpexAI::_logAirLazySelect(year)")
        self.assertIn('OpexDecide("AIR_LAZY_SELECT"', body)
        self.assertIn("pubs=", body)
        self.assertIn("deferred=", body)
        self.assertIn("materialized=", body)

        sched = _read("scheduler_tasks.nut")
        report_body = _body(sched, "function OpexAI::_dispatchReport(task, year)")
        self.assertIn("this._logAirLazySelect(year);", report_body)


class TestV158BestReadersAudit(unittest.TestCase):
    """Audit exhaustif de chaque lecture de .best hors projects_selection.nut."""

    WHITELIST_JUSTIFICATIONS = {
        # Fichier air_planning.nut : champs locaux sur structures de routes/résultats du scan
        "air_planning.nut": "Champs locaux result.best / route.best dans le moteur de recherche de lignes AIR",
        # Fichier candidates.nut : ensemble candidat par mode
        "candidates.nut": "Champ set.best dans la sélection top-K par mode",
        # Fichier projects.nut : sous-table par mode (rail.best, road.best, base.best)
        "projects.nut": "Sous-tables de classement par mode (rail.best, road.best, base.best)",
        # Fichier rail_prep_c121.nut : résultat d'une sous-construction
        "rail_prep_c121.nut": "Champ built.best sur le retour direct d'une sous-construction",
        # Fichier selftests.nut : tests unitaires Squirrel sur mocks
        "selftests.nut": "Mocks synthétiques de tests unitaires",
        # Fichier projects_diagnostics.nut : oracle de fraîcheur C66/B6 lors d'un rebuild
        "projects_diagnostics.nut": "Oracle de fraîcheur b6StaleProjects comparé au nouveau portefeuille dans _rebuildProjects",
        # Fichier projects_update.nut : assignation de projects.best dans OpexIncrementalUpdateProjects
        "projects_update.nut": "Assignation projects.best = funded dans le producteur incrémental",
        # Sous-fonctions de task_projects.nut appelées exclusivement dans _tryBuildProjects
        "task_projects.nut:OpexAI::_recordMonthlyFunnelPass": "Appelé exclusivement en fin de _tryBuildProjects (déjà matérialisé)",
        "task_projects.nut:OpexC121FirstLiveAirOpportunity": "Appelé exclusivement dans la boucle de passage de _tryBuildProjects",
        "task_projects.nut:OpexRailOriginReuseAirOpportunity": "Appelé exclusivement dans la boucle de passage de _tryBuildProjects",
        "task_projects.nut:OpexC121KPassShadow": "Appelé exclusivement dans la boucle de passage de _tryBuildProjects",
        "task_projects.nut:OpexAirC83FundedRaceCoversTown": "Appelé exclusivement dans _c83WatchAirSlotTransitions via _tryBuildProjects",
        "task_projects.nut:OpexC122ThreatFundedMatch": "Appelé exclusivement dans _c83WatchAirSlotTransitions via _tryBuildProjects",
        "task_projects.nut:OpexC122ThreatRegister": "Appelé exclusivement dans _c83WatchAirSlotTransitions via _tryBuildProjects",
        "task_projects.nut:OpexC122ThreatRefreshFunded": "Appelé exclusivement dans _c83WatchAirSlotTransitions via _tryBuildProjects",
        "task_projects.nut:OpexAI::_projectsRankOfAttemptKey": "Appelé exclusivement dans _consumeResumableRailAtPassStart via _tryBuildProjects",
        "task_projects.nut:OpexAI::_recordPortfolioProjectBuilt": "Appelé exclusivement après succès de construction dans _tryBuildProjects",
        "task_projects.nut:OpexAI::_consumeResumableRailAtPassStart": "Appelé exclusivement en tête de _tryBuildProjects",
        "task_projects.nut:OpexAI::_c83WatchAirSlotTransitions": "Appelé exclusivement dans _tryBuildProjects (après _ensureSelection)",
        "task_projects.nut:OpexAI::_c39StampFinanceable": "Appelé depuis _dispatchProjects (protégé) et post-rebuild",
        "task_projects.nut:OpexAI::_rebuildProjects": "Fin de rebuild complet (OpexBuildProjects a fraîchement sélectionné)",
        # Sous-fonctions de task_air.nut appelées exclusivement depuis _tryBuildProjects
        "task_air.nut:OpexAI::_tryBuildAirProject": "Appelé exclusivement depuis la boucle de passage de _tryBuildProjects",
        # Sous-fonctions de task_report.nut appelées exclusivement depuis _dispatchReport ou post-rebuild
        "task_report.nut:OpexAI::_reportYear": "Appelé exclusivement dans _dispatchReport (protégé par _ensureSelection)",
        "task_report.nut:OpexAI::_reportC78Candidates": "Appelé exclusivement dans _dispatchReport (protégé par _ensureSelection)",
        "task_report.nut:OpexAI::_c76LogAnnualReport": "Appelé exclusivement dans _dispatchReport (protégé par _ensureSelection)",
        "task_report.nut:OpexAI::_c76RecordRegen": "Appelé exclusivement après _rebuildProjects ou OpexRegenerateModeProjects (sélection fraîche)",
        # Ledgers post-dispatch et probes de fin de passe
        "ledgers.nut:OpexAI::_schedIdlePostDispatch": "Sonde post-exécution : le passage projects a déjà matérialisé la sélection",
        "ledgers.nut:OpexAI::_recordC69BuildingPass": "Appelé exclusivement en fin de passe dans _tryBuildProjects (déjà matérialisé)",
        "ledgers.nut:OpexC69OnProjectsPass": "Sonde passive appelée en toute fin de _tryBuildProjects (déjà matérialisé)",
        # Probes passives appelées dans _tryBuildProjects ou après rebuild
        "probes.nut:OpexC78FundedRank": "Appelé dans _c78SlotOnProjectsPass depuis _tryBuildProjects (déjà matérialisé)",
        "probes.nut:OpexV309IdleProjects": "V309 sonde passive : lit la derniere selection sans la rematerialiser, pour ne pas deplacer son cout",
        "probes.nut:OpexC39ProjectSignature": "Appelé dans events.nut (protégé) et orchestrator.nut:1292 (post-rebuild)",
        "air_flotte1_shadow.nut:OpexAirF1Before": (
            "Sonde passive : renfort depuis _tryBuildProjects apres _ensureSelection ; "
            "renouvellement V252 photographie la liste sans garantir sa fraicheur "
            "(selection_is_live=unverified), sans reclasser ni choisir un achat"
        ),
        # Fichier projects_rank_log.nut : loggers de classement (appelés post-rebuild ou en fin de passe)
        "projects_rank_log.nut": "Loggers du classement de tête appelés post-rebuild ou post-construction",
        # Sous-fonctions de task_rail.nut appelées exclusivement depuis _tryBuildProjects
        "task_rail.nut:OpexAI::_tryBuildRailProject": "Appelé exclusivement depuis _tryBuildProjects (_buildCandidate)",
        # Post-rebuild / post-reselect directs
        "orchestrator.nut:OpexAI::_c76DoFullRegen": "Exécuté immédiatement après _rebuildProjects (resélection fraîche)",
        "scheduler_tasks.nut:OpexAI::_dispatchCatalog": "Exécuté immédiatement après _rebuildProjects ou OpexReselectProjects",
        "scheduler_tasks.nut:OpexP6FirstlineWindowHold": (
            "P6 opt-in : appele exclusivement dans _tryBuildProjects, "
            "immediatement apres _ensureSelection, avant toute construction"
        ),
        "task_v249.nut:OpexV249MaxListedCapital": "V249 : borne de garde (capital max listé) ; une liste périmée suffit, pas de resélection pour ne pas déplacer son coût",
        "task_v249.nut:OpexV249BestAdmissibleCapital": "V249 mode 2 : meilleur projet admissible et finançable dans projects.best sans resélection",
    }

    def _find_enclosing_function(self, content: str, pos: int) -> str:
        # Search backwards for function declaration
        sub = content[:pos]
        matches = list(re.finditer(r"\bfunction\s+([A-Za-z0-9_:]+)\s*\(", sub))
        if matches:
            return matches[-1].group(1)
        return "<global>"

    def test_shadow_best_reader_call_sites_and_passive_snapshot(self):
        projects = _read("task_projects.nut")
        pass_body = _body(projects, "function OpexAI::_tryBuildProjects(year)")
        fleet_body = _body(projects, "function OpexAI::_tryBuildFleetProject(")
        renewal = _body(_read("task_v252.nut"),
                        "function OpexAI::_dispatchV252AirEngineRefresh(")
        shadow = _body(_read("air_flotte1_shadow.nut"), "function OpexAirF1Before(")

        # Renfort : selection materialisee avant invocation unique de flotte.
        self.assertLess(pass_body.index("this._ensureSelection();"),
                        pass_body.index("this._tryBuildFleetProject("))
        self.assertIn('OpexAirF1Before(this, "reinforce"', fleet_body)
        self.assertEqual(projects.count("this._tryBuildFleetProject("), 1)

        # V252 ne reselecte pas avant le diagnostic ; seuil de caisse preexistant.
        self.assertLess(renewal.index("OpexV249MaxListedCapital(this._projects)"),
                        renewal.index('OpexAirF1Before(this, "renewal"'))
        self.assertIn("selection_is_live=unverified", shadow)
        self.assertIn('OpexAirF1Queue(logs, "AIRF1_LIST"', shadow)
        self.assertNotIn("OpexReselectProjects(", shadow)
        self.assertIn("return { id = id, tick = tick, cash = cash, logs = logs };", shadow)

        # Toute invocation supplementaire exige une revue de sa provenance.
        calls = sum(p.read_text(encoding="utf-8").count("OpexAirF1Before(")
                    for p in AI.glob("*.nut"))
        self.assertEqual(calls, 3)  # declaration + renfort + V252

    def test_p6_best_reader_has_single_materialized_call_site(self):
        source = _read("task_projects.nut")
        executor = _body(source, "function OpexAI::_tryBuildProjects(year)")
        self.assertLess(executor.index("this._ensureSelection();"),
                        executor.index("OpexP6FirstlineWindowHold(this)"))
        self.assertLess(executor.index("OpexP6FirstlineWindowHold(this)"),
                        executor.index("OpexC75BypassEnsureYear(year);"))
        self.assertEqual(sum(p.read_text(encoding="utf-8").count("OpexP6FirstlineWindowHold(")
                             for p in AI.glob("*.nut")), 2)  # declaration + executor

    def test_audit_all_best_readers(self):
        nut_files = list(AI.glob("*.nut"))
        best_pattern = re.compile(r"\b([A-Za-z0-9_]*\.best)\b")

        for f in nut_files:
            if f.name == "projects_selection.nut":
                continue  # Producteur de sélection
            content = f.read_text(encoding="utf-8")
            for match in best_pattern.finditer(content):
                full_match = match.group(1)
                pos = match.start()
                fn_name = self._find_enclosing_function(content, pos)
                fn_key = f"{f.name}:{fn_name}"
                file_key = f.name

                # Check if file or function is in whitelist
                if file_key in self.WHITELIST_JUSTIFICATIONS:
                    continue
                if fn_key in self.WHITELIST_JUSTIFICATIONS:
                    continue

                # Otherwise, the enclosing function MUST contain a call to _ensureSelection or OpexEnsureSelection
                fn_body = _body(content, f"function {fn_name}(")
                has_guard = ("_ensureSelection" in fn_body) or ("OpexEnsureSelection" in fn_body)
                self.assertTrue(
                    has_guard,
                    f"Reader unprotected in {f.name} at line {content[:pos].count('\n') + 1} inside {fn_name}: {match.group(0)}",
                )


if __name__ == "__main__":
    unittest.main()
