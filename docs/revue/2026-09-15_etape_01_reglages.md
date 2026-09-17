# Étape 01 — Réglages et globales

- **SHA revu** : `83dfcf4` (`ai/OpexAI/` au 2026-09-15)
- **Modèle / effort** : Opus 5 / high
- **Périmètre** : `ai/OpexAI/info.nut` (lecture déclarative), `settings.nut`, `globals_pre.nut`, `globals_post.nut` — 3 809 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Recomptage** — le plan annonçait « 227 `AddSetting` contre 213 `GetSetting` ». Au SHA revu :
**227 `AddSetting`** (aucun nom en double, aucun `*_value` divergent, aucun défaut hors
`[min_value, max_value]`) et **224 `GetSetting`** dans `settings.nut`, plus 3 lectures directes
hors de la couche de réglages. **82 défauts actifs** (valeur ≠ 0), conforme au plan.

---

## Constats

### 01.1 — `RAIL_EXPAND_APPROACH_TILES` n'est définie nulle part        [gravité : P1]

`task_rail.nut:521` et `task_rail.nut:565` — les deux sites lisent la globale
`RAIL_EXPAND_APPROACH_TILES`. Aucune définition n'existe dans le dépôt : ni `const`, ni `enum`,
ni affectation de premier niveau (`grep -rn 'RAIL_EXPAND_APPROACH_TILES' ai/` ne rend que ces
deux lectures, et `git log -S 'RAIL_EXPAND_APPROACH_TILES ='` / `'<-'` est vide sur tout
l'historique). En Squirrel, lire un slot inexistant de la table racine lève
`the index 'RAIL_EXPAND_APPROACH_TILES' does not exist` **à l'exécution**, pas à la compilation.

*Ce que le code prétend faire* : `_expandRailLines` ne déclenche `_continueRailExpansion()` que si
la rame est déjà à portée du dépôt ; `_continueRailExpansion` n'injecte l'ordre d'arrêt temporaire
qu'à l'approche. Les deux tests reposent sur ce seuil.

*Conséquence observable* : inerte aux défauts livrés — `rail_expand = 0` fait sortir la boucle par
le `break` de `task_rail.nut:319`, `best` reste nul, et le `return` de `task_rail.nut:486` coupe
avant la ligne 521 ; `_continueRailExpansion` n'est atteignable que par `this._railExpansion`, que
seul ce chemin arme. Mais **dès qu'un bras de banc pose `rail_expand = 1`** — exactement le bras
qu'appelle G5 — la première expansion de wagons éligible tue le script sur une erreur d'exécution.
C'est le mode de mort silencieuse décrit dans `CLAUDE.md` (« une erreur Squirrel tue l'IA presque
en silence »). Ce n'est **pas** une régression C65 : les deux lectures ont été introduites par

**Corrigé le 2026-09-16 (B5).** `main.nut` définit maintenant
`RAIL_EXPAND_APPROACH_TILES = 8`. La valeur reprend la fenêtre locale déjà utilisée par
`OpexPlacePathApproachSignal` dans `builder_rail.nut` (`maxDistance=8`). Le test ciblé
`sweeps/test_b5_rail_persistence.py` vérifie une définition et les deux lectures. Le diagnostic
conditionnel `results/review_b5_rail_expand_5x6.json` exécute 5 graines × 6 ans avec
`rail_expand=1` : 5/5 parties complètes et zéro `protocol_failure`. `rail_expand` reste à 0.
`5a41488` (2026-09-11) sans jamais que la constante existe.

### 01.2 — Le bras de contrôle `road_pax_catchment_pct = 0` n'existe pas, pour deux raisons indépendantes        [gravité : P1 — constat de mesure]

`info.nut:2136-2137` déclare `min_value = 0` et documente explicitement la valeur 0 :
`"86 = measured route default; 0 = historical 22% rail-calibrated control"`. `info.nut:2131-2133`
et `docs/journal_2026-08-29.md:848-851` s'appuient sur ce bras (« `0` rétablit le contrôle à
22 % », banc apparié 20 graines, `results/bench_road_pax_catchment.json`).

1. `settings.nut:38-39` — `local roadPaxCatchment = GetSetting("road_pax_catchment_pct");`
   puis `if (roadPaxCatchment > 0) ROAD_PAX_CATCHMENT_SHARE_PCT = roadPaxCatchment;`. À 0, la
   garde refuse l'affectation et la globale **conserve son initialisation à 86**
   (`globals_pre.nut:21`). Le bras de contrôle produit donc *exactement* le comportement du bras
   traité.
2. Même si la garde laissait passer, `candidates.nut:2242-2244` calcule
   `pct = (ROAD_STOP_CATCHMENT_HOUSES * 100) / houses`, la plafonne par
   `ROAD_PAX_CATCHMENT_SHARE_PCT`, puis applique `if (pct < 1) pct = 1`. À 0 le captage
   tomberait à **1 %**, pas à 22 %. Aucun chemin ne relie 0 à `TOWN_CATCHMENT_SHARE_PCT = 22`
   (`candidates.nut:1342`), qui sert au rail.

*Conséquence observable* : tout banc opposant `road_pax_catchment_pct` 86 à 0 compare deux bras
identiques. Par la méthode du projet, deux bras identiques sur une graine sont des ex æquo, donc
« le drapeau n'a pas joué » — le banc ne peut structurellement rien mesurer. Le t = 2,48 / 14/20
cité en `info.nut:2131-2132` pour justifier le défaut 86 est à re-qualifier. L'historique du dépôt
commence au 2026-09-11 : impossible d'établir ici si la garde existait déjà au 2026-08-30.

### 01.3 — `feeder_mail_strict_orders` : banc sous le plancher **et** bras épinglés hors des défauts livrés        [gravité : P2 — constat de mesure]

`info.nut:1303` (défaut 1, adopté le 2026-09-15 par `c74a123`). La fiche
`docs/taches.md:652-672` donne le banc : 5 graines × 3 ans, 0/5 victoire, −332 789 £ de valeur.
Le plan le retenait déjà comme « ni 20 graines, ni 10 ans, ni p-value, et économiquement
négatif ». S'y ajoute un défaut de protocole non relevé jusqu'ici, lisible en confrontant
`docs/taches.md:664-666` aux défauts de `info.nut` :

| Réglage épinglé dans les deux bras | Valeur au banc | Défaut livré |
|---|---:|---:|
| `feeder_candidates` | 1 | **0** (`info.nut`) |
| `feeder_portfolio` | 0 | **1** (`info.nut:1179`) |
| `feeder_hub_check` | 0 | **1** (`info.nut:1364`) |
| `feeder_mail_duplicate` | 1 | 1 (`info.nut:1295`) |

*Conséquence observable* : les deux bras « forcent exactement le même ancien régime feeder » — un
régime que **trois réglages sur quatre** séparent de la configuration livrée. Le résultat, négatif
compris, ne se transporte pas au défaut adopté. C'est le constat G0 du 09-06 (épinglage des bras,
bras de contrôle inclus) dans sa forme la plus récente, sur le drapeau le plus récemment adopté.

### 01.4 — `event_vehicle_autoreplaced` : réglage actif, jamais lu, globale jamais lue        [gravité : P2]

`info.nut:210` — défaut 1. Aucun `GetSetting("event_vehicle_autoreplaced")` nulle part.
`globals_pre.nut:410` définit `EVENT_VEHICLE_AUTOREPLACED <- true`, et **cette globale n'est lue
par aucun fichier** : le remappage d'IDs est inconditionnel. Le commentaire de `settings.nut:133-135`
assume la décision (« l'ancien interrupteur reste déclaré dans `info.nut` mais l'intégrité des IDs
n'est plus optionnelle, donc il n'est pas lu ») — mais il est posé au-dessus de
`C52_AUTOREPLACE_LOG`, qui, lui, *est* lu : le commentaire décrit un autre réglage que la ligne
qu'il précède.

*Conséquence observable* : le réglage reste exposé dans l'interface de configuration avec un
défaut à 1. Un bras de banc posant `event_vehicle_autoreplaced = 0` obtient des bras identiques,
donc des ex æquo lus comme « le drapeau n'a pas joué » alors que le drapeau n'est pas câblé. La
globale câblée à `true` et jamais lue est le second piège : elle fait croire au grep qu'un garde
existe. **Le plan renvoyait ce cas à l'étape 12 ; il est tranché ici, rien à y rouvrir** — reste à
l'étape 12 la seule question du comptage `33/33 untracked` sur 16 ans.

### 01.5 — Trois plafonds documentés ne sont plus appliqués        [gravité : P2]

`globals_post.nut:9`, `:24`, `:25` — `CASH_CANDIDATE_SCAN_LIMIT <- TOP_K`,
`ROAD_MAX_NEW_LINES_PER_YEAR <- 36`, `ROAD_MAX_ATTEMPTS_PER_YEAR <- 60`. **Aucune des trois n'est
lue** dans le dépôt.

- `ROAD_MAX_NEW_LINES_PER_YEAR` était l'argument `maxItems` de `OpexKnapsackSolve` ; les trois
  sites d'appel ont disparu avec `846381e` (2026-09-11, collapse `portfolio_v2`). `portfolio_v2`
  ne borne plus que par `PROJECT_TOP_K` (`projects.nut:819`, `:1521`, `:2083`, défaut **64**).
- `ROAD_MAX_ATTEMPTS_PER_YEAR` et `CASH_CANDIDATE_SCAN_LIMIT` n'ont jamais eu de lecteur sur
  l'historique disponible.

*Conséquence observable* : le commentaire de `globals_post.nut:3-7` décrit une borne de
continuation active (« une année sans argent examine au plus 20 candidats… l'ancien `break` en
examinait 1 ») et celui de `globals_post.nut:16-22` deux plafonds annuels routiers « à trancher au
banc ». Les trois décrivent un comportement qui n'existe pas. Le plafond annuel de lignes neuves
routières, en particulier, est passé de 36 à *aucun* au collapse `portfolio_v2` sans que ce soit
mesuré. **Effet réel à confirmer à l'étape 6** (`portfolio_max_batch = 1` borne peut-être de fait
par passe) ; le constat ici est que la borne annoncée n'est pas câblée.

### 01.6 — Cinq défauts actifs et vivants n'ont aucune trace documentaire        [gravité : P2 — volet B]

Recherche des 82 défauts actifs sur `docs/taches.md`, `docs/taches_archive_2026-09-09.md`, les 17
`docs/journal_*.md` et `docs/revue_code_2026-09-06_correctifs.md`. Cinq réglages actifs, dont le
maître est lui aussi actif, et dont la globale est consommée en production, ne sont mentionnés
**nulle part** dans `docs/` — seulement épinglés dans `sweeps/bench_v2.py` :

| Réglage | Défaut | Site de consommation | Maître |
|---|---:|---|---|
| `vivier_ratio_filter` | 1 | `candidates.nut:788` | — |
| `staged_bootstrap` | 1 | `main.nut:435`, `task_projects.nut:872`, `:935` | — |
| `feeder_hub_wait_max` | 100 | `task_feeders.nut:139` | `feeder_hub_check = 1` |
| `feeder_hub_min_days` | 60 | `task_feeders.nut:129` | `feeder_hub_check = 1` |
| `air_joined_stop_limit` | 2 | `builder_air.nut:1495` | `air_joined_stops = 1` |

*Conséquence observable* : aucun de ces cinq défauts ne peut être rattaché à un banc, officiel ou
non. `staged_bootstrap` et `vivier_ratio_filter` gouvernent respectivement l'étagement de la
génération au démarrage et un filtre de rejet de candidats — deux leviers de premier ordre sur le
vivier. Ils sont à instruire au volet B de la passe de correction comme des adoptions non
documentées, pas comme du code mort.

**Triage complet du volet B** (82 défauts actifs, classés par la signature du banc trouvée dans
une fenêtre de ±8 lignes autour de la mention la plus forte). Ce triage est un **indice de
provenance, pas un verdict** : il dit où chercher, il ne relit pas le protocole de chaque banc.

| Classe | N | Lecture |
|---|---:|---|
| « 20 graines » **et** p-value dans la fenêtre | 18 | provenance plausiblement officielle, à vérifier une par une |
| « 20 graines » sans p-value | 43 | le test des signes n'est pas lisible depuis la trace |
| p-value sans « 20 graines » | 0 | — |
| petit banc seulement (5/6/8/10/12 graines) | 4 | `unprofitable_streak_threshold`, `dynamic_cash_reserve`, `air_pax_revenue_calibration_pct`, `road_refleet` |
| mention sans aucune trace de banc | 9 | dont `feeder_mail_strict_orders` (01.3), `event_vehicle_autoreplaced` (01.4), `water_lakes_ops_budget`, `rail_devis`, `feeder_hub_check` |
| **aucune mention dans `docs/`** | 8 | les 5 de 01.6 + les 3 `air_early_slot_*`, inertes (voir plus bas) |

Le point saillant : **43 des 82** portent une trace de banc 20 graines dont la p-value n'apparaît
pas dans la trace, alors que le critère du projet est le test des signes *d'abord*. Épuiser les 82
au cas par cas est un travail d'archéologie documentaire qui déborde le quota d'une étape ; le
triage ci-dessus le rend faisable par lots à la passe de correction.

### 01.7 — `rail_min_distance` déclaré, actif en apparence, jamais lu        [gravité : P3]

`info.nut:2421` — défaut 25, `min 5 / max 40`. Aucune lecture nulle part.
`candidates.nut:18` le documente : « Le réglage `rail_min_distance` n'alimente plus le filtre. »
Le réglage reste exposé avec un défaut non nul, donc compté parmi les 82 « actifs ». Même piège de
mesure que 01.4, à moindre enjeu : un bras qui le déplace ne mesure rien.

### 01.8 — `road_cheap_trace` relu par `GetSetting` sur le chemin chaud, et le panneau affiche l'autre valeur        [gravité : P3]

`builder_road.nut:743` — `local cheapOn = ROAD_CHEAP_TRACE || (AIController.GetSetting("road_cheap_trace") != 0);`.
La globale est déjà chargée par `settings.nut:349`. Le défaut étant 0, `ROAD_CHEAP_TRACE` est
`false`, le `||` ne court-circuite pas et **un `GetSetting` est payé à chaque plan routier**, pour
une valeur toujours identique à la globale. Accessoirement, la sonde de `builder_road.nut:747-749`
journalise `flag=` + `ROAD_CHEAP_TRACE`, pas `cheapOn` : si les deux divergeaient un jour, le
panneau rapporterait la valeur qui n'a pas décidé. Même remarque pour `main.nut:471-472`, qui
imprime la globale *et* un second `GetSetting` brut.

### 01.9 — Le modèle de bassin routier est justifié avec une valeur qui n'est plus le défaut        [gravité : P3]

`candidates.nut:2232` (« un arrêt couvre physiquement au maximum ~20 maisons
(`ROAD_STOP_CATCHMENT_HOUSES = 20`) ») et `info.nut:2148-2150` (« `min(road_pax_catchment_pct,
(20 * 100) / houses)` … village de 35 maisons -> 57 % … agglomération de 250 maisons -> 8 % »).
Le défaut livré est **10** (`info.nut:2155`, `globals_pre.nut:23`), et la description de
`info.nut:2153` dit bien « default 10 ». Les deux exemples chiffrés valent donc en réalité 28 % et
4 % — moitié moins. Divergence de documentation sur la justification physique d'un réglage actif,
pas d'erreur de calcul.

### 01.10 — Deux replis de globale divergent de leur défaut déclaré        [gravité : P3]

- `globals_post.nut:60` : `ABANDON_COOLDOWN_DAYS <- 0` contre un défaut déclaré à **365**
  (`info.nut:1651`).
- `globals_pre.nut:377` : `AIR_FLEET_BUFFER <- -1` contre un défaut déclaré à **0**
  (`info.nut:1058`).

Les deux gardes de `settings.nut` (`if (acd >= 0)`, `if (afb >= -1)`) couvrent toute la plage
déclarée, donc l'affectation a toujours lieu et la divergence est aujourd'hui sans effet : le
constructeur ne lit ni l'une ni l'autre. C'est un repli latent, pas un bug actif — mais c'est
précisément le repli que verra tout code déplacé avant `OpexLoadSettings()`, et 365 → 0 signifie
« plus aucun refroidissement d'abandon ».

---

## Vérifié, n'est PAS un bug

- **Les 8 globales définies en double ou en triple.** Recomptées et confirmées :
  `CLEAN_DENSITY_SCORE` (`globals_pre:32` + `candidates:74` + `projects:38`), `TOP_K`
  (`candidates:26` + `globals_post:8`), `OPS_PER_TICK` (`globals_pre:325` + `budget:14`),
  `AIR_FULL_LOAD` (`globals_pre:379` + `builder_air:22`), `AIR_JOINED_STOPS` (`globals_pre:67` +
  `builder_air:29`), `FEEDER_PRICING` (`globals_pre:36` + `candidates:78`),
  `FEEDER_TOWN_COVERAGE` (`globals_pre:38` + `candidates:80`), `FEEDER_UNLOCK` (`globals_pre:34` +
  `candidates:76`). **Toutes portent la même valeur à chaque définition** (`true`/`true`/`true`,
  `20`/`20`, `10000`/`10000`, `false`/`false`…). L'ordre de chargement ne décide donc d'aucune
  valeur aujourd'hui, et `OpexLoadSettings()` les réécrit toutes ensuite. C'est un piège latent de
  maintenance, pas un défaut de comportement : ne pas le relitiger comme un bug.
- **Cohérence déclarative de `info.nut`** : 227 `AddSetting`, **0** nom en double, **0**
  `easy/medium/hard/custom_value` divergent (la convention « les quatre toujours égaux » tient
  partout), **0** défaut hors `[min_value, max_value]`, **0** réglage `AICONFIG_BOOLEAN` à défaut
  hors `{0,1}`, **0** réglage numérique sans bornes.
- **Aucun `GetSetting` sans `AddSetting`** : les 224 lectures de `settings.nut` correspondent
  toutes à un réglage déclaré.
- **Les 210 globales affectées par `OpexLoadSettings()` préexistent toutes** au premier niveau.
  `settings.nut` affecte avec `=` (et non `<-`) : une seule omission lèverait
  `the index '…' does not exist` au premier tick. Vérifié exhaustivement, aucune manquante.
- **`pathfinder_sleep_ticks` lu hors de `settings.nut`** (`builder_rail.nut:385`, `:678`) : c'est
  une lecture **par tranche d'A***, pas par itération, et elle est documentée en place
  (`builder_rail.nut:381-384`, `info.nut:11`, `:2728`). Défaut 0. Coût négligeable, exception
  assumée à la convention.
- **`air_early_slot_target_towns = 6`, `air_early_slot_min_pop = 1000`,
  `air_early_slot_bonus_pct = 50`** (ajoutés par `c74a123` le 2026-09-15) : comptés « actifs » par
  leur valeur, mais **inertes** derrière `air_early_slot = 0` (`info.nut:2518`). Ne pas les
  signaler comme adoptés sans banc — ils ne sont pas adoptés du tout.
- **`AIR_CADENCE_CAP_ADAPTIVE` n'est consommée que dans `settings.nut:312-321`** : c'est son rôle
  (elle désactive `AIR_CADENCE_CAP` sous 50 industries). Défaut 0, banquée et non adoptable
  (fiche C64). Pas de code mort.
- **Le constructeur `OpexAI` ne lit aucune globale adossée à un réglage** : il tourne avant
  `OpexLoadSettings()` (`main.nut:433`), et ses seuls appels externes — `OpexBudget()`,
  `OpexCatalog()`, `OpexAirResetSiteCache()` — ne consultent que `AIR_SITE_CACHE`, une table.
  L'échange de file `FLEET_BEFORE_NEW` est bien reporté dans `Start()`, comme son commentaire
  l'annonce (`main.nut:437-438`).
- **`TENSION_DECISION_FRICTION`** : globale initialisée à `0.05`, réglage
  `decision_friction_permille` à 50 → `50/1000 = 0,05`. Cohérent, pas une divergence.

## Hors périmètre, à relire ailleurs

- **Étape 6 (`projects.nut`)** — effet réel de 01.5 : `portfolio_v2` n'a plus de plafond annuel de
  lignes neuves depuis `846381e` ; vérifier si `portfolio_max_batch = 1` en tient lieu de fait, et
  ce que `PROJECT_TOP_K = 64` borne réellement dans `OpexProjectSelectAffordable`.
- **Étape 7 / 13 (`builder_rail.nut`, `task_rail.nut`)** — 01.1 : le seuil d'approche manquant vit
  dans `task_rail.nut` ; c'est aussi là que se juge G5 (`rail_expand` sous `fleet_fix`).
- **Étape 12 (`events.nut`)** — 01.4 est **tranché** : le réglage n'est pas câblé, par décision
  documentée. Ne reste à l'étape 12 que le comptage `33/33 untracked` sur 16 ans.
- **Étape 14 (`task_feeders.nut`)** — 01.3 et 01.6 : sémantique d'ordres des feeders courrier, et
  `feeder_hub_wait_max` / `feeder_hub_min_days` sans banc.
- **Étape 18 (`bench_v2.py`)** — 01.3 et le triage de 01.6 : `bench_v2.py` est le seul endroit où
  les cinq réglages non documentés apparaissent. C'est là que se vérifie l'épinglage explicite de
  **tous** les réglages dans chaque bras, bras de contrôle compris (G0).
- **Étape 5 (`candidates.nut`)** — 01.2 : `OpexTownBusCatchment` (`candidates.nut:2237-2247`) et
  le plancher `pct < 1`, à relire sur le fond du modèle de bassin.
