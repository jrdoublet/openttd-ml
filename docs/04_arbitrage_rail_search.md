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

### ✅ C41.47 — Libérer l'état rail quand le blocage est la trésorerie *(correctif, codé 2026-09-09)*

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
**Défaut inchangé (`0`) en attendant.**

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

### C41.49 — Le test lui-même *(C41.48 montre des déclenchements — 973/30 graines-années — mais lire la nuance ci-dessus avant de coder)*

⚠️ **Ne pas coder tel quel sans re-trancher la justification.** La règle ci-dessous a été conçue
comme un arrêt optimal en **opcodes** ([[philosophie-opcodes-ressource]]). C41.46 a depuis montré
que le gisement d'opcodes net de l'A\* rail est faible et décroissant (23,3 % cumulé) — couper des
recherches pour ce motif rapporterait peu. Si C41.49 se justifie, c'est plutôt par le **volume**
(rediriger du capital vers un projet prêt plus tôt), la métrique n°1 du projet — mais alors le
dénominateur `E[itérations restantes]` n'est plus la bonne unité de comparaison : il faudrait
comparer des **délais de construction**, pas des opcodes. Cette reformulation n'est pas faite.

`c41_rail_domination=0`. À la frontière de segment uniquement (forme originale, à revoir) :

```
continuer  ssi  profitAnnuel_rail / E[itérations restantes]  ≥  taux_référence
```

- **Marginal, jamais total** : `state.spent` est du sunk cost et n'entre pas au dénominateur.
  C'est la règle d'arrêt optimal de [[philosophie-opcodes-ressource]], pas une comparaison de ROI.
- **`E[itérations restantes]`** s'estime sur les segments déjà franchis : itérations par tuile de
  préfixe × distance restante. À calibrer sur la trace C41.48, jamais posée à vue.
- **`taux_référence`** = profit annuel par itération réalisé par l'IA sur la période récente
  (les deux membres sont en `profit / itération`).
- ⛔ **Aucune conversion d'opcodes en £.** C'est ce qui a tué C35 (`λ_ops × a_ops` : 0 rail sur
  4 graines) et ses deux corrections (7/7 défaites chacune). Si une version de ce test réintroduit
  un prix d'ombre, elle est déjà réfutée.
- ⛔ **Aucune échéance globale posée à l'entrée** : c'est la cause diagnostiquée des rejets
  `rail_search_resumable` (−23,1 % puis −13,3 %), soignée par C20. La borne est ré-évaluée à chaque
  frontière et ne peut pas amputer une recherche déjà avancée.

*Mesure* : diagnostic 5×6, puis **banc officiel apparié 20×10**.

---

## 4. Ce que ce contrat ne fait pas

- **Il ne réordonne pas `_taskQueue`.** La recherche est reprise en tête de `_runNextTask`, avant
  que la file soit consultée : aucun rang ne l'atteint. Le point 1 de l'orchestrateur
  (`town_growth` qui prend le tour sans rien accomplir, 442 échecs sur 453) est **orthogonal** et
  se traite dans la file.
- **Il ne corrige pas `TRACEX`.** Les 20 panneaux `RA|` d'échec rail sont tous en `TRACEX`, comme
  les 442 échecs de `town_growth` — un motif partagé, à instruire séparément.
- **Il ne touche pas à l'offre du vivier.** Le dernier vivier de la partie (1971-12-15) donne
  `considered=260 selected=0 rejected=260` avec 52 952 £ en caisse : l'abstention de `projects`
  (3 tours utiles sur 37) est un problème d'offre, pas d'ordonnancement.

## 5. Critère de clôture

✅ C41.46 livré et lu (§1.1bis) ; ✅ C41.48 livré et lu (§C41.48, 973 frontières avec alternative
sur 30 graines-années) ; ⚠️ C41.47 codé, diagnostic 5×6 **NUL** (14/14 constructions identiques,
délai mixte) — banc officiel 20×10 non lancé faute de signal directionnel à confirmer ; C41.49
**non codé**, sa justification d'origine (arrêt optimal en opcodes) affaiblie par C41.46 et à
reformuler en délai de construction avant d'écrire quoi que ce soit. ⚠️ Le volume est la métrique
n°1 (~85 % de l'écart avec AAAHogEx) : toute variante qui coupe des recherches sans augmenter le
nombre de constructions est un échec, même si elle économise des opcodes.

🆕 **Question ouverte par C41.46, à trancher avant de prioriser C41.49** : `task_ops` (76,7 % du
total cumulé, croissant avec la maturité de la partie) n'est pas ventilé par tâche dans ce ledger.
Avant d'écrire un test de domination pour l'A\* — dont le gisement mesuré est maintenant 23,3 %,
pas 79,7 % — instrumenter *quelle* tâche de file coïncide avec une recherche rail en cours (nom de
tâche + coût, réutilisable via `this._c41LastTaskName` déjà disponible dans
`_runNextTaskWithSlackLedger`) est probablement plus rentable : si c'est `catalog`/`projects`
(hypothèse la plus probable, cf. C41.22), c'est un sujet C39 de fraîcheur, pas un arbitrage C41.
