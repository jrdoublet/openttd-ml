# V91 — Heuristique pondérée du pathfinder rail (Weighted A*)

Date : **2026-09-24**.  
Statut réconcilié au 30 septembre : **poids 120 retenu par décision utilisateur
du 24 après le 20×10 neutre ; poids 150 rejeté**. Les étapes ci-dessous conservent
la conception et les essais historiques, pas un banc à relancer.
Voir [synthèse](journaux/synthese_decisions_2026-09-30.md) et [tâches](taches.md).
Objectif : **réduire fortement le nombre d'itérations d'une recherche ferroviaire** (levier physique direct pour diviser par $\ge 2$ le temps script de recherche), au prix de tracés légèrement sub-optimaux (longueur $\le w \times \text{optimum}$, typiquement +1 à +5 % en pratique).

---

## 1. Contexte et constats mesurés (reprise fiche 29 §9)

Dans la configuration OpexAI (mesures du 2026-09-24 sur le VPS, graines 100, 999, 1234 × 8 ans) :
- Le pathfinder BaNaNaS consommait en moyenne **2 821 opcodes par itération**.
- Les optimisations V90 (ensemble fermé en table Squirrel native, mémoïsation des tuiles et des ponts, précalcul des coordonnées de buts) ont abaissé ce coût à **2 583 opcodes par itération** (**gain de −8 %**).
- **Pourquoi le gain unitaire reste modeste :** les compteurs d'opcodes OpenTTD NoAI mesurent des instructions Squirrel. Les appels à l'API C++ NoAI (`AIList`, `AITile.GetSlope`, `AIRail.BuildRail` en mode test) ne coûtent que quelques opcodes par appel. Le gros de la dépense se situe dans la logique de la machine virtuelle Squirrel elle-même : gestion du tas binaire en $O(\log n)$, instanciation et parcours des objets `Path`, calculs arithmétiques de `_Cost` et `_Estimate`.
- À tracé strictement identique (arbre d'exploration identique), la marge d'optimisation en opcodes/itération est quasiment épuisée.
- Pour accélérer la recherche par un facteur $\ge 2$ et débloquer plus rapidement les lignes ferroviaires du portefeuille, le seul levier physique efficace est de **réduire drastiquement le nombre d'itérations** nécessaires pour atteindre le but.

---

## 2. Conception de l'heuristique pondérée (Weighted A*)

L'algorithme A* évalue chaque nœud candidat selon la priorité de file $f(n) = g(n) + w \cdot h(n)$ :
- $g(n)$ est le coût exact accumulé depuis le départ (`path.GetCost()`).
- $h(n)$ est l'estimation admissible du coût restant jusqu'au but (`_Estimate`).
- $w \ge 1{,}0$ est le facteur de sur-pondération heuristique (`v91_astar_weight_pct / 100`).

### 2.1 Propriétés théoriques
- Pour $w = 1{,}0$ (100 %) : A* standard exact, optimalité garantie.
- Pour $w > 1{,}0$ : recherche $\epsilon$-admissible, le coût du chemin trouvé est mathématiquement borné par $w \times \text{coût\_optimal}$.
- En pratique sur des grilles 2D avec obstacles, un poids $w \in [1{,}2 ; 2{,}0]$ oriente vigoureusement le front d'onde vers la destination, réduisant le volume de nœuds explorés de 50 % à 80 %, pour un surcoût kilométrique réel de l'ordre de 1 % à 5 %.

### 2.2 Réglages et globale Squirrel
- **Réglage `v91_astar_weight_pct`** (`info.nut`) :
  - Type entier, `min_value = 100`, `max_value = 300`, `step_size = 10`.
  - Défaut initial de conception : **100** (V90 strictement inchangé) ;
    **défaut livré ensuite : 120**. Le fragment ci-dessous est historique.
  - Flags : `0` (entier).
- **Globale `V91_ASTAR_WEIGHT_PCT`** (`globals_pre.nut`) : initialisée à `100`.
- **Chargement** (`settings.nut`) :
  ```squirrel
  local astarWeight = AIController.GetSetting("v91_astar_weight_pct");
  V91_ASTAR_WEIGHT_PCT = (astarWeight != null && astarWeight >= 100 && astarWeight <= 300) ? astarWeight : 100;
  ```

### 2.3 Préservation stricte du coût par itération au défaut 100
Au défaut `v91_astar_weight_pct = 100`, aucun calcul supplémentaire ni branchement conditionnel n'est exécuté dans la boucle chaude d'exploration :
- La sélection de la fonction d'estimation s'effectue à l'instanciation de `OpexRailPathFinderV90` (et lors de `SetWeight`) :
  ```squirrel
  local estimate_fn = (this._weight > 100) ? this._EstimateWeighted : this._Estimate;
  this._pathfinder = this._aystar_class(this._Cost, estimate_fn, ...);
  ```
- À $w = 100$, la fonction passée à AyStar est `_Estimate` historique de V90, sans aucun code supplémentaire.
- À $w > 100$, AyStar appelle `_EstimateWeighted` qui applique la multiplication entière :
  ```squirrel
  if (min_cost >= self._max_cost) return self._max_cost;
  return (min_cost * self._weight) / 100;
  ```
- L'intégrité de 32 bits est garantie : même sur une carte de 2048², `min_cost` $\le 410\,000$ ; avec $w = 300$, le produit est $\le 123 \times 10^6 \ll 2^{31}-1$.
- `path.GetCost()` n'est jamais modifié par le poids : le coût réel accumulé $g(n)$ reste exact pour l'élagage `path.GetCost() >= self._max_cost`, pour le choix du tracé final et pour le calcul de devis de la voie ferrée.

---

## 3. Mode de vérification parallèle (`OpexRailPathfinderCheckerV90`)

Le vérificateur de test activé sous `v90_pathfinder_check = 1` s'adapte au mode pondéré :
- **À $w = 100$ :** comparaison pas à pas lockstep avec `RailPathFinder()` BaNaNaS (détection de divergences nœud par nœud via `step_diff`, puis trace `finish`).
- **À $w > 100$ :** les tracés divergent par construction en raison de l'ordre d'expansion modifié. Le vérificateur désactive donc les alertes de divergence pas à pas.
- **Trace comparative finale `finish_weighted` :**
  Dès que la recherche pondérée se termine, le vérificateur termine la recherche BaNaNaS originale jusqu'au bout pour comparer les résultats réels et émet sous `C56_TASK_TRACE` :
  ```
  V90_CHECK finish_weighted iters_orig=... iters_weighted=... ratio_iters=... len_orig=... len_weighted=... ratio_len=... cost_orig=... cost_weighted=... ratio_cost=...
  ```
- **Hors mode check (`v90_pathfinder_check = 0`) :** la classe de vérification n'est jamais instanciée (surcoût strictement nul).

---

## 4. Instrumentation (`C56_TASK_TRACE`)

L'instrumentation existante `RAIL_SEARCH_END` dans `ai/OpexAI/task_rail.nut` est étendue de façon compatible :
- Clés ajoutées :
  - `result` : résultat catégorisé (`found`, `none`, `cap`).
  - `len` : longueur du tracé trouvé en tuiles (via `OpexResolveSearchTiles(slice).len()`), ou 0 en cas d'échec.
  - `weight` : poids heuristique effectif utilisé (`V91_ASTAR_WEIGHT_PCT` si V90 actif, 100 sinon).
- Format émis :
  ```
  OPEX YYYY-MM-DD C56_TASK RAIL_SEARCH_END primary src=... dst=... outcome=OK result=found iters=... len=... weight=150 budget=... days=... ticks=...
  ```

---

## 5. Analyse des points de vigilance

### 5.1 Effet sur `OpexFrontierAlternatives` (builder_rail.nut)
- **Fonctionnement :** En cas de coupure de segment à 2 000 itérations, `OpexFrontierAlternatives` lit `pathfinder._pathfinder._open._queue[..][1]` pour identifier les $K$ meilleurs nœuds ouverts (priorités les plus faibles) et empiler des alternatives de repli.
- **Impact de la pondération :** La priorité lue est $f(n) = g(n) + w \cdot h(n)$. La sur-pondération de $h$ favorise les nœuds les plus proches géographiquement du but. C'est un effet vertueux : les alternatives sélectionnées sont celles qui ont le plus progressé vers la cible. De plus, une fois le nœud extrait, le chemin conserve son coût exact via `node.GetCost()`.
- **Conclusion :** Aucun effet indésirable, l'algorithme d'alternatives reste pleinement cohérent.

### 5.2 Effet sur la recherche segmentée `OpexAdvanceSegmentedSearch`
- **Fonctionnement :** Les segments s'enchaînent par tranches de 2 000 itérations maximum. La fin d'un segment devient la source active du suivant.
- **Impact de la pondération :** Avec un poids $w \ge 1{,}5$, un segment standard atteint son but en 300 à 800 itérations au lieu de 1 500 à 3 500. Le nombre de coupures de segments et de retours en arrière (`backtracks`) diminue considérablement, simplifiant le tracé final et évitant des fragmentations artificielles de voie.

### 5.3 Effet sur le plafond `HARD_ITERATION_CAP` / budget dynamique 10 000
- **Fonctionnement :** Le budget d'itérations calculé par `OpexIterationBudget` est plafonné à `HARD_ITERATION_CAP = 10 000`.
- **Problème historique :** Plusieurs lignes ferroviaires complexes étaient abandonnées avec le statut `ABND` car 10 000 itérations ne suffisaient pas à traverser la carte.
- **Impact de la pondération :** En réduisant le nombre d'itérations par un facteur 2 à 4, des recherches qui échouaient auparavant pour budget épuisé aboutiront désormais avec succès (`found`). Cela augmente le taux de transformation des projets ferroviaires finançables.

### 5.4 Effet sur le coût réel de construction
- **Sub-optimalité :** Un tracé pondéré peut privilégier une diagonale directe ou contourner plus largement un obstacle, générant quelques tuiles de rail supplémentaires (typiquement 1 à 3 tuiles sur un parcours de 50 tuiles, soit 2 à 5 % de plus).
- **Économie ferroviaire :** Dans OpenTTD, le coût de pose du rail nu est négligeable par rapport aux terrassements, ponts, gares et rames. De plus, les revenus de transport NoAI sont proportionnels à la distance de Manhattan entre les gares d'origine et de destination, qui reste invariante. L'impact économique négatif d'un tracé très légèrement plus long est largement compensé par la mise en service beaucoup plus rapide de la ligne (2 à 3 ans gagnés sans immobiliser le slot de recherche).

### 5.5 C41 (vitesse effective)
- `OpexRailEffectiveSpeed` modélise l'accélération et les ralentissements en courbe pour la planification de rames et l'évaluation des candidats.
- Cette fonction n'intervient pas dans `_Estimate` ni dans la boucle chaude du pathfinder. Elle reste strictement inchangée.

---

## 6. Protocole de validation proposé

### Étape 1 : Smoke de conformité (1 graine × 1 an)
- **Objectif :** Vérifier l'absence d'erreur runtime, le respect du contrat de trace et le fonctionnement de `OpexRailPathfinderCheckerV90` en mode pondéré.
- **Configuration :** `v90_fast_pathfinder=1`, `v90_pathfinder_check=1`, `v91_astar_weight_pct=150`, `probe_events=1`, graine 42 sur 1 an.
- **Critère de succès :** Pas de crash, présence de traces `V90_CHECK name=finish_weighted` ou `step_identical` selon activation, 0 régression de santé de partie.

### Étape 2 : Mesure d'exposition et des grandeurs physiques (3 graines × 8 ans)
- **Configuration :** Graines 100, 999, 1234 sur 8 ans, avec `probe_events=1` et `probe_scheduler=1`.
- **Comparaison des bras :**
  1. Référence : `v91_astar_weight_pct=100` (défaut).
  2. Variante 1 : `v91_astar_weight_pct=150` (poids $1{,}5$).
  3. Variante 2 : `v91_astar_weight_pct=200` (poids $2{,}0$).
- **Grandeurs mesurées :**
  - Nombre moyen d'itérations par recherche ferroviaire (`iters` dans `RAIL_SEARCH_END`).
  - Durée calendrier des recherches en jours (`days`).
  - Longueur moyenne des tracés trouvés (`len`).
  - Taux de succès des recherches (`found` vs `cap` / `none`).

### Étape 3 : Duel apparié officiel (20 graines × 10 ans)
- **Objectif :** Qualification économique causale face à AAAHogEx avant toute adoption par défaut.
- **Commande hôte :**
  ```bash
  python3 sweeps/run_c66_reference.py \
    --campaign v91_astar_weight_20x10 \
    --years 10 \
    --reference "OpexAI" \
    --variant "OpexAI[v91_astar_weight_pct=150]" \
    --variant-policy-id "v91_astar_weight" \
    --primary-metric "profit_year" \
    --min-useful-primary-delta 50000 \
    --value-guard-max-loss-pct 5.0 \
    --max-workers 3
  ```
- **Seuils d'adoption :**
  - Métrique primaire : `profit_year` $\ge +50\text{ k\pounds/an}$.
  - Garde-fou de valeur : dégradation de la valeur d'entreprise $\le -5\,\%$.
  - Test bilatéral exact des signes : $p < 0{,}05$ ($\ge 15/20$ victoires).

---

## Mesures du 2026-09-24 (session VPS)

Mode vérification (`v90_pathfinder_check=1`, `probe_events=1`) : chaque recherche est jouée à la
fois par l'A* original et par l'A* pondéré, sur la même carte au même moment ; trace
`V90_CHECK name=finish_weighted`. Graines 100/999/1234 × 8 ans (`results/v91_w150.jsonl`,
`results/v91_w200.jsonl`, worktree `.wt_v91`, non versionnés). La graine 1234 ne lance aucune
recherche rail. La colonne « coût A* » est le `GetCost()` du chemin (pénalités de virage, pente,
pont, côte comprises), pas un coût en livres.

| poids | recherches | itérations original → pondéré | ratio itérations (médiane, étendue) | longueur (tuiles) | coût A* |
|---|---:|---|---|---|---|
| 150 | 8 | 2 589→713, 5 517→384, 1 669→123, 5 863→221, 9 669→168, 4 928→103, 3 470→1 035, 8 129→263 | **≈ 0,05** (0,017 – 0,30) | +0 à +3 % | +3 à +22 % (médiane ≈ +8 %) |
| 200 | 7 | 2 589→566, 11 867→318, 11 774→318, 26 628→316, 1 762→98, 3 470→345, 1 888→133, 1 260→95 | **≈ 0,06** (0,012 – 0,22) | −9 à +6 % | +1 à +29 % (médiane ≈ +12 %) |

Lecture :
- Le nombre d'itérations d'une recherche est divisé par **≈ 20** (3 à 80 selon la recherche) dès
  le poids 150 ; 200 n'apporte presque rien de plus et dégrade davantage le coût A* du tracé.
- **Des recherches qui échouaient deviennent possibles** : à 200, trois recherches demandent
  11 774 à 26 628 itérations à l'original, au-delà du plafond de 10 000 (`HARD_ITERATION_CAP`) :
  au défaut, elles auraient été abandonnées ; pondérées, elles aboutissent en ~320 itérations.
- La colonne `days` de `RAIL_SEARCH_END` est gonflée en mode vérification (l'original tourne
  aussi) ; le délai réel de mise en service n'est pas mesuré ici.

Poids retenu pour le duel : **150**. Duel apparié 20×10 contre le défaut (V90 + C76) lancé le
2026-09-24 : campagne `v91_w150_vs_default_10y_20seeds_20260924`, `profit_year`, effet utile
+50 k£/an, garde de valeur −5 %.

### Duel 20×10 au poids 150 (2026-09-24)

Campagne `v91_w150_vs_default_10y_20seeds_20260924b` (worktree `.wt_v91`, base `dd4058d` + V91,
référence = défaut V90 + C76, 3 CPU / 2 Go / 3 workers) : 40/40 parties, 20/20 paires,
statuts `complete/complete`.

| métrique | résultat |
|---|---|
| `profit_year` (variante − référence) | moyenne **−40,8 k£/an**, médiane **−80,1 k£/an**, IC95 [−126,5 ; +44,9] k£/an |
| victoires / défaites | **7 / 13** (p signes = 0,26) |
| valeur d'entreprise | −1,58 % (garde −5 % tenue) |
| verdict du harnais | `fail_primary` |

Lecture : aucun gain. Selon la règle d'adoption des optimisations d'opcodes (AGENTS.md §4),
l'absence de perte significative est techniquement acquise (IC95 non entièrement négatif,
signes non significatifs, garde tenue), mais V91 change les tracés et la tendance est négative
(13 défaites, médiane −80 k£/an). Hypothèses : tracés plus sinueux (coût A* +8 % médian, pentes
et virages) qui ralentissent les trains et coûtent plus à construire ; lignes supplémentaires
issues de recherches qui échouaient auparavant, sans qu'elles soient rentables. Non adopté au
poids 150 ; défaut 100.

**Clôture (décision utilisateur du 2026-09-24).** V91 est clos. Le code reste disponible derrière
`v91_astar_weight_pct` (défaut 100, chemin V90 inchangé), réutilisable si les chaînes de biens (V88)
exigent des recherches rail rapides. Gain d'opcodes : ≈ ÷ 20 sur une recherche, mais l'A* rail ne
pèse qu'environ 1 % du temps de script ; l'effet principal était le délai de mise en service, que
le duel ne valorise pas.

### Occupation du terrain (même duel, écarts appariés V91 − défaut, fin de partie)

| | moyenne | médiane | hausses/baisses |
|---|---|---|---|
| trains OpexAI | 1,15 → 4,1 | +3 | 17/1 |
| gares rail OpexAI | 2,1 → 7,6 | +4 | 16/1 |
| véhicules OpexAI | +9 | +10 | 15/5 |
| profit/an AAAHogEx | +47 k£ | −52 k£ | 10/10 |
| valeur AAAHogEx | −0,77 M£ (≈ −2 %) | −1,7 M£ | 9/11 |
| trains AAAHogEx | +4,8 | +3 | 11/9 |

V91 fait bien prendre des lignes rail (présence ×3,5, constante), mais AAAHogEx n'en est pas
gênée et ces lignes ne paient pas assez pour compenser. L'occupation du terrain ne vaut que si
les lignes prises sont bonnes : à rejouer quand le rail sera rentable ligne par ligne.

### Poids 120 : adopté par défaut (2026-09-24)

Mode vérification, graines 100/999/1234 × 8 ans (`results/v91_w120.jsonl`) : 5 recherches,
itérations 2 863→1 853, 1 820→241, 9 582→389, 5 863→1 081, 3 470→1 313 : ratio médian **0,18**
(÷ 5,4) ; longueur identique (médiane 1,00) ; coût A* **+3,6 %** médian (0 à +9,6 %).

Duel 20×10 contre le défaut (V90 + C76), campagne `v91_w120_vs_default_10y_20seeds_20260924`,
40/40 parties, 20/20 paires, statuts `complete` :

| métrique | résultat |
|---|---|
| `profit_year` (variante − référence) | moyenne −28,6 k£/an, médiane **+28,1 k£/an**, IC95 [−127,4 ; +70,1] |
| victoires / défaites | **11 / 9** (p signes = 0,82) |
| valeur d'entreprise | −0,79 % (garde −5 % tenue) |
| trains / gares rail OpexAI | 1,15 → 2,35 trains (12/1), +2,3 gares rail (12/1) |
| profit/an AAAHogEx | −169 k£ (médiane −190 k£, 8/12) |
| verdict du harnais | `fail_primary` (seuil +50 k£/an non visé) |

**Décision utilisateur du 2026-09-24 : `v91_astar_weight_pct` = 120 par défaut**, en application
de la règle d'adoption des optimisations d'opcodes (AGENTS.md §4) : recherches ÷ 5, tracés presque
optimaux, 20×10 sans perte. Le poids 150 reste rejeté (tracés +8 %, 7/13).

---

## 7. Rentabilité par mode : outil d'analyse (`sweeps/analyse_line_profit_by_mode.py`)

Sous V91 (défaut 120), le nombre moyen de trains par partie passe de 1,15 à 2,35 (+1,2 train/partie, 12 hausses / 1 baisse), mais sans accroissement correspondant du profit annuel (`profit_year` médian +28,1 k£/an, moyen −28,6 k£/an, 11/9). Pour discriminer entre lignes ferroviaires déficitaires en valeur absolue et lignes ferroviaires rapportant simplement un ROI plus faible que l'aérien par livre investie, l'outil `sweeps/analyse_line_profit_by_mode.py` extrait la rentabilité par ligne et par mode (rail, air, route, eau) à partir des journaux bruts de diagnostic.

### Protocole de collecte des traces

Lancer un diagnostic avec les sondes de portfolio et d'événements activées (`probe_portfolio=1,probe_events=1`) sur un échantillon représentatif (ex. 5 graines × 8 ans) :

```bash
python3 sweeps/diag_c69_bottleneck_probe.py \
  --arm "OpexAI[probe_portfolio=1,probe_events=1]" \
  --seeds 42,100,999,1234,5678 \
  --years 8 \
  --grep "C56_TASK" \
  --raw results/c56_task_diag_5x8.jsonl
```

### Analyse de la rentabilité

```bash
# Rapport synthétique en texte avec tableau récapitulatif et détail rail :
python3 sweeps/analyse_line_profit_by_mode.py results/c56_task_diag_5x8.jsonl

# Export structuré JSON :
python3 sweeps/analyse_line_profit_by_mode.py results/c56_task_diag_5x8.jsonl --json

# Validation autonome des calculs et contrats :
python3 sweeps/analyse_line_profit_by_mode.py --selftest
python3 -m unittest sweeps/test_analyse_line_profit_by_mode.py
```

### Métriques produites par mode
- **Nombre de lignes** et lignes exploitables ;
- **Profit annuel réalisé par ligne** : moyenne, médiane, part des lignes déficitaires (profit < 0) ;
- **Capital moyen / médian par ligne** et capital total investi ;
- **ROI annuel (profit / capital)** : moyenne, médiane et ratio macro (somme des profits / somme des capitaux) ;
- **Âge moyen / médian des lignes** ;
- **Détail spécifique au rail** : liste de chaque ligne ferroviaire avec sa distance, son nombre de trains, son profit par an de service plein, son capital, son année de construction et son statut ;
- **Règle de traitement** : déduplication par `(seed, line_id, profit_year)` et exclusion par défaut de l'année de mise en service (incomplète) pour mesurer la rentabilité pérenne.

### Rentabilité par mode : première mesure (2026-09-24)

Défaut courant (V90 + V91 à 120 + C76), `probe_portfolio=1,probe_events=1`, graines
42/100/999/1234/5678 × 8 ans (`results/lineprofit_5x8.jsonl`), analysé par
`sweeps/analyse_line_profit_by_mode.py`. Année de mise en service exclue ; capital rail = coût réel
payé (recalé par `OpexApplyRailActualCapital`).

| mode | lignes (évaluées) | profit/an médian | pertes | capital moyen | ROI macro |
|---|---:|---:|---:|---:|---:|
| rail | 5 (3) | 28,5 k£ | 0 % | 52,7 k£ | **57,5 %** |
| air | 338 (250) | 45,9 k£ | 1,2 % | 85,8 k£ | **61,4 %** |
| route | 49 (39) | 0,7 k£ | 5,1 % | 12,6 k£ | 43,0 % |

Lecture : les lignes rail ne perdent pas d'argent ; leur rendement par livre est proche de
l'aérien (57,5 % contre 61,4 %), mais elles sont **rares** (5 lignes sur 40 graines-années, un
train chacune). Échantillon trop petit pour conclure ligne à ligne (3 lignes évaluées ; ROI
21,5 % à 106,9 %). Le rail n'est donc pas un gouffre : sa limite est le volume (vivier, un seul
créneau de recherche, un train par ligne), pas la rentabilité unitaire.
