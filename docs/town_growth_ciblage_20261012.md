# Rapport d'analyse : Tâche `town_growth` (Croissance urbaine) — Mécanique, Bancs et Recommandation

**Date :** 12 octobre 2026  
**Sujet :** Ligne « Town growth OFF — coût/bénéfice » de `docs/taches.md` (ligne 760 : « Défaut 0 sur décision utilisateur ; futur ciblage vs OFF »)  
**Documents de référence :** `docs/town_growth_off_20261002.md`, `docs/mecanique_jeu.md`, `docs/taches.md`, `docs/journaux/journal_2026-10-02.md`, `docs/journaux/journal_2026-10-04.md`  
**Cadre strict :** Lecture de fichiers et analyse empirique sans commande Docker, sans banc, sans commit ni modification de code.

---

## 1. Fonctionnement actuel de la tâche `town_growth` dans le code

### 1.1 Déclaration, ordonnancement et réglages
- **File du planificateur :** Dans [`ai/OpexAI/main.nut:449`](../ai/OpexAI/main.nut#L449), la tâche est initialisée dans `_taskQueue` :
  ```squirrel
  { name = "town_growth", dueCycle = 0, enabled = true }
  ```
- **Déclaration du réglage :** Dans [`ai/OpexAI/info.nut:1523-1529`](../ai/OpexAI/info.nut#L1523-L1529), `town_growth` est déclaré avec une valeur par défaut de **0** pour les quatre niveaux (`easy_value = 0`, `medium_value = 0`, `hard_value = 0`, `custom_value = 0`).
- **Chargement du réglage :** Dans [`ai/OpexAI/settings.nut:177`](../ai/OpexAI/settings.nut#L177) :
  ```squirrel
  TOWN_GROWTH_ENABLED = AIController.GetSetting("town_growth") != 0;
  ```
  Le repli statique dans [`ai/OpexAI/globals_post.nut:149`](../ai/OpexAI/globals_post.nut#L149) est `TOWN_GROWTH_ENABLED <- false`.
- **Réglages associés :**
  - `town_growth_plan_memo` ([`info.nut:1531-1536`](../ai/OpexAI/info.nut#L1531-L1536), défaut 1) : mémorise les échecs de tracé routier pour ne retenter qu'en cas de variation du nombre de maisons.
  - `town_growth_skip_noop` ([`info.nut:1539-1544`](../ai/OpexAI/info.nut#L1539-L1544), défaut 0) : passe immédiatement à la tâche suivante en cas d'essai vide.
  - `town_growth_roi_gate` ([`info.nut:1547-1552`](../ai/OpexAI/info.nut#L1547-L1552), défaut 1) : conditionne la construction d'une ligne de bus intra-urbaine à une prédiction de profit annuel positive et ferme les lignes déficitaires.
  - `c80_worker_town` ([`info.nut:1596-1601`](../ai/OpexAI/info.nut#L1596-L1601), défaut 0) : découpe optionnel en travailleur résumable C80.

### 1.2 Comportement quand `town_growth = 0` (défaut actuel)
Lorsque le planificateur rencontre `town_growth` ([`ai/OpexAI/scheduler.nut:370-375`](../ai/OpexAI/scheduler.nut#L370-L375)), il appelle `_dispatchTownGrowth(task, year)` ([`ai/OpexAI/scheduler_tasks.nut:1029`](../ai/OpexAI/scheduler_tasks.nut#L1029)).
À la ligne 1031 de `scheduler_tasks.nut` :
```squirrel
if (!TOWN_GROWTH_ENABLED) {
    task.enabled = false;
    if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
    return false;
}
```
**Effet immédiat :** `task.enabled` passe à `false`. Dès lors, le planificateur, qui filtre sur `candidate.enabled` ([`ai/OpexAI/scheduler.nut:284`](../ai/OpexAI/scheduler.nut#L284)), n'appelle plus jamais `_dispatchTownGrowth` pour le reste de la partie.
**Coût à 0 :** **0 £** et **0 opcode** (hors un test conditionnel unique lors du tout premier cycle).

### 1.3 Comportement quand `town_growth = 1`
Si `town_growth = 1`, `TOWN_GROWTH_ENABLED` est vrai.
- **Ordonnancement :** Par défaut (`c80_worker_town = 0`), le code exécute la branche monolithique synchrone via `_tryTownGrowth(year)` ([`scheduler_tasks.nut:1083-1094`](../ai/OpexAI/scheduler_tasks.nut#L1083-L1094) et [`task_town.nut:283-303`](../ai/OpexAI/task_town.nut#L283-L303)). Si `c80_worker_town = 1`, un travailleur résumable `OpexWorkerTownGrowthStep` ([`orchestrator.nut:367-411`](../ai/OpexAI/orchestrator.nut#L367-L411)) examine une ville par tranche d'opcodes.
- **Sélection des villes candidates :**
  1. `_prepareTownGrowth()` ([`task_town.nut:82-96`](../ai/OpexAI/task_town.nut#L82-L96)) :
     - Vérifie la trésorerie disponible : `money >= OpexCashReserve() + 25000` (exige une marge de 25 000 £ au-dessus de la réserve de sécurité).
     - Vérifie la présence d'un type de route et d'un véhicule passagers routier au catalogue (`_catalog.roadEngineByCargo[paxCargo]`).
     - Appelle `OpexGetServedTowns(this._lines)` ([`task_town.nut:26-49`](../ai/OpexAI/task_town.nut#L26-L49)).
     - **Critère de sélection :** Il extrait **toutes les villes desservies par au moins une gare valide d'OpexAI, tous modes confondus** (lignes rail, air, route ou eau existantes).
  2. Parcours dans `_tryTownGrowthCity(townId, year, anchor)` ([`task_town.nut:100-278`](../ai/OpexAI/task_town.nut#L100-L278)) :
     - **Exclusion 1 :** Si la ville possède déjà une ligne de bus passagers Opex (`OpexTownBusPaxServed`, l. 106-108, défini dans [`candidates.nut:2489-2505`](../ai/OpexAI/candidates.nut#L2489-L2505)), elle est rejetée (au plus 1 ligne de bus de base par commune).
     - **Exclusion 2 :** Si `TOWN_GROWTH_PLAN_MEMO` est actif et que le tracé routier a déjà échoué pour ce même nombre de maisons (`AITown.GetHouseCount(townId)`), la ville est sautée sans calcul (l. 109-113).
     - **Exclusion 3 :** Si `TOWN_GROWTH_ROI_GATE` est actif et que la ville est en quarantaine d'abandon (l. 116).
     - **Exclusion 4 :** Si `OpexCountTownStations(townId) >= 5` (l. 117-118), la ville est rejetée car le plafond de croissance OpenTTD (5 gares) est déjà atteint.
     - **Exclusion 5 :** Si la population est < 100 habitants (l. 121-122).

- **Mode d'action (financements, panneaux, voirie) :**
  - **Financement de construction (`PerformTownAction`) :** **AUCUN.** OpexAI n'appelle jamais `AITown.PerformTownAction` (`TOWN_ACTION_FUND_BUILDINGS`, `BUILD_STATUE`, `FUND_ROAD_RECONSTRUCTION`, etc.).
  - **Panneaux :** Des panneaux de diagnostic interne sont posés sur la tuile d'ancrage `(1, 1)` :
    - `TG|<an%100>|<townId>|<stations_avant>|<stations_après>` lors d'une construction réussie ([`task_town.nut:243`](../ai/OpexAI/task_town.nut#L243)).
    - `RP|...` si `ROAD_COST_PROBE` est actif ([`task_town.nut:230`](../ai/OpexAI/task_town.nut#L230)).
    Ce sont des marqueurs d'audit, sans impact économique dans la simulation.
  - **Infrastructure et véhicules :**
    - La tâche conçoit et implante une **ligne de bus intra-urbaine** ([`task_town.nut:124-240`](../ai/OpexAI/task_town.nut#L124-L240)) :
      - Arrêt A : centre-ville (`townTile = AITown.GetLocation(townId)`).
      - Arrêt B : tuile excentrée (offset de 6 à 8 tuiles) dans la même commune avec production de passagers > 0.
      - Tracé routier par A* (`OpexRoadPlanFor`, l. 174).
      - Si `TOWN_GROWTH_ROI_GATE = 1`, calcul prédictif via `OpexRoadLineEconomics` (l. 202) : si le profit annuel prévisionnel est $\le 0$, abandon.
      - Construction via `OpexBuildRoadRoute` (l. 226) : 2 arrêts de bus, voirie de liaison, 1 dépôt et 1 bus.
      - Enregistrement dans `_lines` avec `purpose = "town_growth"` (l. 258) et `revenueAnnual = 0`.

- **Coût en £ et en opcodes :**
  - **Coût financier (£) :**
    - Immobilisation de capital : `2 * costRoadBusStop + routeDist * costRoadPerTile + costRoadDepot + engine.price` ([`task_town.nut:195`](../ai/OpexAI/task_town.nut#L195)), soit environ **2 500 £ à 4 000 £** par ligne en 1970.
    - Frais d'exploitation : bus circulant sur un trajet très court en ville, générant des recettes faibles voire négatives.
    - Rythme : ~1,2 ligne construite par an et par partie en régime ON.
  - **Coût en opcodes :**
    - Profil C121 du 2 octobre ([`docs/opcode_profile_c121_20261002.md`](../docs/opcode_profile_c121_20261002.md) cité dans `docs/town_growth_off_20261002.md:8-10`) : `town_growth` consommait **15 % des opcodes totaux d'OpexAI**, dont **95 % en planification routière infructueuse** (A* bloqué par les bâtiments, le relief ou les façades de dépôt).
    - Même avec `town_growth_plan_memo=1`, la charge restait disproportionnée au regard de l'activité réelle.

---

## 2. Mécanique du jeu OpenTTD / NoAI 15.3 (`docs/mecanique_jeu.md`)

### 2.1 Levier réel de croissance urbaine
D'après [`docs/mecanique_jeu.md:324-416`](../docs/mecanique_jeu.md#L324-L416) (Section 5 : « Croissance des villes », vérifiée dans le code source d'OpenTTD 15.3 `src/town_cmd.cpp`) :

1. **Règle d'accélération du moteur de jeu :**
   - « La croissance peut être accélérée en **chargeant ou déchargeant au moins UNE unité de cargo**, dans **jusqu'à CINQ gares** de l'aire d'influence de la ville, sur une fenêtre de **50 jours** (20 ticks d'inactivité). »
   - **Le volume ne compte pas :** 1 passager suffit.
   - Barème de cadence selon le nombre $n$ ($0 \le n \le 5$) de gares actives (en climat tempéré, `town_growth_rate = 2` normal) :
     - $n = 0$ gare active : la ville ne grandit pas dans **11 tirages sur 12** (`Chance16(1, 12)`).
     - $n = 1$ gare active : construction d'un bâtiment tous les **210 ticks ville** $/ (num\_houses / 50 + 1)$ (divisé par 2 si *city*).
     - $n = 2$ gares actives : tous les **150 ticks ville**.
     - $n = 3$ gares : 110 ticks.
     - $n = 4$ gares : 80 ticks.
     - $n = 5$ gares : 50 ticks (plafond d'accélération maximale).

2. **Actions municipales (`AITown.PerformTownAction`) :**
   - `TOWN_ACTION_FUND_BUILDINGS` finance temporairement de nouvelles constructions pendant 3 mois.
   - Coût prohibitif (dizaines de milliers de £), dépend de la cote d'autorité locale et **non utilisé dans OpexAI**.

3. **Note de station :**
   - La note de station n'a **aucun lien** avec la vitesse de croissance urbaine.
   - Elle détermine uniquement la part de production captée par la station : $\text{cargo capté} = \text{production} \times \text{note}$.

### 2.2 Gain de passagers attendu pour une ville pourvue d'un aéroport
- **Déblocage initial :** Dès qu'un aéroport est construit et qu'un avion y assure un service régulier (au moins un chargement/déchargement tous les 50 jours), **la ville compte déjà $n = 1$ gare active**. Elle sort donc immédiatement du régime de quasi-stagnation ($n=0$).
- **Gain marginal d'une 2e gare (bus intra-urbain) :**
  - Passer de $n = 1$ à $n = 2$ accélère la fréquence théorique de $210 / 150 = 1,40$ (+40 % de rythme de construction).
  - Pour une ville de 500 à 1 500 habitants, cela représente un gain modeste de **quelques maisons supplémentaires par an**.
  - Chaque maison ne générant qu'environ 1 à 2 passagers par mois ([`docs/mecanique_jeu.md:374-378`](../docs/mecanique_jeu.md#L374-L378)), le surplus de passagers généré pour l'aéroport après 3 ans d'exploitation est **anecdotique** (de l'ordre de 10 à 25 passagers par mois au bout de plusieurs années).
- **Cannibalisation locale :**
  L'arrêt de bus au centre-ville intercepte une partie des passagers du centre pour les acheminer sur la ligne de bus locale (à rentabilité médiocre), détournant potentiellement du flux du bassin aéroportuaire.

---

## 3. Analyse des deux bancs 20×10 (C115 et C121) et statut du « ciblage aéroports/hubs »

### 3.1 Résultats vérifiés des deux bancs 20×10 (`docs/town_growth_off_20261002.md`)

| Banc (20 graines × 10 ans) | $\Delta \text{profit}$ annuel OFF − ON | IC95 Student | Victoires / Défaites / Égalités | $\Delta \text{valeur}$ | Avions Opex (ON vs OFF) | Bus Opex (ON vs OFF) |
|---|---|---|---|---|---|---|
| **C115 20×10** | **−21,8 k£/an** (−1,0 %) | [−131,9 ; +88,2] k£/an | 10 / 10 / 0 ($p = 1,00$) | +2,05 % | 140,8 vs **156,8** (+16,0) | 19,5 vs **5,8** (−13,8) |
| **C121 20×10** (secondaire) | **+131,8 k£/an** (+9,7 %) | [+19,9 ; +243,7] k£/an | 13 / 7 / 0 ($p = 0,26$) | +9,48 % | 143,1 vs **154,7** (+11,6) | 24,5 vs **10,6** (−13,9) |

*(Chaque banc comporte 40/40 duels sains et 20/20 paires complètes face à AAAHogEx.)*

### 3.2 Signal sur les villes desservies par l'AIR
- **Pas de gain pour ON :**
  - Dans C115, le nombre d'aéroports Opex est équivalent (27,6 en ON vs 27,1 en OFF).
  - Dans C121, **OFF ouvre davantage d'aéroports** que ON (22,3 vs 20,8) et dessert plus de villes aériennes (21,8 vs 20,2).
  - **OFF achète substantiellement plus d'avions** (+16 avions dans C115, +11,6 avions dans C121).
  - **Explication causale :** En coupant `town_growth`, OpexAI ne bloque pas 25 000 £ de trésorerie de précaution, n'immobilise pas son capital dans des lignes de bus intra-urbaines et n'épuise pas ses opcodes en A* routiers. Ce capital et ce temps processeur sont automatiquement captés par le vivier de projets à fort ROI : **les lignes et flottes aériennes**.

### 3.3 Le ciblage « seulement les villes de nos aéroports saturés / hubs » est-il étayé ou spéculatif ?
- **Ce ciblage est purement spéculatif.**
  1. **Absence totale de données :** Aucune métrique de population urbaine différentielle ou de passagers en attente aux aéroports n'a été mesurée pour étayer un gain économique.
  2. **Origine du texte :** La mention « version ciblée aux monopoles aéroportuaires Opex 2-0 » relevait du chantier C83.1. Or l'audit de C83.1 ([`docs/22_c78_lignes_vs_aaa.md:276-380`](../docs/22_c78_lignes_vs_aaa.md#L276-L380)) montre que C83.1 concernait la course aux créneaux aériens (`AIR_C83_TARGET_TOWNS`), sans aucun rapport avec la stimulation urbaine par bus.
  3. **Confirmation lors des retests C121 :** Dans [`docs/journaux/journal_2026-10-04.md:803`](../docs/journaux/journal_2026-10-04.md#L803), réactiver `town_growth` à 1 dégradait le profit de **−8,08 %**. L'entrée consignait expressément :  
     *« Ne pas classer town_growth ou road pax parmi les candidats neutres à prolonger. »*

---

## 4. Recommandation et analyse d'une éventuelle Porte A 40×3

### 4.1 Rappel des exigences de la Porte A V102 (`AGENTS.md` §4)
- **40 graines canoniques × 3 ans**, appariées face à AAAHogEx (80 duels).
- Test exact de Wilcoxon bilatéral : **$p < 0,05$**.
- Borne basse de l'IC95 bootstrap de la moyenne : **$> 0$**.
- Delta moyen : **$\ge +4\ \%$ du profit annuel moyen de référence à l'année 3**.
- Garde de valeur d'entreprise : $\ge -5\ \%$.
- **Règle fondamentale :** L'objectif est le **profit net** pour rattraper AAAHogEx. La valeur patrimoniale n'est pas un objectif.

### 4.2 Hypothèse chiffrée et faisabilité à l'horizon 3 ans
- À l'année 3 (fin 1972), le profit annuel d'OpexAI se situe entre 1 000 et 1 500 k£/an. Le seuil de $+4\ \%$ exige donc un gain net minimum de **$+40\text{ k£ à }+60\text{ k£/an}$**.
- **Trajectoire réelle mesurée aux 3 premières années :**
  Dans [`docs/town_growth_off_20261002.md:215-225`](../docs/town_growth_off_20261002.md#L215-L225), l'écart annuel moyen **OFF − ON** était de :
  - Fin 1970 : $+4,3\text{ k£/an}$ en faveur de OFF
  - Fin 1971 : $+85,1\text{ k£/an}$ en faveur de OFF
  - Fin 1972 (année 3) : **$+78,8\text{ k£/an}$ en faveur de OFF**
- En année 3, **OFF bat ON de près de 80 k£/an**. Les investissements de bus intra-urbains et leur maintenance représentent une perte sèche immédiate qui n'est pas amortie en 3 ans, tandis que la croissance démographique n'a produit que quelques maisons supplémentaires sans impact sensible sur les vols.
- Par conséquent, toute tentative de réactiver `town_growth` (même ciblée) subirait un **`fail_primary` massif et garanti** à la porte A 40×3.

### 4.3 Recommandation formelle

1. **Recommandation principale : CLORE DÉFINITIVEMENT LA PISTE.**
   - Dans `docs/taches.md` (ligne 760), remplacer l'indication d'un éventuel « futur ciblage vs OFF » par un statut **Clos** : maintien définitif de `town_growth = 0`.
   - **Raisons :**
     - OpexAI bénéficie déjà de la croissance des villes pourvues d'aéroports ($n=1$ gare active).
     - Le surcoût en capital et en opcodes (15 % du temps CPU) pénalise directement l'expansion du réseau aérien.
     - L'écart avec AAAHogEx provient du manque de lignes et d'avions à fort ROI (doctrine V106 / V108), pas d'un manque de passagers au sol.

2. **Alternative minimale (si l'utilisateur refuse la clôture sans sonde) :**
   - **Interdire tout banc comportemental 40×3.**
   - Mettre en place uniquement une **sonde passive d'analyse post-mortem** (script Python hors ligne analysant les sauvegardes des bancs V93bis ou V108) pour mesurer l'évolution réelle de la population entre villes à 1 gare et villes à 2+ gares sur 10 ans, afin de vérifier si l'accélération OpenTTD a un effet mesurable sur la carte.

---

## Note de relecture (Claude, 12/10)

Vérifié dans `docs/town_growth_off_20261002.md` (trajectoire annuelle, banc C121 20×10) : OFF−ON = +4,3 / +85,1 / +78,8 k£/an en 1970 / 1971 / 1972, toujours favorable à OFF jusqu'en 1978. Un ciblage partirait de ce handicap à l'horizon de la porte A (3 ans) ; aucune mesure n'étaye un gain propre aux villes aériennes. **Piste close, `town_growth=0` maintenu.**
