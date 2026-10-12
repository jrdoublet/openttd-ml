# V154 — insertion de la sélection par dichotomie (optimisation d'opcodes strictement équivalente)

Date : 12 octobre 2026\
Branche : `v154-select-bisect`\
Worktree : `/home/deploy/projects/wt-v154-select-bisect`\

---

## 1. Contexte mesuré et objectif

Dans la revue de code et de profilage V151d (§2, `docs/v151d_revue_opcodes_scan_air_orchestrateur_20261012.md`),
le poste d'insertion dans la sélection :
```
pub.select.score.insert : 6,6 à 10 M opcodes/an (1973), ~2,2 k opcodes/insertion
```
provenait du comportement de la fonction `OpexProjectInsertDefensive` (`ai/OpexAI/projects_selection.nut` ~1537) :
1. Parcours linéaire intégral depuis la fin (`pos = best.len()` vers 0) pour chaque insertion ;
2. Recalcul répété pour chaque prédécesseur `prior` de `OpexProjectDefensiveAirPriority(prior)`, `OpexProjectSelectionScore(prior, field)` et `OpexProjectIsForcedChain(prior)` ;
3. Recalcul à chaque itération de boucle du prédicat `c118Active`, pourtant strictement invariant pendant l'insertion.

**Objectif V154 :**
Introduire un chemin rapide par dichotomie ($O(\log K)$ comparaisons au lieu de $O(K)$) avec mise en cache des composantes de tri sur les tables des projets, strictement équivalent au comportement historique, sécurisé par le réglage `select_bisect_insert` (désactivé par défaut, valeur 0 aux quatre difficultés).

---

## 2. Preuve d'équivalence stricte

### 2.1 Comparateur et relation de priorité
Hors C118 territorial et C122 shadow, le comparateur historique de deux projets (`prior` déjà présent dans `best`, `project` candidat à l'insertion) applique un ordre lexicographique total :
1. **Tier défensif** (`priorTier > projectTier`) ;
2. **Score de sélection** (`priorScore > projectScore`) ;
3. **Revenu annuel** (`prior.revenueAnnual >= project.revenueAnnual`).

Soit le prédicat booléen `KeepsPrior(prior, project)` défini par :
```squirrel
priorTier > projectTier
|| (priorTier == projectTier && priorScore > projectScore)
|| (priorTier == projectTier && priorScore == projectScore && prior.revenueAnnual >= project.revenueAnnual)
```

### 2.2 Invariant de préfixe et position d'insertion
Soit une liste `best` triée selon cette même relation d'ordre.
Puisque la relation « a priorité ou égalité » est transitive et totale, pour tout projet entrant `project`, l'ensemble des éléments de `best` vérifiant `KeepsPrior(best[i], project) == true` forme un **préfixe contigu** $[0, k-1]$ de `best`.
Pour tout indice $i \ge k$, on a `KeepsPrior(best[i], project) == false`.

- **Chemin historique (parcours de droite à gauche) :**\
  La boucle `while (pos > 0)` teste `prior = best[pos - 1]`. Dès que `KeepsPrior(prior, project)` est vrai, elle exécute `break`.
  En partant de `pos = len`, les éléments pour $pos - 1 \ge k$ ont `KeepsPrior == false` (la boucle décrémente `pos--`). Le premier élément rencontré satisfaisant `KeepsPrior == true` est exactement $pos - 1 = k - 1$, d'où `pos = k`. L'insertion a lieu en `k`. Si aucun élément ne vérifie `KeepsPrior`, `pos` descend à 0 et l'insertion a lieu en 0.

- **Chemin V154 (dichotomie / recherche binaire) :**\
  L'intervalle $[lo, hi[$ commence à $[0, len[$. À chaque étape, `mid = (lo + hi) / 2` :
  - Si `KeepsPrior(best[mid], project)` est vrai, l'indice d'insertion $k$ est strictement supérieur à `mid`, donc `lo = mid + 1`.
  - Sinon, $k \le mid$, donc `hi = mid`.
  À terminaison, $lo = hi = k$. L'élément est inséré en `lo = k`.

### 2.3 Préservation de la stabilité (gestion des égalités)
Soit un projet `prior` dans `best` ayant exactement les mêmes `tier`, `score` et `revenueAnnual` que le nouvel arrivant `project` :
- `priorScore == projectScore && prior.revenueAnnual >= project.revenueAnnual` est **vrai** (égalité large `>=`).
- Donc `KeepsPrior(prior, project)` est **vrai**.
- Tout élément déjà présent dans la liste conserve donc la priorité sur le nouvel arrivant.
- Le nouvel arrivant est placé *après* tous les éléments de clé égale.
- L'ordre FIFO / stabilité historique est ainsi rigoureusement préservé.

---

## 3. Mise en cache des clés et cycle de vie du tampon (`SELECT_BISECT_STAMP`)

### 3.1 Structure du cache
Au moment de l'insertion d'un projet, sa clé et ses métadonnées sont attachées à sa table via `rawset` :
- `_bsTier` : entier (priorité défensive C77 + bonus chaîne V88) ;
- `_bsScore` : flottant ou entier (score du champ avec bonus `earlySlot` éventuel) ;
- `_bsRevenue` : entier (`revenueAnnual`) ;
- `_bsField` : chaîne identifiant le champ scoré (`fundScore`, `budgetScore`, `c69Score`) ;
- `_bsEarly` : booléen (`applyEarlySlot`) ;
- `_bsStamp` : entier, horodatage de génération de la passe de sélection courante.

### 3.2 Invalidation et fraîcheur du cache
Lors de l'examen de `best[mid]` par la dichotomie :
- Si `prior._bsStamp == SELECT_BISECT_STAMP && prior._bsField == field && prior._bsEarly == applyEarlySlot`, les champs mis en cache sont directement réutilisés sans aucun appel de fonction ni lookup de table externe.
- Sinon, la clé est recalculée pour `prior` et remise en cache avec le tampon courant.
Ce mécanisme gère naturellement :
- Les listes `best` survivantes entre plusieurs mois (C78 ~1629) : le changement de `SELECT_BISECT_STAMP` force la réévaluation paresseuse à la première comparaison ;
- Les changements de champ (`scoreKey` vs `c69Score`) ;
- Les variations du drapeau `applyEarlySlot`.

### 3.3 Incrémentation de `SELECT_BISECT_STAMP`
`SELECT_BISECT_STAMP` est incrémenté :
1. Au début de `OpexProjectSelectAffordable` (`ai/OpexAI/projects_selection.nut:1078`) ;
2. À l'entrée du filet de sécurité (safety net, `projects_selection.nut:1306`), lorsque le plancher de profit a tout écarté et que les alternatives sont re-scorées.

---

## 4. Conditions de repli sur le chemin historique

Le chemin rapide est conditionné par :
```squirrel
local c118Active = C118_AIR_TERRITORIAL_EXPANSION
    && C118_AIR_PROJECT_SNAPSHOT != null
    && ("active" in C118_AIR_PROJECT_SNAPSHOT) && C118_AIR_PROJECT_SNAPSHOT.active;
local useBisect = SELECT_BISECT_INSERT && !forceHistoric && !c118Active
    && !(C122_AIR_REGIME_SHADOW && C121_AIR_PROJECT_REALIZATION_REGIME == 0);
```

Le repli sur le chemin historique s'opère si l'une des conditions suivantes est remplie :
1. **`SELECT_BISECT_INSERT == 0` :** réglage désactivé (défaut).
2. **`c118Active == true` :** l'expansion territoriale C118 applique un comparateur non-lexicographique complexe multi-critères (`c118NewTowns`, `c118NextDays`, `c118C68Profit`, `c118C68Roi`). Le chemin historique est conservé intact (avec hissage de `c118Active` hors de la boucle, invariant vérifié).
3. **`C122_AIR_REGIME_SHADOW && C121_AIR_PROJECT_REALIZATION_REGIME == 0` :** la sonde shadow C122 émet des traces `OpexC122TraceShadow` pour chaque comparaison de paires AIR durant la boucle linéaire ; elle requiert donc le parcours historique pas-à-pas.
4. **`forceHistoric == true` :** passé explicitement par les appelants diagnostiques / hors production.

### Choix de conception pour les appelants diagnostiques (`forceHistoric = true`)
Les fonctions de sonde diagnostique :
- `OpexC121KDecColdShadowEnd` (`projects_selection.nut:986`)
- `OpexAmortProbeEnd` (`selection_diagnostics.nut:96-97`)
créent des copies superficielles de projets (`clone project`) et modifient localement `shadowProject.fundScore = row.coldScore` ou `after.fundScore = OpexProjectScore(...)`.\
En Squirrel, un `clone` duplique les slots de la table, y compris `_bsStamp` et `_bsScore`. Si ces sondes utilisaient la dichotomie sur un clone sans réinitialisation explicite des champs, la lecture de `_bsScore` lirait l'ancien score pré-clonage si le tampon coïncidait.
Pour garantir une **sécurité absolue** sans surcharger le code :
- Ces appelants passent explicitement `forceHistoric = true` à `OpexProjectInsertDefensive` ;
- En défense en profondeur, ils incrémentent également `SELECT_BISECT_STAMP++` à leur entrée.
Les sondes diagnostiques étant inactives en partie standard et hors chemin critique, cette séparation garantit zéro régression et zéro interférence avec le cycle de vie du cache en production.

---

## 5. Validation et tests d'équivalence

### 5.1 Banc Python d'équivalence stricte
Un harnais dédié a été implémenté dans `sweeps/test_v154_bisect_equivalence.py` :
- Transcription fidèle des deux algorithmes en Python (`insert_defensive_historic` et `insert_defensive_bisect`) ;
- Tests unitaires ciblés : liste vide, élément unique, tri strict, stabilité sur égalités parfaites (FIFO), priorité relative (tier > score > revenue), cas `limit = 1` (déduplication `pairBest`), invalidation paresseuse de tampon et champ ;
- **Fuzzing massif :** 5 000 séquences aléatoires de 1 à 100 projets avec collisions massives sur tiers $\in \{0, 1, 2\}$, scores positifs/négatifs/flottants et revenus avec égalités fréquentes, testées pour des limites allant de 1 à 64 ;
- Vérification que pour chaque insertion de chaque séquence, l'ordre résultant et les identifiants sont strictement identiques entre les deux algorithmes.
- **Contrats Squirrel :** vérification de la déclaration dans `info.nut` (défaut 0, 4 difficultés à 0, `AICONFIG_BOOLEAN`), dans `globals_pre.nut`, du chargement dans `settings.nut`, des signatures et des gardes dans `projects_selection.nut` et `selection_diagnostics.nut`.

Exécution :
```bash
PYTHONPATH=/home/deploy/.local/lib/python3.13/site-packages:sweeps python3 -m unittest sweeps/test_v154_bisect_equivalence.py
```
Résultat : **12 tests passés avec succès en 1,4 s** (0 échec).

### 5.2 Tests de non-régression
- `test_physical_counters.py` : 8 tests OK ;
- `test_game_health.py` : 27 tests OK ;
- `test_campaign_freeze.py` : 17 tests OK ;
- `sweeps/bench_1v1_5y_20seeds.py --selftest` : réussi avec succès ;
- `git diff --check` : aucun avertissement de whitespace.

---

## 6. Diff résumé des fichiers modifiés

```diff
 ai/OpexAI/globals_pre.nut           |   5 +
 ai/OpexAI/info.nut                  |   6 +
 ai/OpexAI/projects_selection.nut    | 120 +++++++++++++++++++++++++-----------
 ai/OpexAI/selection_diagnostics.nut |   5 +-
 ai/OpexAI/settings.nut              |   1 +
 sweeps/test_v154_bisect_equivalence.py | 299 +++++++++++++++++++++++++++++++++++
```
