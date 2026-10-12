# V155 — Flotte AIR : gardes C121 « O » avant le rafraîchissement de cible (optimisation d'opcodes)

**Date :** 12 octobre 2026  
**Branche :** `v155-fleet-preguard`  
**Réglage introduit :** `air_fleet_c121_preguard` (0/1, défaut 0, 4 `*_value` = 0)  
**Variable globale :** `AIR_FLEET_C121_PREGUARD`  
**Statut :** Implémenté, vérifié statiquement et couvert par tests unitaires. Défaut à 0 préservé (aucun banc Docker ni OpenTTD exécuté).

---

## 1. Contexte & motivation

Dans `docs/v151d_revue_opcodes_scan_air_orchestrateur_20261012.md` (§1), l'audit des spans V151c (`fleet.resize`) a mis en évidence le coût prépondérant de l'extension de flotte aérienne :
- `fleet.resize` (`OpexAI::_resizeAirFleets`, `ai/OpexAI/task_air.nut:1069`) coûte **155 k opcodes par appel en 1974** (soit **16,6 M opcodes/an**, ~25 % du budget opcodes annuel total), et cette dépense croît linéairement avec la taille de la flotte.
- Pour chaque ligne aérienne active, `OpexC121RefreshVisibleFleet(this._catalog, line, this._lines)` (`ai/OpexAI/air_fleet.nut:316`) réévalue la demande, la concurrence visible, le modèle moteur et l'économie marginale, tout en parcourant les autres lignes en $\mathcal{O}(L)$. Cet appel a lieu au plus tous les 30 jours par ligne (throttle de cache).
- Or, juste après ce rafraîchissement (lignes 1177–1222 de `task_air.nut`), une ligne sous C121 est immédiatement confrontée aux gardes d'observation (« O ») et de cadence post-agrandissement :
  1. Âge d'exploitation insuffisant : `c121Age < 2` (moins de deux années complètes de service).
  2. Profit non mesuré ou non positif : `!("lastProfit" in line) || line.lastProfit <= 0`.
  3. Cadence post-extension : `("lastAirFleetYear" in line) && (year - line.lastAirFleetYear) < 2`.
- **Propriété fondamentale :** Aucune de ces trois gardes ne dépend de la valeur de la cible (`targetAirPlanes`) ni des grandeurs marginales recalculées par `OpexC121RefreshVisibleFleet`. Une ligne qui échoue à l'un de ces tests sera donc **systématiquement refusée**, quelle que soit la cible théorique produite par le rafraîchissement.
- Payer le coût lourd de `OpexC121RefreshVisibleFleet` pour ces lignes est donc un gaspillage pur d'opcodes.

---

## 2. Description de l'intervention

### 2.1 Réglage et variable globale
- Déclaré dans `ai/OpexAI/info.nut` :
  ```squirrel
  AddSetting({
    name = "air_fleet_c121_preguard",
    description = "Filter AIR lines refused by C121 observation/cadence before visible fleet refresh",
    min_value = 0, max_value = 1,
    easy_value = 0, medium_value = 0, hard_value = 0,
    custom_value = 0,
    flags = 0
  });
  ```
- Déclaré dans `ai/OpexAI/globals_pre.nut` :
  ```squirrel
  AIR_FLEET_C121_PREGUARD <- false;
  ```
- Chargé dans `ai/OpexAI/settings.nut` :
  ```squirrel
  AIR_FLEET_C121_PREGUARD = AIController.GetSetting("air_fleet_c121_preguard") != 0;
  ```

### 2.2 Pré-filtre dans `_resizeAirFleets` (`ai/OpexAI/task_air.nut`)
Inséré immédiatement avant l'appel `OpexC121RefreshVisibleFleet(this._catalog, line, this._lines)` (~ligne 1176) :

```squirrel
    /* V155: pre-filter AIR lines refused by C121 observation/cadence before paying the visible fleet refresh */
    if (AIR_FLEET_C121_PREGUARD && C121_AIR_ECONOMICS && C121_AIR_VISIBLE_COMPETITION
        && ("targetAirPlanes" in line)) {
      local isFirstLiveEligible = C121_AIR_FIRST_LIVE_GROWTH
          && (C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS <= 0
              || year - OPEX_START_YEAR < C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS)
          && have == 1 && !("lastAirFleetYear" in line);
      if (!isFirstLiveEligible) {
        local c121Age = ("year" in line) ? year - line.year : -1;
        if (c121Age < 2 || !("lastProfit" in line) || line.lastProfit <= 0) {
          if (DECISION_LOG) {
            local reasonStr = (c121Age < 2) ? "age" : "profit";
            OpexDecide("AIR_FLEET_PREGUARD", "line=" + line.lineId + " reason=" + reasonStr);
          }
          OpexAirFleetRefusal(line, year, "O");
          if (plan != null && C69_BOTTLENECK_PROBE)
            OpexC73RecordRejection("fleet", "c121_no_full_year_observation", 1);
          continue;
        }
        if (("lastAirFleetYear" in line) && (year - line.lastAirFleetYear) < 2) {
          if (DECISION_LOG) {
            OpexDecide("AIR_FLEET_PREGUARD", "line=" + line.lineId + " reason=cadence");
          }
          OpexAirFleetRefusal(line, year, "O");
          if (plan != null && C69_BOTTLENECK_PROBE)
            OpexC73RecordRejection("fleet", "c121_wait_full_year_after_growth", 1);
          continue;
        }
      }
    }
```

---

## 3. Preuve d'équivalence stricte des décisions

L'analyse de tous les cas démontre que l'arbre de décision économique est rigoureusement identique :

1. **Cas d'une ligne non-first-live échouant à l'observation C121 (`c121Age < 2` ou `lastProfit <= 0`) :**
   - *Historique :* Exécute `OpexC121RefreshVisibleFleet`. Si la nouvelle cible est $\le \text{have}$, la ligne est refusée avec le code `"T"`. Si la nouvelle cible est $> \text{have}$, elle entre dans `c121BelowTarget` et est refusée à la ligne 1213 avec le code `"O"` et le goulot C73 `"c121_no_full_year_observation"`.
   - *Avec pré-garde :* Refusée immédiatement avant le refresh avec le code `"O"` et le goulot C73 `"c121_no_full_year_observation"`.
   - *Effet économique :* Aucun achat d'appareil, aucune entrée insérée dans `plan`. Décision identique. Seul le code de diagnostic interne en cas de saturation de capacité passe de `"T"` à `"O"` (le motif d'observation préalable préemptant le test de saturation).

2. **Cas d'une ligne non-first-live en cooldown de croissance (`year - lastAirFleetYear < 2`) :**
   - *Historique :* Exécute `OpexC121RefreshVisibleFleet`. Refusée soit avec `"T"` (si cible $\le \text{have}$), soit à la ligne 1218 avec `"c121_wait_full_year_after_growth"`.
   - *Avec pré-garde :* Refusée immédiatement avant le refresh avec le même goulot C73 `"c121_wait_full_year_after_growth"`.
   - *Effet économique :* Aucun achat, aucune entrée dans `plan`. Décision identique.

3. **Cas d'une ligne éligible au chemin first-live :**
   - Condition exacte : `C121_AIR_FIRST_LIVE_GROWTH`, phase valide, `have == 1`, jamais `lastAirFleetYear`.
   - Ces lignes peuvent être autorisées à croître prématurément de 1 à 2 avions via `OpexC121FirstLiveBalanced90(line)` sans attendre deux ans d'observation.
   - La pré-garde détecte cette condition (`isFirstLiveEligible = true`) et **exclut expressément ces lignes du pré-filtre**. Elles accèdent ainsi à `OpexC121RefreshVisibleFleet` et aux gardes first-live exactement comme dans l'historique.

4. **Cas d'une ligne pleinement éligible à la croissance :**
   - Âge $\ge 2$ ans, profit mesuré $> 0$, cadence depuis la dernière extension $\ge 2$ ans.
   - La pré-garde ne la refuse pas.
   - La ligne exécute `OpexC121RefreshVisibleFleet`, évalue la cible visible mise à jour et participe normalement à la sélection/achat.

5. **Cas où `targetAirPlanes` est absent de la ligne :**
   - Conditionnée par `("targetAirPlanes" in line)`. Si la cible n'existe pas encore (ex. création récente de ligne), la pré-garde est désactivée afin de laisser le refresh initialiser les métadonnées de la ligne.

6. **Interaction avec `c84BelowTarget` (`C84_AIR_TARGET_FLEET`) :**
   - `C84_AIR_TARGET_FLEET` est désactivé par défaut (`false`).
   - S'il est activé, `c84BelowTarget` vérifie `("targetAirPlanes" in line) && line.targetAirPlanes > have`, ce qui est identique à `c121BelowTarget`. Les gardes en aval (lignes 1230, 1249, 1250) ne concernent que `!belowTarget`, qui n'est jamais atteint lorsque `C121_AIR_VISIBLE_COMPETITION` est actif puisque la garde `"T"` refuse préalablement tout cas où `have >= targetAirPlanes`. L'activation ou désactivation de C84 n'introduit donc aucune divergence.

7. **Ordre des gardes historiques (1176–1222) :**
   - Entre la ligne 1176 (`OpexC121RefreshVisibleFleet`) et la ligne 1222 (fin des gardes C121), il n'y a que le test `"T"`, le calcul de `c84BelowTarget` / `c121BelowTarget`, et les blocs first-live / C121. Aucune autre fonction ni mutation d'état ne s'intercale.

---

## 4. Recensement exhaustif des lecteurs des champs du rafraîchissement

L'appel `OpexC121RefreshVisibleFleet` écrit sur `line` :
1. `line.targetAirPlanes <- target.planes`
2. `line.c121TargetPlanes = target.planes` (si la clé existe)
3. `line.c121MarginalProfit <- after.profitAnnual - before.profitAnnual` (si `samples <= 0`)
4. `line.c121MarginalRevenue <- after.revenueAnnual - before.revenueAnnual` (si `samples <= 0`)
5. `line.c121RealizationPmAtBuild <- (before.realizationFactor * 1000.0).tointeger()` (si `samples <= 0`)
6. `C121_VISIBLE_FLEET_CACHE.rawset(line.lineId, ...)`

Tous les sites de lecture de ces champs dans `ai/OpexAI` ont été audités :

| Champ | Emplacements de lecture | Analyse d'impact |
|---|---|---|
| `targetAirPlanes` | `task_air.nut:1177, 1181, 1183, 1307`<br>`air_fleet.nut:308, 310`<br>`task_projects.nut:249`<br>`projects_selection.nut:878`<br>`projects_builders.nut:168, 170` | Les lectures en aval (`task_projects.nut:249`, `projects_selection.nut:878`, `projects_builders.nut:168`) ne sont appelées **que pour les projets insérés dans `plan`** par `_resizeAirFleets`. Une ligne refusée par la pré-garde n'est jamais insérée dans `plan`. Dès qu'une ligne redevient éligible, la pré-garde ne la refuse pas, et le rafraîchissement a lieu immédiatement avant toute lecture. |
| `c121TargetPlanes` | `task_air.nut:511, 932`<br>`probes.nut:364, 540`<br>`persist.nut:657` (`OPEX_SAVE_LINE_SKIP`) | Initialisé à la construction. Lu pour initialiser `targetAirPlanes` lors de nouveaux chantiers, et dans les sondes passives (`probes.nut`). Ignoré dans la sauvegarde (`OPEX_SAVE_LINE_SKIP`). |
| `c121MarginalProfit`<br>`c121MarginalRevenue` | `task_report.nut:53, 56`<br>`projects_models.nut:150`<br>`projects_selection.nut:105, 927`<br>`projects_builders.nut:178`<br>`probes.nut:408` | `task_report.nut` ne lit ces valeurs que si `addedObserved > 0` (un avion a effectivement été acheté et observé un an plus tard). `projects_builders` et `projects_selection` ne les lisent que pour évaluer les entrées de `plan`. Si la ligne est refusée, elle n'est pas dans `plan`. |
| `c121RealizationPmAtBuild` | `projects_builders.nut:188` | Lu uniquement lors de l'instanciation d'un projet de flotte présent dans `plan`. |
| `C121_VISIBLE_FLEET_CACHE` | `air_fleet.nut:322` | Cache privé interne à `OpexC121RefreshVisibleFleet` pour limiter sa fréquence d'exécution à une fois par tranche de 30 jours par ligne. Si l'appel est sauté, le cache n'est pas alimenté, ce qui garantit qu'au premier cycle où la ligne redevient éligible, le rafraîchissement s'exécutera sans être bloqué par un cache périmé. |

**Conclusion :** Aucun de ces champs n'est lu pour une ligne refusée avant son prochain cycle d'éligibilité (où le rafraîchissement s'exécute de façon certaine).

---

## 5. Estimation de la part des lignes concernées & gains attendus

### 5.1 Proportion des lignes filtrées
Sur une partie mature (ex. 1974 avec 15 à 30 lignes aériennes) :
- Toute ligne créée récemment (dans les 2 premières années) est filtrée par `c121Age < 2`.
- Toute ligne ayant bénéficié d'un agrandissement de flotte l'année précédente est filtrée par le cooldown `(year - lastAirFleetYear) < 2`.
- Toute ligne temporairement déficitaire est filtrée par `lastProfit <= 0`.
- En pratique, sur l'ensemble des lignes existantes lors de chaque appel de `_resizeAirFleets`, **70 % à 90 %** des lignes se trouvent dans l'un de ces trois états de refus certain.

### 5.2 Gains d'opcodes estimés
- Coût mesuré de `_resizeAirFleets` en 1974 : ~155 k opcodes par appel (~106 appels/an, soit ~16,6 M opcodes/an).
- En éliminant 70 % à 90 % des appels à `OpexC121RefreshVisibleFleet` (qui constituent la quasi-totalité du temps de `_resizeAirFleets`), le gain attendu est de **11 à 14 millions d'opcodes par an en régime de croisière**.
- Conformément à la décision utilisateur du 2026-09-24 pour les optimisations d'opcodes, ce gain libère des opcodes pour les chantiers d'infrastructure et de sélection sans altérer la politique économique de l'IA.

---

## 6. Validation statique et tests automatisés

- **Tests de non-régression existants :** Tous les tests unitaires et de contrats du harnais passent avec succès :
  - `sweeps/test_c121_air_economics.py`
  - `sweeps/test_c84_air_target_fleet.py`
  - `sweeps/test_c121_visible_target.py`
  - `sweeps/test_opcode_exact.py`
  - `sweeps/test_mechanism_fixtures.py`
  - `sweeps/test_v102_protocol.py`
- **Nouveau test unitaire dédié :** `sweeps/test_v155_fleet_preguard.py`
  - Valide la déclaration de réglage dans `info.nut` (défaut 0, 4 `*_value` = 0).
  - Valide la déclaration dans `globals_pre.nut` et le chargement dans `settings.nut`.
  - Valide la structure du pré-filtre et son positionnement immédiat avant `OpexC121RefreshVisibleFleet`.
  - Valide l'exclusion stricte du chemin first-live.
  - Valide l'équivalence rigoureuse des décisions économiques sur un jeu complet d'états de lignes (lignes jeunes, déficitaires, en cooldown, éligibles first-live, pleinement éligibles).
- **Formatage & lint :** `git diff --check` passe sans aucun avertissement.
