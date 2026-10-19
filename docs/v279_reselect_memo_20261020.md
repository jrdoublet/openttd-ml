# Fiche Tâche V279 — Re-sélection incrémentale exacte du portefeuille

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

Dans `pub.select.score`, sur environ 96 projets par sélection, les sous-spans instrumentés (`fund_score`, `fit`, `insert`, `refresh_slots`) ne totalisent qu'environ 3,0 M sur les 5,4 M mesurés. Le reste est consommé dans les boucles de parcours répétées (calcul du plancher `PORTFOLIO_FLOOR_PCT`, appels multiples à `OpexProjectFinanceCapital`, etc.).

### Retour d'expérience V277 (piste écartée)
Le remplacement d'`OpexAirBatchPlanStillLive` par la version indexée V156 (`OpexIncrRevalidateIndexContext`) donnait 0 écart fonctionnel mais coûtait **plus cher** (26,8 k contre 23,0 k par filtre). Le surcoût provient de la maintenance et du parcours des structures d'indexation comparé à une boucle courte sur les lignes existantes. Cette piste ne doit donc pas être reprise.

---

## 2. Étape 1 : Analyse exhaustive des dépendances par étape

Chaque appel à `OpexReselectProjects(projects, capitalBudget, abandonedPairs, lines, railReadyStock)` traverse les étapes suivantes :

### 2.1 Aplatissement du vivier (`pub.select.flatten`)
- **Dépendances :** `projects.candidateGroups` uniquement.
- **Invariance :** Si aucun nouveau projet n'a été inséré dans `candidateGroups`, la liste des projets est strictement identique en contenu et en ordre.

### 2.2 Fusion rail/air (`pub.select.merge`)
- **Dépendances :** Réglages `MODE_AIR`, `MODE_RAIL`, `C121_CATALOG_FIRST_YEAR_ACTIVE`, et `railReadyStock`.
- **Invariance :** Invariant tant que `railReadyStock` ne change pas.

### 2.3 Filtrage des alternatives AIR (`pub.select.filter`)
Pour chaque projet `mode == "air"` :
1. **Test d'abandon :** `OpexCandidateIsAbandoned(project, abandonedPairs)`. Dépend de l'ensemble `abandonedPairs` (couples de villes abandonnées).
2. **Survie du plan de vol :** `OpexAirBatchPlanStillLive(plan, lines)`. Dépend de `lines` (présence de lignes actives réutilisant déjà les mêmes aéroports).
3. **Validité des sites au sol :** `OpexAir0310SiteValidityOk(validity, key, site, airport, plane, reuse, stationLimitedTowns)`. Dépend :
   - Du mois courant (`OpexAir0310SiteValidityMonth()`), car le cache mensuel de validité des sites expire chaque mois ;
   - Des aéroports construits sur la carte et de la topologie locale (invalidation via `OpexAirResetSiteCache`, `OpexAirInvalidateCachedSite`, `OpexAir0310InvalidateSiteValidity`) ;
   - Du nombre de stations par ville (`stationLimitedTowns`).

**Synthèse d'invariance du filtre AIR :**
Pour un projet donné, le verdict de validité du filtre est **strictement invariant** tant que :
1. Le mois calendaire n'a pas changé ;
2. La liste globale des lignes (`this._lines`) n'a subi aucune mutation (aucun ajout de ligne aérienne/ferroviaire/routière/fluviale, ni suppression pour scrap) ;
3. Le cache de sites aériens n'a subi aucune invalidation locale ou globale ;
4. La liste `abandonedPairs` n'a pas changé de taille ;
5. La présence de la référence `lines` est stable.

### 2.4 Scoring et sélection budgétaire (`pub.select.score`)
Dans `OpexProjectSelectAffordable` :
1. **Ajustement de flotte :** `OpexProjectFitFleetToBudget(project, capitalBudget)`. Dépend explicitement de `capitalBudget`. Pour les projets `fleet`, la taille de flotte et le capex s'adaptent au budget disponible.
2. **Calcul du plancher de profit :** Dépend de `PORTFOLIO_FLOOR_PCT` et du meilleur profit annuel parmi les projets abordables sous `capitalBudget`.
3. **Créneaux early et défensifs :** `OpexEarlySlotSelectionState()` et `OpexDefensiveSlotSelectionState(earlySlotState)`. Dépendent de la présence de lignes concurrentes et des créneaux temporels.
4. **Calcul de `kDec` :** `OpexC69ComputeKDec()`. Dépend de la trésorerie disponible et de la réserve de capital.
5. **Calcul des termes du projet :**
   - `financeCapital` : Pour les projets non-fleet (`mode != "fleet"`), `OpexProjectFinanceCapital(project)` ne dépend que des champs constants du projet (`costEst`, `capitalMin`, `capexMin`, `headroomRatio`). Il est **totalement invariant** d'un appel à l'autre.
   - `decisionFinanceCapital` : Pour les projets non-fleet, dépend de `financeCapital` et éventuellement de `project.decisionFinanceCapital` (constant pour le projet). **Totalement invariant**.
   - `fundProfit` : `OpexProjectFundProfit(project)`. Pour les projets non-fleet, dépend de `project.profitAnnual`, `project.annualRunCost`, `project.decisionFinanceCapital`. **Totalement invariant**.
   - `fundScore` : `OpexProjectScore(fundProfit, max(kDec, decisionFinanceCapital))`. Dépend de `fundProfit` (invariant), `decisionFinanceCapital` (invariant), et `kDec` (variable selon la trésorerie).
6. **Insertion ordonnée :** `OpexProjectInsertDefensive(affordable, project, scoreKey, limit, true)`. Tri stable par score décroissant.

### 2.5 Statistiques et horodatage (`pub.select.stats`)
- `projects.stats.selectedCapital` : somme des `financeCapital` des projets retenus.
- `projects.stats.selectedRevenue` : somme des `revenueAnnual` des projets retenus.
- `projects.stats.nextProjectCapital` : `financeCapital` du premier projet retenu (ou 0).
- `OpexProjectsStampSelectionStats` : met à jour `bestScore`, `medianScore`, `worstScore`, etc. Ces champs sont lus par `_c39StampFinanceable`, la télémétrie de cadence et les panneaux de diagnostic.

---

## 3. Étape 2 : Choix retenus et choix écartés

### 3.1 Choix retenus

#### A. Mémoïsation du filtre AIR sous estampille composite
- Fonction dédiée : `OpexFilterAirAlternativesV279Memo(alternatives, abandonedPairs, lines)`.
- Estampille globale `V279_FILTER_STAMP_ID`, incrémentée dès qu'un élément du contexte change :
  - `month != V279_LAST_MONTH` (détection mensuelle via `OpexAir0310SiteValidityMonth()`),
  - `OPEX_LINES_REVISION != V279_LAST_LINES_REV` (compteur de révision des lignes),
  - `OPEX_AIR_SITE_EPOCH != V279_LAST_SITE_EPOCH` (compteur d'époque des caches de sites),
  - `abandonedPairs.len() != V279_LAST_ABND_COUNT`,
  - `(lines != null) != V279_LAST_HAS_LINES`.
- Chaque projet testé stocke `project._v279Stamp = V279_FILTER_STAMP_ID` et `project._v279Live = isLive`.
- Tant que l'estampille est valide, les appels suivants réutilisent immédiatement `project._v279Live` en O(1) sans aucune réévaluation de validité ni parcours de lignes/sites.

#### B. Compteur de révision globale des lignes (`OPEX_LINES_REVISION`)
Aucun compteur n'existait dans le moteur. Un compteur global `OPEX_LINES_REVISION` est introduit dans `globals_pre.nut` et incrémenté sous la garde `if (V279_RESELECT_MEMO != 0)` à **l'ensemble exhaustif des 7 sites de mutation** de `this._lines` :
1. `ai/OpexAI/main.nut:406` : Initialisation du constructeur (`this._lines = [];`).
2. `ai/OpexAI/persist.nut:959` : Restauration après sauvegarde (`this._lines = liveLines;`).
3. `ai/OpexAI/task_air.nut:345` : Construction effective d'une ligne aérienne (`this._lines.append({...})`).
4. `ai/OpexAI/task_rail.nut:1270` : Construction effective d'une ligne ferroviaire (`this._lines.append({...})`).
5. `ai/OpexAI/task_road.nut:270` : Construction effective d'une ligne routière (`this._lines.append({...})`).
6. `ai/OpexAI/task_water.nut:79` : Construction effective d'une ligne maritime (`this._lines.append({...})`).
7. `ai/OpexAI/task_report.nut:727` : Démantèlement / suppression de ligne non rentable (`this._lines.remove(...)`).

#### C. Compteur d'époque de cache de sites AIR (`OPEX_AIR_SITE_EPOCH`)
Incrémenté sous garde `if (V279_RESELECT_MEMO != 0)` aux 3 points d'invalidation de cache de sites dans `ai/OpexAI/air_coverage.nut` :
1. `OpexAirResetSiteCache()` : réinitialisation complète du cache de sites.
2. `OpexAir0310InvalidateSiteValidity()` : invalidation explicite de la validité d'un site.
3. `OpexAirInvalidateCachedSite(site)` : invalidation d'une tuile d'ancrage spécifique.

#### D. Mémoïsation des termes intrinsèques de scoring
Dans `OpexProjectSelectAffordableMemoized` :
- Pour chaque projet non-fleet (`mode != "fleet"`), `_v279FinCap`, `_v279DecCap` et `_v279FundProfit` sont calculés une seule fois et mémorisés sur l'instance de projet (`project._v279FinCap <- ...`, etc.).
- Les recalculs répétés d'`OpexProjectFinanceCapital` dans les boucles de plancher de profit (`PORTFOLIO_FLOOR_PCT`), de filtrage budgétaire et de sommation statistique réutilisent cette valeur mémorisée.
- Les termes dépendant de `capitalBudget` (`OpexProjectFitFleetToBudget` pour la flotte) et de la caisse (`kDec`) continuent d'être évalués dynamiquement à chaque appel.

### 3.2 Choix écartés

1. **Indexation V156 des plans de vol :** Écartée car son coût de maintenance d'index surpasse le coût de la boucle de contrôle des lignes (mesuré sur V277 : 26,8 k vs 23,0 k opcodes).
2. **Différer davantage d'appels d'`OpexReselectProjects` :**
   - V158 a déjà mis en place la paresse lors des publications incrémentales de scan (`air_publish_lazy_select` posant `projects.selectionStale <- true`).
   - L'analyse des appels restants montre que les 165 à 173 appels provenant de `_ensureSelection()` sont appelés immédiatement avant `_tryBuildProjects`, qui consomme immédiatement `projects.best[0]`.
   - Les appels de `fleet.inject` sont également consommés immédiatement lors de l'injection d'avions.
   - Il n'existe donc aucun appel sans lecteur dont le résultat pourrait être différé sans altérer l'ordre temporel des décisions de construction.

---

## 4. Preuves d'exactitude et Mode Contrôle (2)

### 4.1 Strict respect du mode 0 (défaut)
À `v279_reselect_memo = 0` :
- `V279_RESELECT_MEMO` vaut 0.
- L'aiguillage en tête d'`OpexReselectProjects` n'est pas franchi (`if (V279_RESELECT_MEMO == 1) ... if (V279_RESELECT_MEMO == 2) ...`).
- Aucune affectation, mutation ou allocation nouvelle n'est exécutée hors condition.
- Le code exécuté est strictement identique à celui de master au caractère près.

### 4.2 Mode 2 : double calcul et contrôle de non-divergence
À `v279_reselect_memo = 2`, la fonction `OpexV279ReselectProjectsControl` orchestre la validation croisée continue :
1. **Sauvegarde de l'état mutable :**
   - Dictionnaire `savedScores` pour les `fundScore` attachés aux projets dans `candidateGroups`.
   - Dictionnaire `savedCatalogScores` pour `entry.lastScore` dans `C121_CATALOG_CACHE`.
   - Valeur d'horodatage `SELECT_BISECT_STAMP`.
   - Échantillons d'accumulation `C121_AIR_PRESSURE_ACCUM.samples`.
2. **Exécution du chemin mémoïsé :**
   - Appel à `OpexV279ReselectProjectsMemoized`.
   - Capture en mémoire de `projects.best`, `projects.capitalRemaining`, `projects.stats.selectedCapital`, `projects.stats.selectedRevenue`, `projects.stats.nextProjectCapital`, ainsi que des `fundScore` de chaque projet retenu.
3. **Restauration rigoureuse de l'état :**
   - Restauration des scores originaux dans `projects.candidateGroups` (suppression si absent initialement).
   - Restauration de `lastScore` dans `C121_CATALOG_CACHE`.
   - Restauration de `SELECT_BISECT_STAMP` et de `C121_AIR_PRESSURE_ACCUM.samples`.
4. **Exécution du chemin historique :**
   - Appel à `OpexReselectProjects(..., forceHistoric = true)`.
5. **Comparaison exhaustive :**
   - Taille de la liste `best` (`best_len`),
   - Identité et ordre strict de chaque projet dans `best` (`best_order_at_i`),
   - `fundScore` de chaque projet retenu (`fund_score_at_i`),
   - Capital restant `capitalRemaining`,
   - Capital sélectionné `stats.selectedCapital`,
   - Chiffre d'affaires sélectionné `stats.selectedRevenue`,
   - Capital du prochain projet `stats.nextProjectCapital`.
6. **Journalisation et garantie de comportement :**
   - Si une divergence quelconque est constatée, elle est journalisée sous `V279_CHECK` via `OpexDecide` et doublée d'un `AILog.Warning`.
   - La fonction retourne systématiquement le résultat du **chemin historique**, garantissant ainsi une immunité totale contre tout risque de régression en jeu.

---

## 5. Validation statique et conformité

1. **Contrats source V279 (`sweeps/test_v279_reselect_memo.py`) :**
   - Vérifie la déclaration du réglage dans `info.nut` (0..2, défaut 0, 4 profils à 0).
   - Vérifie le chargement dans `settings.nut` et la déclaration des globales dans `globals_pre.nut`.
   - Vérifie l'intégrité absolue du chemin historique (mode 0).
   - Vérifie le protocole complet de comparaison et restauration du mode 2.
   - Vérifie la présence de l'incrémentation de révision sur les 7 sites de mutation de `_lines`.
   - Vérifie la présence de l'incrémentation d'époque sur les 3 sites de cache de sites.
   - Vérifie les logiques de mémoïsation de filtrage et de scoring.
2. **Suite complète des tests du dépôt :**
   - Commande : `python3 -m unittest discover -s sweeps -p 'test_*.py'`
   - Résultat : **2 099 tests passés avec succès** (0 nouvel échec, 3 sauts et 3 échecs attendus identiques à master).
3. **Vérification de syntaxe et délimiteurs :**
   - `python3 tmp/undecl.py ai/OpexAI` : 0 variable non déclarée.
   - `python3 tmp/delim.py ai/OpexAI` : 0 délimiteur déséquilibré.
4. **Vérification Git :**
   - `git diff --check` : aucun espace ou saut de ligne invalide.
