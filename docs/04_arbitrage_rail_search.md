# C41.46–C41.49 — Le canal rail : arbitrage, et le gel qui le précède

**Contrat écrit avant code, 2026-09-09.** Prépare le point 2 de l'orchestrateur C41 : sortir la
recherche A\* rail du régime « hors-file » et lui donner une borne décidée, au lieu d'une borne
subie. Source de mesure unique : `results/diag_1v1_shared_timeline_2y_seed42.json` (graine 42,
2 ans, partie partagée avec AAAHogEx, 2 859 événements, `-d script=4`).

⚠️ Aucun code n'est écrit dans ce document. Chaque tranche ci-dessous porte son réglage à `0`,
sa mesure et son critère de passage à la suivante, selon le patron C41 habituel.

---

## 1. Ce que la mesure dit, et ce qu'elle ne dit pas

### 1.1 Répartition des opcodes (ledger `C41_SLACK_LEDGER` du 1971-01-11)

| catégorie de passe | opcodes | part | `ran`/`calls` |
|---|---:|---:|---:|
| **`rail_search`** (une recherche en vol) | **48 859 278** | **79,7 %** | 267 / 531 |
| `town_growth` | 5 270 109 | 8,6 % | 37 / 37 |
| `catalog` | 3 626 479 | 5,9 % | 3 / 37 |
| `projects` | 2 345 712 | 3,8 % | 3 / 37 |
| `expand` | 378 474 | 0,6 % | 37 / 37 |
| `report` | 297 007 | 0,5 % | 1 / 37 |
| `refleet` | 283 774 | 0,5 % | 37 / 37 |
| `air_fleet` | 163 261 | 0,3 % | **0 / 37** |
| `repay` / `scrap` / `air` / `feeders` | 69 628 | 0,1 % | |
| **total** | **61 293 722** | | **866 passes** |

⚠️ **Ces 79,7 % ne sont pas la part nette de l'A\*.** `_runNextTaskWithSlackLedger` étiquette la
passe entière `rail_search` dès que `_railSearch != null`, or `main.nut:6020` avance une tranche
**puis exécute une tâche de file dans la même passe**. Le ledger agrège donc les deux.

**Corroboration indépendante, 5 graines** (`c41_monthly_busy_ledger`, duel partagé 5 × 3 ans,
`results/diag_1v1_shared_month_busy_3y_5seeds.json`, `docs/taches.md` fiche C41) : sur les mois
« ≥300 k£ en caisse et aucune construction », `rail_search` = **70,6 %** des opcodes, `catalog`
15,0 %, `town_growth` 14,0 %. Même ordre de grandeur, même conflation à lever — et la graine 42
n'est donc pas une singularité.

### 1.1bis ✅ C41.46 mesuré (2026-09-09) — la part nette est BIEN PLUS BASSE que la borne estimée

`c41_rail_slice_ledger=1`, solo (pas de duel), 5 graines × 6 ans,
`results/diag_c41_46_rail_slice_ledger_6y_5seeds.json`, 0 échec. Encadre isolément le seul appel
`_continueRailSearch()` (seulement quand `phase == "search"`, donc jamais les passes `"build"` à
coût nul ou `_consumeRailUpgrade`) et déduit les opcodes de la tâche de file par différence avec
la mesure totale de la passe (`OpexOpsMeasureBegin/End` imbriqués sans état partagé, vérifié dans
`budget.nut`).

| année | tranches | net A\* | tâche même passe | **part nette** |
|---|---:|---:|---:|---:|
| 1971 | 398 | 62,25 M | 76,03 M | 45,0 % |
| 1972 | 368 | 50,35 M | 101,00 M | 33,3 % |
| 1973 | 374 | 56,77 M | 199,29 M | 22,2 % |
| 1974 | 286 | 43,32 M | 196,59 M | 18,1 % |
| 1975 | 284 | 37,85 M | 250,66 M | 13,1 % |
| **cumul 5 graines** | **1 710** | **250,5 M** | **823,6 M** | **23,3 %** |

**La borne basse que j'avais estimée à vue (~59 %, sur l'hypothèse ~2 700 opcodes/itération) était
fausse dans le mauvais sens : la part nette réelle est PLUS BASSE, pas plus haute, et elle
S'EFFONDRE avec la maturité de la partie** (45,0 % → 13,1 % en 5 ans). L'hypothèse « `rail_search`
= 79,7 % des opcodes » de §1.1 attribuait donc à l'A\* rail un coût qui est, aux trois quarts et de
plus en plus, celui de la tâche de file qui se trouve exécutée dans la même passe — très
probablement `catalog`/`projects`, dont le coût par reconstruction (C41.22 : 2,09 M
opcodes/reconstruction) suffit à expliquer la croissance observée, mais **ce ledger ne le prouve
pas** : c'est un accumulateur unique, pas ventilé par tâche coïncidente (choix de conception
assumé — un seul canal de recherche rail existe à la fois, rien à ventiler côté A\*, mais la tâche
de file, elle, aurait pu être capturée par nom pour trancher ce point).

🔑 **Conséquence directe pour C41.49** : un test de domination qui coupe l'A\* pour économiser des
opcodes économiserait, à l'échelle de la partie, moins d'un quart de ce que la seule lecture du
ledger C41.11 laissait penser — et cette part continue de baisser. **Le gisement d'opcodes n'est
pas la recherche rail : c'est la tâche qui tourne à côté.** Ça ne dispense pas de traiter le gel
trésorerie (C41.47, §1.3, mesuré indépendamment sur une chronologie distincte et non affecté par
ce résultat), mais ça déplace fortement la priorité relative : C41.49 devient un candidat plus
faible qu'il ne semblait, et **la vraie question à instruire avant lui est laquelle des tâches de
file (`catalog` ? `projects` ?) gonfle `task_ops`, et si son propre coût est justifié — un sujet
C39, pas C41.**

⚠️ **Ne pas comparer directement `net_share` (23,3 % ici) aux 79,7 %/70,6 % de §1.1** : ce
diagnostic tourne **en solo** (pas de duel partagé avec AAAHogEx), sur une carte 8×8 qui a eu 5 ans
de plus pour mûrir que la fenêtre à 2 ans des mesures précédentes — la tendance (part nette qui
s'effondre avec l'âge de la partie) est le résultat robuste, la valeur absolue à 2 ans ne l'est pas
forcément autant.

### 1.2 Le rendement du canal rail sur 2 ans

- **1** projet rail élu sur 15 `PROJECT_CHOSEN` (7 air, 7 route, 1 rail).
- **1** `RAIL_BUILD` (ligne 18, COAL, 9815→13978), **1** `RAIL_EXPAND` (double voie, 1971-04-16).
- **2** `RAIL_SEARCH` menées à terme en 2 ans (`outcome=OK`, 3 274 et 2 581 itérations).
- **20** panneaux `RA|` d'échec rail, **tous** en `TRACEX`.

### 1.3 🔑 Le vrai coût : la chronologie de l'unique ligne rail

| date | événement |
|---|---|
| 1970-01-13 | `PROJECT_CHOSEN rank=0 mode=rail cargo=COAL src=9815 dst=13978 roi=1053` |
| 1970-01-25 | `PROJECT_DISCARD rank=0 mode=rail src=9815 dst=13978 reason=search_in_progress` |
| 1970-05-16 | `RAIL_SEARCH type=resumable outcome=OK iters=3274 budget=7000` |
| 1970-10-24 | `RAIL_BUILD line=18 … cost=48845 trains=1 wagons=3` |

**Le meilleur projet du portefeuille (ROI 1 053) a mis 9 mois et 11 jours à devenir une ligne :
4 mois de recherche, puis 5 mois d'attente.** Les 5 mois ne sont pas de l'A\* — c'est
`_consumeRailSearch` qui rend `"cash"` (`main.nut`, garde `money < need`) sans libérer l'état :

```squirrel
if (money < need) return "cash";        // _railSearch reste non nul, phase = "build"
```

L'intention est bonne (« ne pas jeter le plan sur CASH : on réessaiera sans refaire l'A\* »), mais
tant que `_railSearch` est non nul :

- `_expandRailLines` sort immédiatement (`main.nut:4417`, *« ne pas en empiler une seconde »*) —
  **aucune croissance rail possible** ;
- aucune autre recherche rail ne peut démarrer — **le canal rail entier est gelé** ;
- le plan vieillit sur une carte vivante pendant des mois.

Le cas symétrique — un plan **en échec** bloquant indéfiniment la phase build — a déjà été
identifié et corrigé (garde `planFailed`, G3§1). **Le cas trésorerie a exactement la même forme et
n'est pas couvert.**

### 1.4 Ce que ça change pour l'orchestrateur

Le point 2 tel que formulé (« continuer `rail_search` seulement s'il domine les projets prêts »)
n'attaque que le premier des deux gels — et pas le plus long. Sur cette graine, l'arbitrage aurait
pu récupérer au mieux 4 mois ; la libération de l'état sur `cash` en récupère 5, sans aucun test de
domination, sans dénominateur commun, sans rejouer C35. **L'ordre des tranches en découle.**

---

## 2. Le socle déjà en place (ne rien réinventer)

| brique | état | ce qu'elle donne |
|---|---|---|
| `rail_search_resumable` | **défaut 1, adopté** (`info.nut:1167`) | la recherche rend déjà la main par tranches |
| `rail_micro_deadline` (C20) | **défaut 1, adopté** | échéance **par tranche**, pas globale — la cause des rejets −23,1 % / −13,3 % est soignée |
| `rail_segmented_search` (A5) | défaut 1 | **frontières de segment explicites** : `state.segments++`, `state.prefix` accumulé, `OpexSegmentedResult(…, "CONT", false)` |
| `RAIL_SEARCH_SLICE = 50` | `builder_rail.nut:39` | la granularité de reprise existe |
| `state.spent` | cumul de toutes les tranches | **le dénominateur d'un test marginal est déjà calculé** |
| `plan.iterationBudget` | 7 000–10 000 observés | la borne actuelle, subie et non décidée |

Un arbitrage n'a donc **rien à construire** : il a un point de reprise, une frontière naturelle, un
compteur d'itérations dépensées et une échéance locale. Il lui manque uniquement de quoi comparer.

---

## 3. Les tranches

### ✅ C41.46 — Séparer la tranche A\* de la tâche de file dans la même passe *(passif, fait 2026-09-09)*

`c41_rail_slice_ledger=0` (`1` au diagnostic). Encadre le seul appel `_continueRailSearch()` par
`OpexOpsMeasureBegin/End`, uniquement quand `phase == "search"` (jamais les passes `"build"` à
coût nul ni `_consumeRailUpgrade`), et journalise par an : tranches avancées, opcodes **nets** de
l'A\*, opcodes de la tâche de file dans la même passe (par différence avec la mesure totale de
`_runNextTaskWithSlackLedger`), itérations cumulées, et tranches n'ayant pas atteint `slice.done`.

**Résultat (5 graines × 6 ans, §1.1bis) : part nette 45,0 % en 1971 → 13,1 % en 1975, cumul
23,3 %, `done_rate` 1,5 %.** La part nette de l'A\* est plus basse que toute borne envisagée ici et
s'effondre avec la maturité de la partie ; le gisement d'opcodes présumé de C41.49 est donc plus
faible qu'estimé, et la vraie question est ce qui gonfle `task_ops` — pas encore ventilé par tâche
dans ce ledger (accumulateur unique par conception).
🐛 Piège trouvé au premier smoke test : la première version journalisait via `OpexC41SchedulerLog`,
gatée sur `C41_SLACK_LEDGER/OPPORTUNITY/ADMISSION` — `c41_rail_slice_ledger=1` seul n'émettait
donc RIEN. Corrigé par un gate dédié (`OpexC41RailSliceLog`), comme les sondes rail-lost.

### ✅ C41.47 — Libérer l'état rail quand le blocage est la trésorerie *(ADOPTÉ, banc officiel 20×10, 2026-09-09)*

`c41_rail_cash_release=0`. À `1`, `_consumeRailSearch()` libère `_railSearch` **dès le premier
blocage trésorerie constaté** — précheck (`money < need`) ou échec `CASH` à l'exécution du plan —
au lieu de le garder indéfiniment. `candidate.railPlan` **n'est pas effacé**.

**Décisions tranchées à l'implémentation** (les deux points laissés ouverts par le contrat) :
- **`N = 0` (libération immédiate)**, symétrique de `planFailed` (G3§1) qui ne temporise pas non
  plus — dès qu'un blocage cash est établi comme la seule cause, il n'y a rien à gagner à attendre.
- **Aucune revalidation supplémentaire à ajouter, parce qu'il n'y en a pas aujourd'hui non plus.**
  `OpexBuildLine` réutilise déjà `candidate.railPlan` **sans replanification** dès qu'il est
  présent (`builder_rail.nut:1918`) — c'est le chemin emprunté à CHAQUE nouvelle tentative tant
  que `_railSearch` reste bloqué sur cash, avec ou sans ce correctif. Le risque « carte périmée »
  est donc préexistant et inchangé par ce correctif ; il n'est pas dans son périmètre.

**Effet secondaire vérifié en lisant le code (pas seulement le candidat bloqué)** :
`_tryBuildRailProject` rejette **tout autre candidat rail** avec `reason=search_in_progress` tant
que `this._railSearch != null` (`main.nut:2574`), et `_expandRailLines` sort immédiatement dans le
même cas (`main.nut:4445`). Le gel touche donc tout le canal rail, pas seulement la ligne élue —
confirmé en observant `cash_releases=1` avec un `delay` bien plus court côté `treatment` au smoke
test 2 ans (`2` jours contre `155`/`3` côté `control`, une seule graine, non concluant seul).

🐛 Piège identique à C41.46, évité d'emblée : `OpexC41RailCashReleaseLog` a son propre gate dédié
(`C41_RAIL_CASH_RELEASE`), pas `OpexC41SchedulerLog`.

*Mesure* : diagnostic 5×6 apparié control/treatment sur le délai élection→construction rail et le
nombre de `RAIL_EXPAND` (`sweeps/diag_c41_47_rail_cash_release.py`,
`results/diag_c41_47_rail_cash_release_6y_5seeds.json`), puis **banc officiel 20×10** (ce
correctif change l'entrelacement, donc les décisions).

#### ⚠️ Diagnostic mesuré (2026-09-09) — NUL, pas le gain espéré. Ne pas conclure à ce stade.

0 échec, 5 graines × 6 ans, appariées control/treatment. `cash_releases` ne se déclenche que sur
**3 graines sur 5** — c'est un motif rare (≈0,6 déclenchement/graine sur 6 ans), cohérent avec
l'unique cas observé dans la chronologie de départ.

| graine | builds (C/T) | expands (C/T) | releases (T) | délai moyen jours (C/T) |
|---:|---:|---:|---:|---:|
| 7 | 3/3 | 1/1 | 0 | 443,0 / 443,0 (identiques : jamais de release) |
| 42 | 3/3 | 2/1 | 1 | **73,0 / 295,7** |
| 100 | 3/2 | 1/0 | 1 | 383,7 / **413,5** |
| 999 | 1/1 | 0/0 | 0 | 182,0 / 182,0 (identiques) |
| 12345 | 4/5 | 2/2 | 1 | 117,0 / **92,2** |
| **total** | **14/14** | **6/4** | 3 | — |

**Total de lignes rail construites strictement identique (14/14).** Sur les 3 graines où le
correctif s'est réellement déclenché, le délai moyen est **pire deux fois sur trois** (42 : +305 %,
100 : +8 %) et **meilleur une fois** (12345 : −21 %, avec un cinquième train construit en plus).
`RAIL_EXPAND` recule (6 → 4), sans qu'on sache si c'est un effet réel ou le bruit d'une
réordonnance qui décale tout le reste de la partie. **N'est pas un gain net mesuré : c'est un
résultat mixte, sans signal directionnel net, avec un signe défavorable sur le délai (2 pertes
contre 1 gain) et sur `RAIL_EXPAND`.**

⚠️ **Interprétation, pas verdict.** Deux graines sur cinq ne divergent JAMAIS (`releases=0`,
sorties byte-identiques) : l'échantillon utile est en réalité de 3 graines, bien en dessous du
plancher de détection habituel ([[banc_monograine_insuffisant]]). Toute divergence de
comportement — même corrective — recompose la trajectoire RNG en aval (butterfly effect classique
de ce projet), donc un délai « pire » sur une graine ne prouve pas que le mécanisme est mauvais :
il peut simplement avoir fait construire une AUTRE ligne d'abord, décalant tout le reste. **Ce
diagnostic ne tranche rien dans un sens ou dans l'autre — il confirme seulement que le code
fonctionne (le mécanisme se déclenche, aucun crash, aucune régression de volume total) et qu'il
faut le banc officiel 20×10 pour lire un signal, exactement comme le contrat l'annonçait.**

#### ✅ Banc officiel 20×10 (2026-09-09) — ADOPTÉ. Le diagnostic 5×6 était sous-puissant, pas faux.

`results/bench_c41_47_rail_cash_release_10y_20seeds.json`, 20 graines × 10 ans, apparié, 0 échec.
Contrairement au diagnostic 5×6 (14/14 constructions identiques, délai mixte), le test des signes
sur les 5 métriques de succès est **cohérent et significatif dans le même sens sur toutes** :

| métrique | victoires du correctif | p (test des signes) | t (différence moyenne) |
|---|---:|---:|---:|
| `profit` | **19/20** | **p<0,0001** | −1,46 |
| `profit_year` | **19/20** | **p<0,0001** | −0,94 |
| `company_value` | 16/20 | p=0,012 | −0,68 |
| `performance_history` | 16/20 | p=0,012 | 0,80 |
| `median_station_rating` | 15/20 | p=0,041 | 0,95 |

**Aucun |t| ne dépasse 1,5** — la différence moyenne est noyée dans le bruit inter-graines — mais
le **test des signes est net sur toutes les métriques**, exactement le motif que
[[banc_monograine_insuffisant]] décrit : *« une moyenne peut être tirée par 2-3 graines
divergentes alors que le compte de victoires est proche du hasard »* — sauf qu'ici c'est
l'inverse, le compte de victoires est **loin** du hasard (p<0,0001 pour profit) pendant que la
moyenne reste bruitée. Seuil identique à celui qui avait fait adopter le mode route (16/20,
p=0,012, [[opexai_mode_route]]).

**Pourquoi le diagnostic 5×6 avait raté ça** : 2 graines sur 5 n'ont jamais divergé du tout
(`cash_releases=0`), laissant un échantillon utile de 3 — bien en dessous de tout seuil de
détection. Le banc à 20 graines a le pouvoir statistique que le diagnostic n'avait pas ; ce n'est
pas une contradiction, c'est exactement pourquoi le contrat exigeait le banc avant de conclure.

**Adopté par défaut** (`easy/medium/hard/custom_value = 1` dans `info.nut`, `C41_RAIL_CASH_RELEASE
<- true` dans `main.nut`).

### ✅ C41.48 — Sonde de comparaison à la frontière de segment *(passif, codé et mesuré 2026-09-09)*

`c41_rail_domination_probe=0`. À chaque frontière de tranche segmentée (`slice.done == false`,
la seule valeur produite par `OpexSegmentedResult(…, "CONT", false)`), journalise sans rien
couper : itérations dépensées (`state.spent`), budget restant, segments franchis, longueur du
préfixe, distance Manhattan restante jusqu'au but, profit annuel prévu et capital du candidat rail,
et **le meilleur projet finançable prêt à bâtir au même instant** — scan de `this._projects.best`
dans l'ordre de rang, premier dont `capital ≤ OpexAvailableCapital()` (même formule centralisée que
`_consumeRailSearch`/`_tryBuildProjects`), donc *réellement* finançable, pas seulement le mieux
classé. Uniquement `kind == "primary"` (une recherche d'upgrade n'a ni candidat ni profit/capital
au même sens).

#### Résultat mesuré — **à l'opposé de C41.14, il y a bien matière à arbitrer**

5 graines × 6 ans, `results/diag_c41_48_rail_domination_probe_6y_5seeds.json`, 0 échec :

| graine | frontières | avec alternative financable | dont *autre* projet (pas le candidat lui-même) |
|---:|---:|---:|---:|
| 7 | 221 | 193 (87,3 %) | 159 |
| 42 | 270 | 219 (81,1 %) | 159 |
| 100 | 320 | 209 (65,3 %) | 151 |
| 999 | 290 | 283 (97,6 %) | 250 |
| 12345 | 410 | 301 (73,4 %) | 254 |
| **total** | **1 511** | **1 205 (79,8 %)** | **973 (64,4 % du total, 80,7 % des "avec alt")** |

**973 frontières sur 30 graines-années (~32/graine-année) où une AUTRE ligne financée et prête à
bâtir existe pendant que l'A\* rail continue.** Ce n'est pas le motif de C41.14 (0 admission sur
56 fenêtres) : là où C41.14 cherchait un reliquat d'opcodes à admettre pour une micro-tâche de
rafraîchissement, ici la question porte sur un **arbitrage de capital et de temps de construction**,
et le matériau existe en abondance. `rail_profit` moyen (26 k–45 k£/an selon la graine) et
`best_cost` moyen (50 k–56 k£) sont du même ordre de grandeur que le candidat rail lui-même
(`rail_capital` 48 k–53 k£) — les alternatives ne sont pas des miettes.

⚠️ **Nuance qui pèse sur la suite** : croisé avec C41.46, le gisement d'opcodes visé par C41.49 est
modeste et décroissant (23,3 % cumulé, en baisse). **La fréquence élevée ici ne dit donc pas
« C41.49 économiserait beaucoup d'opcodes »** — elle dit « il y a souvent un choix réel à faire ».
Si C41.49 vaut la peine, c'est probablement pour une raison différente de celle du contrat
d'origine : **rediriger du capital vers un projet prêt plus tôt** (effet sur le volume construit,
la métrique n°1 du projet), pas économiser du calcul. À trancher explicitement avant d'écrire
C41.49 — la règle proposée plus bas visait l'arrêt optimal en opcodes ; sa justification a changé.

### C41.49 (reformulé 2026-09-10) — Le porte-à-faux n'est peut-être pas l'A\*, c'est de savoir si l'alternative saisit déjà sa chance

⚠️ **La règle d'arrêt optimal en opcodes ci-dessous est abandonnée, pas seulement affaiblie.**
Elle supposait implicitement que rien d'autre ne peut se construire tant que l'A\* rail tourne.
Relire `_tryBuildProjects`/`_runNextTask` (main.nut) montre que ce n'est **pas** ce que fait le
code par défaut — et que la vraie inconnue est ailleurs.

#### Ce que la lecture du scheduler montre (2026-09-10, aucune mesure encore)

1. **Le canal non-rail n'est pas gelé par défaut.** Sous `portfolio_dynamic_batch=0` (défaut,
   `main.nut:963`), quand `_tryBuildRailProject` rejette le rang courant en
   `reason=search_in_progress` (`main.nut:2605-2608`), la boucle de `_tryBuildProjects`
   **continue aux rangs suivants dans la même passe** (`main.nut:3381-3400`, aucun `break` sur
   `rejected` hors `PORTFOLIO_DYNAMIC_BATCH`) — un candidat air/route/eau finançable peut donc déjà
   être bâti PENDANT une recherche rail. Le blocage total avant le premier build (`return true` à
   `main.nut:3278-3288`) n'existe que sous `portfolio_dynamic_batch=1`, qui n'est pas le défaut.
   **La phrase de C41.47 « le gel touche tout le canal rail, pas seulement la ligne élue » ne
   parlait que du canal RAIL** (aucun autre candidat rail ne peut être tenté) — elle a été lue à
   tort comme couvrant aussi air/route/eau.
2. **Ce que fait `projects` pendant une recherche rail est invisible dans TOUS les ledgers
   existants.** `_runNextTaskWithSlackLedger` étiquette `continuationCategory = "rail_search"`
   dès que `this._railSearch != null`, **avant même de savoir quelle tâche `_runNextTask` va
   dispatcher** (`main.nut:5973-5983`) — donc chaque passe pendant une recherche rail est comptée
   `rail_search`, même si c'est en réalité `projects` (ou `catalog`, `town_growth`…) qui a tourné
   dans cette passe. C'est pour ça que `catalog`/`projects` apparaissent « 3/37 » sur 2 ans
   (§1.1) : ce sont 3 occurrences **hors** fenêtre de recherche rail, pas 3 occurrences au total.
   Ce que `projects` fait à l'intérieur de la fenêtre n'a jamais été compté.
3. **La file est un round-robin strict** (`main.nut:1298-1331`) : 11 tâches actives par défaut
   (`catalog`, `report`, `scrap`, `air`, `air_fleet`, `feeders`, `projects`, `expand`, `refleet`,
   `town_growth`, `repay`), chacune due chaque cycle. `projects` devrait donc obtenir ~1 passe sur
   11, y compris pendant une recherche rail — ce n'est a priori pas un cas rare, mais ce n'est pas
   mesuré non plus.
4. **`_portfolioInvalidated` n'est probablement pas le bon suspect.** Le drapeau fait abstenir
   `projects` (`return false`, `main.nut:6794`), mais les trois chemins qui le posent
   (`ET_INDUSTRY_OPEN`, `ET_TOWN_FOUNDED`, `ET_ENGINE_AVAILABLE` sous `C39_ENGINE_REFRESH` —
   `main.nut:5865/5899/5936`) forcent **dans le même geste** `catalog.dueCycle = 0` et
   `projects.dueCycle = 0` (`main.nut:5868/5902/5939`) : `catalog` est donc due à son tour
   immédiatement suivant, se rafraîchit et lève le drapeau. La fenêtre d'abstention est courte
   (un tour de file, pas des mois) — à confirmer, mais ce n'est pas la piste prioritaire.

#### Conséquence : la question à trancher n'est plus une règle de décision, c'est une mesure

On ne sait pas, sur les 973 frontières « avec alternative finançable » de C41.48, si c'est :

  **(a)** déjà saisi — `projects` tourne dans la même fenêtre et construit l'alternative, juste
  après le point de mesure de C41.48 (qui ne regarde que l'instant de la frontière, pas ce qui
  suit) → **C41.49 est un non-sujet, fermer la fiche** ;
  **(b)** tenté mais refusé pour une autre raison (trésorerie, `too_close`, vivier déjà épuisé
  à ce rang) → le correctif porte sur **cette raison précise**, pas sur l'A\* rail ;
  **(c)** jamais tenté dans la fenêtre utile — `projects` n'a pas eu son tour, ou son vivier
  (`this._projects.best`) était périmé/vide à ce moment → le correctif est une question de
  **cadence/fraîcheur de `projects` pendant un `_railSearch` actif**, un sujet C39, pas un arrêt
  optimal C41.

Coder une règle de domination sur l'A\* avant de savoir laquelle domine reviendrait à traiter un
problème qui n'existe peut-être pas (a), ou à traiter le mauvais mécanisme (b, c).

#### ✅ Étape 0 — codée, mesurée en 5×6 (2026-09-10), (c) domine : C41.49 fermé en tant que règle sur l'A\*

Réglage `c41_projects_fallthrough_probe=0` (`ai/OpexAI/info.nut`/`main.nut`), gate dédié
(`OpexC41ProjectsFallthroughLog`, pas `OpexC41SchedulerLog` ni `OpexC41RailDominationLog`).
Dans `OpexAI::_tryBuildProjects`, uniquement quand `this._railSearch != null &&
this._railSearch.kind == "primary" && this._railSearch.phase == "search"` (même garde que
C41.48) : à l'entrée, `_portfolioInvalidated` et `this._projects.best.len()` ; après la boucle,
combien de candidats **non-rail** ont été tentés et combien ont été **bâtis**.

⚠️ **Angle mort trouvé après coup, sans conséquence sur la mesure ci-dessous** : le champ
`_portfolioInvalidated` loggé à l'entrée de `_tryBuildProjects` est mort — le site d'appel
(`main.nut:6791-6796`, tâche `"projects"`) fait `if (this._portfolioInvalidated) return false;`
**avant** d'appeler `_tryBuildProjects`, donc la sonde ne peut jamais observer `invalidated=1`.
Ça n'affecte pas le comptage attempted/built ni la classification (a)/(b)/(c) (qui ne dépendent
que de la présence/absence des logs entry/exit, pas de ce champ), mais une future mesure de
cadence `projects` devra lire `_portfolioInvalidated` **au site d'appel**, pas dans la fonction.

**Mesure** : diagnostic 5×6, les deux sondes combinées sur la même arm
(`OpexAI[c41_rail_domination_probe=1,c41_projects_fallthrough_probe=1]`,
`sweeps/diag_c41_49_projects_fallthrough_probe.py`,
`results/diag_c41_49_projects_fallthrough_probe_6y_5seeds.json`, 0 échec). Corrélation
frontière par frontière : comme `_continueRailSearch()` (qui loggue la frontière) s'exécute
toujours AVANT le dispatch de tâche dans la même passe de `_runNextTask`, au plus une paire
entry/exit du fallthrough peut s'intercaler avant la frontière suivante, et elle appartient de
droit à CETTE passe — la corrélation est donc exacte, pas une fenêtre approximative.

| graine | frontières avec alt | (a) captée+bâtie | (b) tentée-refusée | (c) jamais tentée cette passe |
|---:|---:|---:|---:|---:|
| 100 | 360 | 34 (9,4 %) | 1 (0,3 %) | 325 (90,3 %) |
| 12345 | 301 | 35 (11,6 %) | 1 (0,3 %) | 265 (88,0 %) |
| 42 | 242 | 26 (10,7 %) | 1 (0,4 %) | 215 (88,8 %) |
| 7 | 193 | 20 (10,4 %) | 1 (0,5 %) | 172 (89,1 %) |
| 999 | 283 | 28 (9,9 %) | 1 (0,4 %) | 254 (89,8 %) |
| **cumul** | **1 379** | **143 (10,4 %)** | **5 (0,4 %)** | **1 231 (89,3 %)** |

(le total de frontières avec alternative — 1 379 ici contre 973 en solo C41.48 — bouge parce que
la sonde combinée change le budget d'opcodes de chaque passe, donc la trajectoire : effet déjà
documenté, [[banc_monograine_insuffisant]] et §1.1bis, pas une contradiction.)

**(c) domine sur les 5 graines** (88,0 %–90,3 %), largement au-dessus du seuil de passage du
contrat (4/5). **Conséquence directe** : (b) est quasiment nul (0,3–0,5 %, une seule occurrence
par graine) — la trésorerie ou `too_close` ne sont PAS le facteur limitant. Une règle de
domination sur l'A\* rail (la forme C41.49 d'origine, ou même sa version reformulée en délai de
construction) réglerait un non-problème : le canal ne refuse quasiment jamais l'alternative une
fois qu'il l'essaie, il ne l'essaie simplement pas assez souvent — `projects` n'est due à son
tour de round-robin que dans ~10 % des passes qui coïncident avec une frontière utile,
exactement l'ordre de grandeur attendu d'une file à 11 tâches actives par défaut (§0 point 3).

**🔒 C41.49 est fermé en tant qu'arbitrage sur la recherche rail.** Aucune règle de décision
n'a été écrite, et il n'y a plus lieu d'en écrire une sous cette forme. Le levier réel est la
**cadence de dispatch de `projects` pendant une recherche rail active** — un sujet de
fraîcheur/ordonnancement, donc **C39**, à cadrer dans une fiche séparée avant tout diagnostic ou
banc : métrique = délai de construction de l'alternative captée en retard (jamais un prix
d'ombre en opcodes, ⛔ C35 déjà réfuté). Aucun banc officiel n'a été lancé sur ce contrat — il
n'y avait rien à bancher, seulement cette mesure de cadrage.

---

## 4. Ce que ce contrat ne fait pas

- **Il ne réordonne pas `_taskQueue`.** La recherche est reprise en tête de `_runNextTask`, avant
  que la file soit consultée : aucun rang ne l'atteint. Le point 1 de l'orchestrateur
  (`town_growth` qui prend le tour sans rien accomplir, 442 échecs sur 453) est **orthogonal** et
  se traite dans la file.
- **Il ne corrige pas `TRACEX`.** Les 20 panneaux `RA|` d'échec rail sont tous en `TRACEX`, comme
  les 442 échecs de `town_growth` — un motif partagé, à instruire séparément.
- **Il ne touche pas à l'offre du vivier.** Le dernier vivier de la partie (1971-12-15) donne
  `considered=260 selected=0 rejected=260` avec 52 952 £ en caisse : à CET instant précis,
  l'abstention de `projects` est un problème d'offre, pas d'ordonnancement.
  ⚠️ **« 3 tours utiles sur 37 » ne veut pas dire que `projects` tourne 3 fois en 2 ans** — voir
  la reformulation C41.49 : le ledger étiquette `rail_search` toute passe où `_railSearch != null`,
  quelle que soit la tâche réellement dispatchée dans cette passe, donc ce que `projects` fait
  PENDANT une recherche rail (l'essentiel des 2 ans) n'a jamais été compté par ce chiffre.

## 5. Critère de clôture

✅ C41.46 livré et lu (§1.1bis) ; ✅ C41.48 livré et lu (§C41.48, 973 frontières avec alternative
sur 30 graines-années) ; ✅ **C41.47 ADOPTÉ** (diagnostic 5×6 sous-puissant et NUL, mais banc
officiel 20×10 net sur les 5 métriques — profit/profit_year 19/20, p<0,0001) ; ✅ **C41.49
FERMÉ le 2026-09-10, sans règle de décision écrite.** Étape 0 codée (`c41_projects_fallthrough_probe`)
et mesurée en 5×6, corrélée à C41.48 : sur 1 379 frontières « avec alternative finançable »,
**(c) jamais tentée sur cette passe précise domine à 88,0–90,3 % sur les 5 graines** (contre
10,4 % captée+bâtie, 0,4 % tentée-et-refusée) — la cadence de dispatch de `projects`
(round-robin ~1/11 tâches), pas un défaut de comparaison sur l'A\*. Aucun banc officiel : le
contrat l'excluait avant cette étape, et il n'y a maintenant rien à bancher sous cette forme.
⚠️ Le volume reste la métrique n°1 (~85 % de l'écart avec AAAHogEx) : le relais de cette fiche
est la tâche C39.5 sur la cadence de `projects` pendant `_railSearch` actif — **cadrée le
2026-09-10 dans [`docs/05_cadence_projects_rail_search.md`](05_cadence_projects_rail_search.md)**,
pas à rouvrir ici. ⚠️ Cette fiche-là commence par relire les chiffres ci-dessus autrement : les
89,3 % de (c) sont le **dénominateur d'un round-robin à 10 tâches actives** (pas 11 — `air`
s'auto-désactive), et (a+b) = 10,7 % coïncide avec 1/10 ; `projects` bâtit 96,6 % des fois où il
tourne. Le fallthrough n'est donc pas cassé, il est cadencé.

🆕 **Question ouverte par C41.46, en partie répondue par l'étape 0 C41.49 ci-dessus** :
`task_ops` (76,7 % du total cumulé, croissant avec la maturité de la partie) n'est toujours pas
ventilé par tâche dans le ledger C41.11/C41.46. La corrélation frontière-par-frontière de
C41.49 confirme indirectement l'hypothèse (`catalog`/`projects` la plus probable, cf. C41.22) :
`projects` n'obtient un tour dans la fenêtre utile que ~10 % du temps, cohérent avec un
round-robin à 11 tâches — mais ne prouve pas encore lequel de `catalog` ou `town_growth` occupe
le reste. Un sujet C39 de fraîcheur/cadence, pas un arbitrage C41.
