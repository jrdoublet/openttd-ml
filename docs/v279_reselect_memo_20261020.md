# Fiche Tâche V279b — Re-sélection incrémentale exacte du portefeuille

Date : 20 octobre 2026\
Branche : `v279`\
Base : master (`ac78c8e`)\
Worktree : `/home/deploy/projects/wt-v279`\
Référence : Constat mesuré spans AIR 1 an à 256² graine 42

---

## 1. Contexte et constat mesuré

Dans les profils de spans mesurés (1 an à 256², graine 42), la fonction `OpexReselectProjects` (`ai/OpexAI/projects_selection.nut`) est appelée entre **190 et 300 fois par an**, pour un coût global de **11,6 à 16 M d'opcodes par an**, soit environ **60 k opcodes par appel**. C'est le premier poste de consommation d'opcodes AIR.

Les appelants principaux sont :
- `task.projects` (165 à 173 appels/an via `_ensureSelection` avant `_tryBuildProjects`),
- `fleet.inject` (18 à 71 appels/an),
- Régénération d'événements (`regen`) et C77.

### Décomposition du coût par appel (192 appels)

| Span | Rôle principal | Coût total annuel | Par appel |
|---|---|---|---|
| `pub.select.filter` | Revalidation des alternatives AIR (`OpexFilterAirAlternativesStillValid`) | 4,42 M | 23 k |
| `pub.select.score` | Dimensionnement de flotte et scoring (`OpexProjectSelectAffordable`) | 5,38 M | 28 k |
| `pub.select.stats` | Horodatage et statistiques (`OpexProjectsStampSelectionStats`, etc.) | 1,27 M | 6,6 k |
| `pub.select.flatten` | Aplatissement de `candidateGroups` | 0,18 M | ~0,9 k |
| `pub.select.merge` | Fusion alternatives rail/air préparées | 0,02 M | ~0,1 k |

---

## 2. Abandon de la mémoïsation du score (V279b)

La tentative initiale V279 mémoïsait les termes de score d'évaluation indépendants du budget (`_v279FinCap`, `_v279DecCap`, `_v279FundProfit`) dans une fonction dupliquée `OpexProjectSelectAffordableMemoized`.

Cette mémoïsation a été **entièrement retirée** pour les motifs suivants :
1. **Les termes ne sont pas constants au cours de la partie :**
   - `OpexProjectFundProfit` appelle `OpexC70Profit` (`projects_models.nut:160`), qui multiplie par `C70_MODE_FACTOR[mode]`. Ce facteur est recalculé dynamiquement en cours de partie (`projects_models.nut:54`, `task_report.nut:103`).
   - Le profit dépend également de `payload.economics.realizationFactor` (C121).
   - `OpexApplyRailActualCapital` (`economy.nut:588`, appelé depuis `builder_rail.nut`, `rail_templates.nut` et `goods_v233.nut`) réécrit sur place `candidate.capital`, `capitalIsActual`, `amortAnnual` et `profitAnnual`, que lit `OpexProjectFinanceCapital`.
2. **Gain marginal disproportionné au risque et au code :**
   - Le calcul de `fund_score` ne coûte qu'environ 67 opcodes par projet.
   - La duplication de ~500 lignes de sélection alourdissait la maintenance sans garantie d'équivalence absolue.
3. **Architecture retenue :**
   - `OpexProjectSelectAffordable` historique est conservé **à l'identique strict de master `ac78c8e`**, sans aucune duplication, paramètre supplémentaire ni crochet (`OpexHookV216*` retirés).
   - `OpexReselectProjects` ne contient aucun dédoublement (`OpexV279ReselectProjectsMemoized` et `OpexV279ReselectProjectsControl` supprimés).
   - L'optimisation se concentre exclusivement sur le filtre AIR (`pub.select.filter`).

---

## 3. Analyse exhaustive des dépendances du filtre et couverture de l'estampille

Le filtre AIR réévalue la validité physique des alternatives de `candidateGroups`. Pour chaque projet aérien, les vérifications suivantes sont effectuées :

### 3.1 Dépendances directes et leur couverture

| Composant testé | État lu | Mécanisme de couverture par l'estampille |
|---|---|---|
| `OpexCandidateIsAbandoned` | `this._abandonedPairs` | Compteur `OPEX_ABANDON_REVISION`, incrémenté aux 5 sites de mutation (`lines.nut:282`, `lines.nut:308`, `task_report.nut:177`, `main.nut:409`, `persist.nut:791-792`). Le simple décompte `len()` a été rejeté car `_pruneAbandonedPairs` peut supprimer un couple pendant qu'un autre s'ajoute, laissant la taille inchangée. |
| `OpexAirRecoveryBlocksPlan` | `OPEX_AIR_ROLLBACKS` | Compteur `OPEX_AIR_ROLLBACK_REVISION`, incrémenté aux 6 sites de mutation (`air_construction.nut:41` append et :44 pop, `air_recovery.nut:97` remove, :104 rotated, :125 reconcile purge, `persist.nut:770` reset et :776 load). |
| `OpexAirTownServed` | `town.tile` (immuable) et `this._lines` | Compteur `OPEX_LINES_REVISION`, incrémenté aux 7 sites de mutation de `_lines` (`main.nut`, `persist.nut`, `task_air.nut`, `task_rail.nut`, `task_road.nut`, `task_water.nut`, `task_report.nut`). |
| `OpexAirBatchHubHasCapacity` | Aéroports existants de la compagnie et comptage de lignes par hub | Compteur `OPEX_LINES_REVISION` (comptage de routes et ferraillage) et `OPEX_AIR_ROLLBACK_REVISION` (rollback). Un aéroport de la compagnie ne disparaît que par ferraillage (`_scrapDeadLines`) ou rollback. Son type ne change jamais sans reconstruction. |
| Conflit de paire d'aéroports | `this._lines` (originA/originB) | Compteur `OPEX_LINES_REVISION`. |
| `OpexAirC83SecondSlotOpen` | `AITown.GetPopulation` et `AITown.GetAllowedNoise` | **Non couvrable par estampille :** ces grandeurs d'API OpenTTD évoluent continuellement sans aucun événement IA. **Règle stricte :** tout plan portant `c83OwnSecondSlotA/B` ou `v134SecondSlotA/B` est **exclu de la mémoïsation** et réévalué à chaque appel. |
| `OpexAir0310SiteValidityOk` | Cache mensuel de validité des sites et constructibilité | `month = OpexAir0310SiteValidityMonth()` (expiration calendaire) et `OPEX_AIR_SITE_EPOCH` (invalidation lors de resets ou de modifications topologiques dans `air_coverage.nut`). |

### 3.2 Amorçage et ordre des sondages de validité

Dans `OpexFilterAirAlternativesV279Memo` :
- En Mode 2 (contrôle) : `validity` et `stationLimitedTowns` sont amorcés dès l'entrée de fonction (`OpexAir0310SiteValidityBegin(stationLimitedTowns)`), garantissant un remplissage de `AIR0310_SITE_VALIDITY_STATE` strictement identique à master.
- En Mode 1 (mémoïsé) : si au moins un plan nécessite une évaluation (miss ou second créneau), `validity` et `stationLimitedTowns` sont amorcés avant le premier test.
- Les sondages `OpexAir0310SiteValidityOk` ne sont appelés que si `OpexAirBatchPlanStillLive` est vrai, respectant exactement le court-circuitage historique de master.

### 3.3 Sérialisation et intégrité de la persistance

- `persist.nut` ne sérialise ni `this._projects` ni `candidateGroups` (remis à `null` lors du chargement dans `_reconcileAfterLoad`).
- Les champs temporaires `_v279Stamp` et `_v279Live` posés sur les projets du vivier ne peuvent donc jamais être écrits dans une sauvegarde.
- Aucun champ `_v279*` n'est stocké dans `_lines` ni dans l'état persistant.

---

## 4. Mode 2 (Contrôle) dans le filtre lui-même

Le contrôle de non-divergence est intégré directement au sein d'`OpexFilterAirAlternativesV279Memo` :
1. Pour chaque projet aérien :
   - Évaluation du verdict historique `histLive` avec le code identique à master dans le même ordre.
   - Si l'estampille est valide (et hors second créneau), comparaison de `memoLive` (`project._v279Live`) avec `histLive`.
   - En cas de divergence, émission d'un log formaté :
     `V279_CHECK filter town_a=... town_b=... memo=... hist=... stamp=...` via `OpexDecide`, doublé d'`AILog.Warning` si `!DECISION_LOG`.
   - Conservation du verdict historique dans la sélection (`if (histLive) live.append(project)`).
   - Mise à jour de l'estampille et du verdict mémorisé avec la valeur historique.

---

## 5. Mesure des taux de réussite (`V279_STATS`)

Les globales `V279_HITS` et `V279_MISSES` comptabilisent les accès au filtre pour les modes 1 et 2.
Chaque changement de mois calendaire émet une statistique sous `V279_STATS` :
`OpexDecide("V279_STATS", "month=" + V279_LAST_STATS_MONTH + " hits=" + V279_HITS + " misses=" + V279_MISSES + " total=" + total + " hit_pct=" + pct);`
Ceci permet de mesurer directement en jeu ou sous banc le taux de succès sans surcoût.

---

## 6. Intégrité absolue du défaut (Mode 0)

À `v279_reselect_memo = 0` :
- `V279_RESELECT_MEMO` vaut 0.
- `OpexReselectProjects` évalue `(V279_RESELECT_MEMO != 0)` à faux et appelle directement `OpexFilterAirAlternativesStillValid(alternatives, abandonedPairs, lines)`.
- Toutes les gardes `if (V279_RESELECT_MEMO != 0)` dans le moteur évaluent à faux.
- Le code exécuté est strictement identique à celui de master `ac78c8e` au caractère près.

---

## 7. Validation statique et conformité

1. **Contrats source V279 (`sweeps/test_v279_reselect_memo.py`) :**
   - 13/13 tests unitaires passés avec succès.
   - Vérifie la limitation du diff de `projects_selection.nut` au filtre et à son appel.
   - Vérifie l'absence de `_v279FinCap`, `_v279DecCap` et `_v279FundProfit`.
   - Vérifie l'incrémentation des compteurs d'abandons (5 sites), rollbacks (6 sites), lignes (7 sites) et époques de sites (3 sites).
   - Vérifie l'exclusion des plans à second créneau.
   - Vérifie le comportement du mode 2 et la journalisation des statistiques.
2. **Suite complète de non-régression :**
   - Commande : `python3 -m unittest discover -s sweeps -p 'test_*.py'`
   - Résultat : **2 103 tests passés avec succès** (0 échec, 3 sauts et 3 échecs attendus identiques à master).
3. **Vérification de syntaxe et délimiteurs :**
   - `python3 tmp/undecl.py ai/OpexAI` : 0 variable non déclarée.
   - `python3 tmp/delim.py ai/OpexAI` : 0 délimiteur déséquilibré.
4. **Vérification Git :**
   - `git diff --check` : aucun espace ou saut de ligne invalide.
