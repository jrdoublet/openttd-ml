# Rapport de réalisation — Tâche F-EVENT-BACKLOG-01

**Date :** 11 octobre 2026  
**Chantier :** F-EVENT-BACKLOG-01 (`docs/taches.md`)  
**Branche / Workspace :** `/home/deploy/projects/wt-fevent-subsidy`

---

## 1. Contexte et objectif

Lors des expirations d'offres ou de subventions (`AIEventSubsidyOfferExpired`, `AIEventSubsidyExpired`) et lorsqu'un concurrent remporte une subvention (`AIEventSubsidyAwarded`), la méthode `OpexAI::_c77RemoveSubsidy(subId)` dans [ai/OpexAI/event_handlers.nut](file:///home/deploy/projects/wt-fevent-subsidy/ai/OpexAI/event_handlers.nut#L353) purgeait la subvention via `_purgeSubsidyFromProjects(subId)` puis relançait systématiquement une réélection complète du portefeuille via `OpexReselectProjects`.

Les mesures de profilage (`probe_event_backlog=1`, `probe_span_trace=1`) ont révélé que ces réélections peuvent consommer jusqu'à 2,56 M opcodes et bloquer 255 ticks (dont ~87 % dans `select.full` / `pub.select.score`), y compris lorsque `_purgeSubsidyFromProjects` n'a retiré aucun candidat du portefeuille (aucun projet subvention n'était présent dans `best`, `road.best` ni `candidateGroups`).

L'objectif de cette intervention est de conditionner cette réélection coûteuse derrière le nouveau réglage booléen `subsidy_reselect_if_purged` :
- Sous `subsidy_reselect_if_purged = 0` (défaut strict) : comportement historique inconditionnel inchangé.
- Sous `subsidy_reselect_if_purged = 1` : réélection exécutée uniquement si `_purgeSubsidyFromProjects` a retiré au moins un candidat (`purged > 0`).

---

## 2. Emplacements modifiés (fichier:ligne) et diff résumé

### 2.1 [ai/OpexAI/info.nut](file:///home/deploy/projects/wt-fevent-subsidy/ai/OpexAI/info.nut#L1985-L1995)
Déclaration du réglage `subsidy_reselect_if_purged` avec `flags = AICONFIG_BOOLEAN`, bornes 0..1, pas 1, et valeur 0 aux 4 difficultés (`easy_value = 0`, `medium_value = 0`, `hard_value = 0`, `custom_value = 0`).

```squirrel
    AddSetting({
      name = "subsidy_reselect_if_purged",
      description = "F-EVENT-BACKLOG-01: only reselect projects on subsidy expiration/award if _purgeSubsidyFromProjects actually removed candidates; 1 = conditional reselect, 0 = unconditional reselect (historical default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });
```

### 2.2 [ai/OpexAI/globals_pre.nut](file:///home/deploy/projects/wt-fevent-subsidy/ai/OpexAI/globals_pre.nut#L1060-L1063)
Initialisation de la variable globale `SUBSIDY_RESELECT_IF_PURGED` à `false` (défaut inerte).

```squirrel
/* F-EVENT-BACKLOG-01 : ne relancer la reselection dans _c77RemoveSubsidy que si
 * la purge a reellement retire des candidats de subvention. 0 = inconditionnel (defaut historique). */
SUBSIDY_RESELECT_IF_PURGED <- false;
```

### 2.3 [ai/OpexAI/settings.nut](file:///home/deploy/projects/wt-fevent-subsidy/ai/OpexAI/settings.nut#L661)
Chargement du réglage dans `OpexLoadSettings()` :

```squirrel
  SUBSIDY_RESELECT_IF_PURGED = AIController.GetSetting("subsidy_reselect_if_purged") != 0;
```

### 2.4 [ai/OpexAI/task_projects.nut](file:///home/deploy/projects/wt-fevent-subsidy/ai/OpexAI/task_projects.nut#L161-L200)
`_purgeSubsidyFromProjects(subId)` comptabilise et retourne le nombre exact d'éléments retirés dans toutes les structures purgées :
- Entrées invalides (`subId == null || subId < 0` ou `this._projects == null`) : renvoie `0`.
- Éléments retirés de `this._projects.best` : incrémente `removed++`.
- Éléments retirés de `this._projects.road.best` : incrémente `removed++`.
- Clé `"subsidy|" + subId` supprimée de `this._projects.candidateGroups` : incrémente `removed += count` (supporte à la fois les tableaux de candidats et les objets uniques présents dans les bouchons de test).
- Renvoie `removed`.

### 2.5 [ai/OpexAI/event_handlers.nut](file:///home/deploy/projects/wt-fevent-subsidy/ai/OpexAI/event_handlers.nut#L353-L367)
Dans `OpexAI::_c77RemoveSubsidy(subId)` :
- Le nettoyage de `this._activeSubsidies[subId]` reste inconditionnel et s'exécute en premier.
- Appel de `local purged = this._purgeSubsidyFromProjects(subId);`.
- Garde conditionnelle : `if (SUBSIDY_RESELECT_IF_PURGED && purged <= 0) return;`.
- Si le réglage est à 0 : l'expression est fausse, la réélection complète s'exécute (comportement historique strict).
- Si le réglage est à 1 et `purged <= 0` : retour immédiat sans exécuter `OpexReselectProjects`, évitant jusqu'à 2,56 M opcodes.

### 2.6 [sweeps/test_subsidy_reselect_if_purged.py](file:///home/deploy/projects/wt-fevent-subsidy/sweeps/test_subsidy_reselect_if_purged.py)
Nouveau fichier de tests unitaires et de contrats Python vérifiant :
1. Déclaration du réglage et défaut 0 aux 4 difficultés (via `parse_ai_settings` et `parse_ai_setting_specs`).
2. Déclaration globale unique `SUBSIDY_RESELECT_IF_PURGED <- false`.
3. Lecture unique via `AIController.GetSetting` dans `settings.nut`.
4. Absence de persistance dans `persist.nut`.
5. Prise en compte et retour du compteur dans `_purgeSubsidyFromProjects`.
6. Positionnement et sémantique de la garde dans `_c77RemoveSubsidy`.
7. Conformité Squirrel (aucun mot réservé `clone`, `base`, `parent`, `resume`, équilibre des accolades).
8. Simulation exhaustive de la logique de purge (cas limites et structures complexes).

---

## 3. Analyse des risques et vérification des états collatéraux

Une vérification approfondie a été menée pour déterminer si d'autres états internes d'OpexAI sont mis à jour uniquement lors de cette réélection et risqueraient de devenir obsolètes lorsque la réélection est sautée :

1. **`this._ranked`** :
   - Dans `_c77RemoveSubsidy`, `this._ranked` reçoit `this._projects.rail`.
   - Les subventions sont exclusivement modales routières (`candidates.nut::OpexGenerateSubsidyCandidates` ne produit que des candidats route).
   - `OpexReselectProjects` ne modifie jamais `projects.rail`.
   - `this._ranked` est en outre rafraîchi régulièrement par l'ordonnanceur (`scheduler_tasks.nut:149, 336, 670, 942`), la boucle de fond et `orchestrator.nut`.
   - Si aucun candidat n'a été purgé, `projects.rail` est strictement identique avant et après l'événement. Sauter la réélection ne rend donc pas `_ranked` obsolète.

2. **Seuil rail stock C80 (`this._updateRailStockSelectionThreshold()`)** :
   - `_updateRailStockSelectionThreshold()` met à jour `this._railStockLastFundedScore` d'après le score du dernier projet financé dans `this._projects.best`.
   - Si la purge n'a retiré aucun projet (`purged == 0`), le vivier de projets financés n'a pas varié.
   - De plus, `this._tryStartRailStockWorker()` (dans `task_rail.nut:1846`) appelle systématiquement `_updateRailStockSelectionThreshold()` avant de démarrer un travailleur de stock.
   - Ce seuil n'est donc en aucun cas tributaire de `_c77RemoveSubsidy`.

3. **`this._activeSubsidies`** :
   - L'effacement de l'offre expirée dans `this._activeSubsidies[subId]` est exécuté en ligne 356, **avant** l'appel de purge et avant la garde de réélection.
   - La table des offres suivies est donc garantie propre même lorsque la réélection est sautée.

4. **Trésorerie et réélection ordinaire** :
   - Le seul effet potentiel de relancer `OpexReselectProjects` quand aucun projet subvention n'est purgé était de réévaluer le portefeuille par rapport au capital disponible courant (`OpexAvailableCapital()`).
   - Cependant, la gestion du portefeuille dispose déjà de son cycle de réélection périodique régulier (mensuel et planifié).
   - Déclencher 2,56 M opcodes sur un événement moteur asynchrone sans modification du vivier n'apportait aucun rafraîchissement fonctionnel requis.

**Conclusion :** Aucun état interne ne devient obsolète lorsque la réélection est ignorée sous `purged == 0`.

---

## 4. Résultats des tests

### 4.1 Tests ciblés F-EVENT-BACKLOG-01
```
python3 -m unittest sweeps/test_subsidy_reselect_if_purged.py
........
----------------------------------------------------------------------
Ran 8 tests in 0.016s

OK
```

### 4.2 Tests liés aux sondes d'événements et subventions
```
python3 -m unittest sweeps/test_event_backlog_probe.py sweeps/test_c45_subsidy_persistence.py sweeps/test_campaign_freeze.py
..............................
----------------------------------------------------------------------
Ran 30 tests in 8.897s

OK
```

### 4.3 Suite complète de découverte (`sweeps/test_*.py`)
Exécution de `python3 -m unittest discover -s sweeps -p "test_*.py"` :
- **1878 tests exécutés** (contre 1870 avant l'intervention, soit +8 tests apportés par `test_subsidy_reselect_if_purged.py`).
- **1 seul échec attendu** : `FAIL: test_preexisting_builder_entirely_preserved (test_parallel_fleet_amort_shadow.SourceTests.test_preexisting_builder_entirely_preserved)`, préexistant sur `master` comme spécifié par la consigne.
- Aucune régression introduite.
