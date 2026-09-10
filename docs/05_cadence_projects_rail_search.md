# C39.5 — Cadence de `projects` pendant une recherche rail active

**Contrat écrit avant code, 2026-09-10. Aucun banc, aucun diagnostic lancé sur ce document.**
Relais direct de [`docs/04_arbitrage_rail_search.md`](04_arbitrage_rail_search.md) §C41.49, fermée le
même jour : l'étape 0 y a montré que le canal ne *refuse* quasiment jamais l'alternative finançable
(**(b) = 0,4 %**), il ne l'*essaie* pas — **(c) « jamais tentée sur cette passe » = 89,3 %**, stable
sur les 5 graines. La conclusion écrite était « le levier réel est la cadence de dispatch de
`projects` ». Ce document instruit cette phrase **avant** d'écrire la moindre ligne de code, et son
premier travail est de montrer qu'elle n'est pas encore démontrée.

⚠️ Rattachement : fiche **C39** (fraîcheur / déclenchement), pas C41 (arbitrage / opcodes).
La métrique est un **délai en jours de jeu**, jamais un prix d'ombre en opcodes (⛔ C35, réfuté).

---

## 0. Ce que la mesure C41.49 dit — et ce qu'elle ne dit pas

Rappel du tableau d'étape 0 (`results/diag_c41_49_projects_fallthrough_probe_6y_5seeds.json`,
5 graines × 6 ans, 1 379 frontières de tranche A\* « avec alternative finançable ») :

| graine | frontières | (a) bâtie | (b) tentée-refusée | (c) jamais tentée | **(a+b) = `projects` a tourné** |
|---:|---:|---:|---:|---:|---:|
| 100 | 360 | 34 | 1 | 325 | **9,7 %** |
| 12345 | 301 | 35 | 1 | 265 | **12,0 %** |
| 42 | 242 | 26 | 1 | 215 | **11,2 %** |
| 7 | 193 | 20 | 1 | 172 | **10,9 %** |
| 999 | 283 | 28 | 1 | 254 | **10,2 %** |
| **cumul** | **1 379** | **143** | **5** | **1 231** | **10,7 %** |

🔑 **Lecture qui manquait à la fiche C41.49 : 89,3 % de (c) n'est pas un taux d'échec, c'est un
dénominateur de round-robin.** Deux quantités s'en déduisent, et elles pointent dans la direction
opposée à « il y a un problème » :

1. **Taux de dispatch observé de `projects` = 10,7 %** (a+b), soit 9,7–12,0 % par graine. La file
   en régime établi compte **10 tâches actives**, pas 11 : `air` s'auto-désactive à sa première
   passe sous `air_portfolio=1` (défaut adopté C36.2, `main.nut:6814`). **1/10 = 10,0 %.** Le taux
   mesuré est donc celui d'un round-robin strict, à un cheveu près — l'excédent (+0,7 pt)
   s'explique par les remises à `dueCycle = 0` événementielles (`main.nut:5921/5955/5992`).
2. **Taux de succès conditionnel = 143/148 = 96,6 %.** Quand `projects` obtient son tour à une
   frontière utile, il bâtit **presque toujours**.

**Conséquence : le fallthrough n'est pas cassé, il est cadencé.** Rien dans les données de C41.49
ne dit qu'une alternative a été *perdue* — seulement qu'elle a attendu son tour. Un tour de file
est court ; **combien de jours de jeu il dure n'a jamais été mesuré**, et c'est exactement le
chiffre qui manque pour trancher.

---

## 1. Le mécanisme, vérifié dans le code (pas seulement mesuré)

| # | fait | lieu |
|---|---|---|
| 1 | **Round-robin strict, une tâche par passe.** Le curseur est avancé (`_taskCursor = (taskIndex+1) % len`) puis la tâche élue reçoit `dueCycle = this._taskCycle + 1` : exactement une exécution par tour continu. | `main.nut:6260-6285` |
| 2 | **10 tâches actives en régime établi** : `catalog`, `report`, `scrap`, `air_fleet`, `feeders`, `projects`, `expand`, `refleet`, `town_growth`, `repay`. (`air` s'éteint sous `air_portfolio=1` ; les 4 tâches C41 ciblées naissent `enabled=false`.) | `main.nut:1315-1350`, `6814` |
| 3 | 🔑 **Une abstention consomme le tour.** `dueCycle` est posé **avant** le dispatch (ligne 6285) : `projects` qui sort en `return false` sur `_portfolioInvalidated` (`main.nut:6847`) a déjà brûlé son tour et attend un cycle complet. Idem pour toute tâche hors période. | `main.nut:6285`, `6847` |
| 4 | **Au plus UN projet bâti par passe** (`PORTFOLIO_MAX_BATCH = 1`, défaut), et un succès régénère lui-même le portefeuille. | `main.nut:976`, `3292` |
| 5 | 🔑 **`_consumeRailSearch` ne tourne QUE dans la tâche `projects`.** La phase `"build"` d'une recherche rail est donc cadencée par **la même horloge** que le fallthrough non-rail. Atténué, pas supprimé, par C41.47 (`c41_rail_cash_release=1` par défaut, N=0 : le premier blocage trésorerie libère `_railSearch`, donc la fenêtre `"build"` ne dure au plus qu'**un** dispatch de `projects`). | `main.nut:3320-3323`, `5057` |
| 6 | **La tranche A\* est jouée AVANT la file, dans la même passe** — elle ne prend pas de tour et ne décale pas le round-robin. | `main.nut:6237-6252` |
| 7 | ⚠️ **Une passe ≠ un tick, et un tick ≠ une durée fixe de jeu.** Sous `loop_budget=0` (défaut, `info.nut:1923`), la boucle exécute une tâche puis `Sleep(1)` — mais une passe lourde s'étale sur plusieurs ticks par suspension, et les commandes d'API coûtent des **jours de jeu sans coûter d'opcodes** (mesuré ailleurs : un passage `OpexAirPlans` ≈ 21 jours, `main.nut:6811`). | `main.nut:940-963` |

### 1.1 ⛔ La conversion passes → jours n'est PAS dérivable des ledgers existants

Deux estimations à partir des mesures déjà au dossier donnent des résultats incompatibles :

- **Par les opcodes** : ledger C41.46, 823,6 M + 250,5 M sur 1 710 tranches ⇒ ~628 k opcodes/passe
  ⇒ ~63 ticks ⇒ **~0,85 jour/passe** ⇒ un tour de file ≈ 8,5 jours.
- **Par le comptage brut** : ledger C41.11 du 1971-01-11, **866 passes** pour ~1 an ⇒ ~31 ticks/passe
  ⇒ **~0,42 jour/passe** ⇒ un tour de file ≈ 4,2 jours. Or ces mêmes 866 passes ne totalisent que
  61,3 M opcodes, soit ~7 ticks de calcul : les 24 ticks restants sont du **temps de jeu consommé
  par les commandes**, pas du calcul.

Facteur 2 d'écart, et les deux chiffres mélangent des passes qui font 3 opcodes avec des passes qui
reconstruisent un catalogue (2,09 M opcodes, C41.22). **Aucune moyenne dérivée ne peut servir de
critère.** Le délai doit être **horodaté directement**, c'est tout l'objet de l'étape 1.

---

## 2. L'hypothèse nulle qu'il faut battre

**H0 — la cadence est bénigne.** `projects` tourne à 10,7 % des passes (= son dû exact), bâtit
96,6 % des fois où il tourne, et l'alternative « manquée » à une frontière est bâtie quelques passes
plus tard, sans perte matérielle. Sous H0, accélérer la cadence ne crée **aucun** chantier
supplémentaire : elle en déplace la date de quelques jours.

H0 n'est pas une pose de prudence : **elle est soutenue par une mesure déjà au dossier.**
`portfolio_max_batch=4` contre 1 (banc apparié 20 graines × 3 ans, 2026-09-02,
`results/bench_portfolio_max_batch_3y.json`) a donné **company_value −3,8 %, n_stations −7,9 %,
n_vehicles −9,5 %**, et le diagnostic aux panneaux (`results/diag_batch8_5seeds.json`) a dit
pourquoi : *un passage réussi régénère lui-même le portefeuille, donc bâtir deux projets dans la
même passe ne fait pas un chantier de plus, il **fusionne deux cycles en un**.* Et même à 8, le
batch ne dépasse jamais deux, parce que **la caisse est vidée entre-temps par les tâches
concurrentes** — 295 000 £ mobilisables tombent à 24 013 £ après un seul chantier à 26 589 £.

🔑 **Le précédent est direct : « donner plus de débit au portefeuille » a déjà été essayé sur l'axe
*par passe*, et c'était négatif, parce que le goulot mesuré est la CONCURRENCE POUR LA CAISSE.**
Cette fiche tente le même geste sur l'axe *fréquence des passes*. Elle doit donc, avant tout code,
montrer que le délai est matériel **en jours** — sinon elle rejoue un réfuté sous un autre nom.

**H1 — la cadence coûte du volume.** Le délai médian entre « l'alternative est en tête du vivier et
finançable » et « elle est bâtie » est assez long pour que la caisse soit captée entre-temps par une
autre tâche (`town_growth`, `air_fleet`, `feeders`, `refleet`), ou pour que le candidat périme au
rafraîchissement mensuel suivant. Alors la construction n'est pas seulement retardée : elle est
**remplacée** par un choix pris sur un autre critère que le ROI du portefeuille.

H1 est réfutable, H0 aussi, et **une seule mesure les sépare : la distribution du délai.**

---

## 3. La métrique de la fiche

⛔ **Interdits, avec leur motif** — ne pas les reproposer sous un habillage nouveau :

| interdit | motif |
|---|---|
| prix d'ombre en opcodes d'un dispatch | ⛔ C35, réfuté |
| règle de domination / arrêt optimal sur l'A\* rail | 🔒 C41.49 fermée le 2026-09-10 |
| `portfolio_max_batch > 1` | banc 20×3 négatif (−3,8 %), cause identifiée |
| `portfolio_dynamic_batch = 1` | non défaut, change le fallthrough qu'on cherche à mesurer (`main.nut:3309-3318`) |
| réordonner `_taskQueue` « pour mettre `projects` devant » | `fleet_before_new` a déjà mesuré −20,4 % sur ce geste ; l'ordre de service existant est un **principe** ([[principe_regler_avant_construire]]), pas un réglage libre |
| `rail_search_resumable` | déjà à 1, adopté (`info.nut:1167`) |
| `town_growth_skip_noop` | banc 20×10 refait le 2026-09-10 : ni rejet ni adoption, défaut 0 conservé |

**Métriques retenues**, toutes en **jours de jeu** :

- **D1 — délai de dispatch.** Jours écoulés entre deux exécutions consécutives de la tâche
  `projects`, **conditionné** sur `_railSearch != null` vs `== null`. Distribution : médiane, p90,
  max. C'est la mesure du tour de file, celle qui manque au §1.1.
- **D2 — délai de captation.** Pour chaque projet non-rail effectivement bâti : jours entre
  **le premier instant où il était en tête du vivier ET finançable** (même formule
  `OpexAvailableCapital()` que le chemin réel, comme la sonde C41.48) et **l'instant de sa
  construction**. C'est la métrique de la fiche : le délai de construction de l'alternative captée
  en retard.
- **D3 — abstentions et leur cause.** Nombre de tours de `projects` consommés sans rien tenter, et
  la cause lue **au site d'appel** : `_portfolioInvalidated` (`main.nut:6847`) ou vivier vide
  (`_projects.best.len() == 0`).

**Critère de passage à l'étape 2** — décidé maintenant, avant de voir les chiffres :

- **FERMER** la fiche si `médiane(D2) ≤ 5 jours` **et** `p90(D2) < 30 jours` sur au moins 4 graines
  sur 5. Motif du seuil à 30 jours : le vivier est régénéré au **changement de mois**
  (`_lastCatalogMonth`, `main.nut:6321`) ; un délai qui dépasse le mois survit au
  rafraîchissement qui a produit le candidat — ce n'est alors plus un retard d'ordonnancement, c'est
  un **autre candidat**. En deçà, le retard est un réordonnancement interne au cycle, exactement ce
  que `portfolio_max_batch` a déjà montré sans valeur.
- **INSTRUIRE** l'étape 2 si `p90(D2) ≥ 30 jours` sur ≥ 4 graines sur 5, **ou** si D3 révèle que les
  abstentions (et non le round-robin) dominent le délai — auquel cas le sujet n'est plus la cadence
  mais l'invalidation, et il redescend en C39.2/C39.3 déjà instrumentés.

---

## 4. Étape 1 — la sonde (à coder, défaut 0, aucun banc)

Réglage `c39_projects_cadence_probe`, `easy/medium/hard/custom = 0`, `AICONFIG_BOOLEAN`.
**Gate de journal DÉDIÉ** : `OpexC39ProjectsCadenceLog`, pas `OpexC41SchedulerLog` ni
`OpexC41ProjectsFallthroughLog` — 🐛 c'est le piège trouvé au premier smoke test de C41.46 : une
sonde gatée sur les drapeaux d'une autre fiche n'émet rien quand on n'arme que le sien.

Trois points d'instrumentation, tous en lecture seule, **aucune décision modifiée** :

1. **Au site d'appel de la tâche** (`main.nut:6844-6849`, tâche `"projects"`), **avant** le
   `if (this._portfolioInvalidated) return false;` :
   `phase=dispatch`, `days_since_last` (D1), `rail_search` (0/1), `rail_phase`
   (`search`/`build`/`-`), `invalidated`, `best_len`, `capital`.
   ⚠️ **C'est ici, et nulle part ailleurs, que `_portfolioInvalidated` est observable.** Le champ
   `invalidated` que loggue la sonde C41.49 **à l'intérieur** de `_tryBuildProjects` est mort :
   le site d'appel filtre déjà le drapeau avant d'entrer dans la fonction (angle mort documenté
   §C41.49 de la fiche 04). Reproduire cette erreur invaliderait D3.
2. **Marquage de fraîcheur du vivier**, dans la génération du portefeuille : horodater
   (`AIDate.GetCurrentDate()`) le premier instant où un projet donné apparaît **en tête et
   finançable**. Une seule date par clé `OpexProjectAttemptKey(project)`, jamais réécrite tant que
   la clé survit à une régénération, purgée quand elle disparaît du vivier.
3. **À la construction** d'un projet non-rail dans `_tryBuildProjects` : `phase=built`, `mode`,
   `days_since_financeable` (D2), `rail_search`.

**Diagnostic** : 5 graines × 6 ans, solo, mêmes graines que C41.48/C41.49 (`100, 12345, 42, 7, 999`)
pour rester comparable. ⚠️ **La sonde déplace la trajectoire** : le total de frontières est passé de
973 (C41.48 seule) à 1 379 (les deux sondes armées) sur les mêmes graines — effet attendu et déjà
documenté ([[banc_monograine_insuffisant]], §1.1bis de la fiche 04), pas une contradiction. Lire les
**parts et les distributions**, jamais les totaux absolus d'une arm contre une autre.

⛔ **Aucun banc officiel à cette étape.** Une sonde à défaut 0 ne change aucun défaut : il n'y a rien
à bancher tant que le critère du §3 n'a pas été lu.

### 4.1 ✅ Étape 1 mesurée (2026-09-10) — le résultat renverse le cadrage

`c39_projects_cadence_probe=1`, solo, 5 graines × 6 ans, `sweeps/diag_c39_5_projects_cadence_probe.py`,
`results/diag_c39_5_projects_cadence_probe_6y_5seeds.json`, **0 échec**. 705 lignes `dispatch`,
266 lignes `built`. La mesure couvre **10 803 des 10 950 jours-graines** (98,7 % — le reliquat est
l'intervalle avant le premier dispatch de chaque graine), donc la comptabilité du temps est close.

**D1 — intervalle entre deux tours de `projects`, en jours de jeu :**

| régime | n | médiane | p90 | max | moyenne |
|---|---:|---:|---:|---:|---:|
| `_railSearch == null` | 505 | **4 j** | 23 j | 68 j | 7,4 j |
| `_railSearch != null` | 195 | **36 j** | 57 j | 84 j | 36,3 j |

Par graine, la médiane sous recherche rail vaut 34, 35,5, 36, 40 et 44 jours : **les 5 graines sont
d'accord**, l'effet n'est pas tiré par une divergente.

🔑 **`cycles_since_last` vaut 1 dans 99,4 % des dispatches et n'excède JAMAIS 1.** `projects` n'est
donc **pas** sauté, pas affamé, pas retardé par une abstention : il obtient exactement son tour à
chaque cycle de la file, comme le round-robin le prévoit. **Ce n'est pas la place de `projects` dans
la file qui change — c'est la DURÉE du cycle**, qui passe de 7,4 à 36,3 jours (×4,9 en moyenne,
×9 en médiane) dès qu'une recherche rail est en vol.

🔑 **Et ce régime est le régime dominant : 7 073 jours sur 10 803, soit 65,5 % du temps de jeu, se
passent avec `_railSearch != null`.** Les 10 tâches de la file paient ce ralentissement, pas
seulement `projects` : pendant les deux tiers de la partie, **l'horloge de décision entière de l'IA
tourne ~5 fois moins vite**.

**D2 — délai de captation (premier instant finançable → construction), en jours de jeu :**

| régime au moment du chantier | n | médiane | p90 | max |
|---|---:|---:|---:|---:|
| `_railSearch == null` | 93 | **4 j** | 180 j | 604 j |
| `_railSearch != null` | 158 | **192,5 j** | 656 j | 1 435 j |
| cumul tous modes | 251 | 64 j | 519 j | 1 435 j |

(hors rail : 250 chantiers, médiane 64,5 j — le rail ne tire pas le résultat. 15 chantiers `built`
sans marquage préalable, tous sous recherche rail : devenus finançables et bâtis dans la même passe.)

**D3 — les abstentions :**

| cause | part des dispatches |
|---|---:|
| `_portfolioInvalidated == 1` | **0,14 %** (0 sur 4 graines, 1,25 % sur la graine 7) |
| `best_len <= 0` (vivier vide) | **55,3 %** (15,8 % à 72,3 % selon la graine) |
| `financeable == 0` | 55,3 % (exactement les mêmes passes) |

### 4.2 Verdict contre le critère pré-enregistré du §3

Le critère de FERMETURE exigeait `médiane(D2) ≤ 5 j` **et** `p90(D2) < 30 j` sur ≥ 4 graines/5.
Mesuré : médiane 64 j, p90 519 j. **Fermeture refusée, très largement.** H0 (« la cadence est
bénigne ») est écartée : le délai est matériel en jours, pas un réordonnancement interne au cycle.

⚠️ **Mais l'étape 2 telle que le §5 l'a écrite ne suit PAS de ce résultat**, et c'est le point le
plus important de cette mesure :

1. **Les leviers L1/L2 visaient une starvation qui n'existe pas.** `cycles_since_last` toujours à 1
   dit que `projects` a déjà son tour à chaque cycle. Poser `dueCycle = 0` lui donnerait des tours
   *supplémentaires* dans un cycle — ça raccourcirait son intervalle, mais en prenant le tour des
   9 autres tâches, qui subissent **exactement le même** ralentissement. C'est un arbitrage entre
   tâches également pénalisées, déguisé en correctif.
2. **Le vivier vide domine les abstentions à 55,3 %.** Le §6 avait posé d'avance que si D3 était
   dominé par `best_len == 0`, la fiche se referme « vers C41/vivier, pas vers un levier de
   cadence ». C'est le cas. `_portfolioInvalidated`, lui, est confirmé inerte (0,14 %) — le point 4
   de la lecture de scheduler de la fiche 04 était juste.
3. ⛔ **D2 ne mesure pas que la cadence.** Le marquage horodate TOUS les projets finançables du
   vivier, pas seulement le premier ; un projet au rang 5 attend derrière les mieux classés, un par
   passe (`PORTFOLIO_MAX_BATCH = 1`). D2 agrège donc cadence + file d'attente par rang + concurrence
   pour la caisse. La comparaison ×48 entre les deux régimes contrôle en partie ces trois termes
   (mêmes règles des deux côtés), **mais ne les sépare pas** : ne pas citer les 192 jours comme un
   coût de cadence pur.

### 4.3 ❌ ERREUR CORRIGÉE — le « facteur 15 » n'existe pas, c'était une faute d'unité

⛔ **Le §4.3 d'origine (conservé plus bas, barré) affirmait un facteur ~15 inexpliqué entre le coût
en opcodes d'une tranche A\* et les jours de jeu qu'elle coûte. C'est FAUX, et l'erreur est de moi :
j'avais converti les ticks en jours à 74 ticks/jour.** La sonde C39.6
(`c39_pass_clock_ledger=0` par défaut, `results/diag_c39_6_pass_clock_6y_5seeds.json`, 5 graines ×
6 ans, 0 échec) mesure directement le rapport : **18,48 ticks par jour**, pas 74. Une tranche de
~150 k opcodes vaut donc ~14,6 ticks ≈ **0,79 jour**, pas 0,2 jour. L'écart se referme entièrement.

🔑 **Et la mesure va plus loin : les jours SONT les opcodes.** Sur les passes contenant une tranche
A\*, la part de la tranche vaut **22,4 % des jours, 22,3 % des ticks, 22,9 % des opcodes** — la même
proportion à trois chiffres près. Cumul : 1,668 G d'opcodes pour 8 967 jours, soit **186 k opcodes
par jour de jeu** = 10 k/tick × 18,5 ticks/jour. **Il n'y a aucun coût caché en jours d'API.**
[[philosophie_opcodes_ressource]] tient : l'opcode reste la ressource, et le jour n'en est qu'une
autre unité.

### 4.3 bis ✅ Ce que C39.6 trouve vraiment — et le confondant qui tue la conclusion facile

En cumul, une passe coûte **3,54 jours** quand une tranche A\* y tourne contre **0,81 jour** sinon
(×4,4), et chaque tâche de file suit : `projects` 9,60 j/passe contre 2,12, `catalog` 8,35 contre
2,03, `town_growth` 7,48 contre 2,30. Tentant d'en conclure que la recherche rail ralentit tout.

⚠️ **Le contrôle année par année dit le contraire** (relecture du journal brut par année) :

| année | j/passe avec tranche | j/passe sans | rapport |
|---|---:|---:|---:|
| 1971 | 1,88 | 0,39 | **4,84** |
| 1972 | 2,57 | 0,82 | 3,16 |
| 1973 | 3,97 | 2,26 | 1,75 |
| 1974 | 4,71 | 4,29 | 1,10 |
| 1975 | 5,40 | 5,92 | **0,91** |

**Le rapport s'effondre de 4,84 à 0,91.** En fin de partie, une passe avec recherche rail ne coûte
plus rien de plus qu'une passe sans. Le ×4,4 cumulé est donc **un artefact de maturité**, pas un
effet de la recherche rail — exactement la même forme que l'effondrement 45 % → 13 % de la part
nette de l'A\* mesuré par C41.46.

🔑 **Le vrai effet, lui, est énorme et n'a rien à voir avec le rail : le coût d'une passe est
multiplié par ~15 en cinq ans** (0,39 → 5,92 jours pour les passes sans tranche). C'est **ça** qui
étire l'horloge de décision, et c'est cohérent avec le coût d'une reconstruction de catalogue
(2,09 M opcodes, C41.22) qui croît avec la carte. **C'est le sujet à instruire**, et il est
indépendant du canal rail.

⚠️ **Tension résiduelle non résolue** : C39.5 mesure D1 = 35,5 j sous recherche rail contre 2 j
hors (médianes), alors qu'en 1975 les deux régimes coûtent le même prix par passe. Médianes contre
moyennes et distributions très étalées expliquent peut-être l'écart, ce n'est pas démontré.
**Ne pas citer les deux chiffres côte à côte comme s'ils se corroboraient.**

⚠️ Couverture de C39.6 : **81,9 %** du temps de jeu (contre 98,7 % pour C39.5) — le ledger est
publié annuellement par la tâche `report`, donc la dernière année partielle est perdue.

### ~~4.3 (version d'origine, RÉFUTÉE ci-dessus)~~ : d'où viennent 3,6 jours par passe ?

Une passe coûte ~0,74 jour hors recherche rail et ~3,6 jours pendant. Or la tranche A\* mesurée par
C41.46 vaut ~146 k opcodes (250,5 M / 1 710 tranches), soit ~15 ticks ≈ **0,2 jour**. **Il manque
donc plus d'un facteur 15 entre le coût en opcodes de la tranche et le temps de jeu qu'elle fait
perdre au cycle.** Les commandes d'API consomment des jours sans consommer d'opcodes (§1 point 7) —
c'est l'explication la plus probable, elle n'est pas démontrée.

🔑 **Ça reformule la question de C41.46 (« quelle tâche gonfle `task_ops` ? »), qui postulait que les
opcodes sont la ressource rare. En jours de jeu, la recherche rail coûte ~5× le temps de cycle
pendant 65 % de la partie, alors qu'elle ne pèse que 23,3 % des opcodes.** [[philosophie_opcodes_ressource]]
tient toujours pour le budget par tick, mais **le tick n'est pas le jour**, et c'est le jour qui
décide du volume. La prochaine mesure est là, pas dans un levier de file.

### 4.4 ✅ Étape 1 bis (2026-09-10) — la décomposition tranche : **ce n'est PAS la cadence**

La sonde a été enrichie pour séparer les trois causes que §4.2 point 3 refusait de confondre :
`topSince`/`topTurns` datent et comptent les tours où un projet est **le meilleur finançable**
(première entrée de `best` avec `capital <= OpexAvailableCapital()`, définition identique à C41.48).
Diagnostic relancé, 5 graines × 6 ans, `results/diag_c39_5b_projects_cadence_probe_6y_5seeds.json`,
**0 échec**, 754 dispatches, 261 chantiers.

| | hors recherche rail | pendant une recherche rail |
|---|---:|---:|
| D1, intervalle entre deux tours | 2 j | **35,5 j** |
| D2 brut (`days_since_financeable`) | 3 j | **173 j** |
| **délai depuis « meilleur finançable »** (`days_since_top`) | 1 j | **5 j** |
| **tours depuis « meilleur finançable »** (`turns_since_top`) | **1** | **1** |
| tours depuis « finançable » (`turns_since_financeable`) | 1 | 6 |

🔑 **`turns_since_top` vaut 1 en médiane, 1 au p90 et 2 au maximum — dans les DEUX régimes.**
Autrement dit : **dès qu'un projet devient le meilleur candidat finançable, il est bâti au tout
premier tour de `projects` qui suit, sans exception.** Le délai de 173 jours n'est donc pas un
délai de cadence : c'est le temps que le projet passe à **attendre son rang**, derrière des
candidats mieux classés, à raison d'un chantier par passe (`PORTFOLIO_MAX_BATCH = 1`).

**H1 est réfutée pour le candidat de tête.** Le §4.2 avait déjà écarté L1/L2 parce que
`cycles_since_last` ne dépasse jamais 1 ; cette mesure-ci ferme la question pour de bon : accélérer
la cadence ne peut pas produire un chantier de plus, puisque **aucun chantier n'attend jamais plus
d'un tour** une fois qu'il est le bon choix. C'est exactement le mécanisme qui avait fait échouer
`portfolio_max_batch=4` (§2), redécouvert par l'autre bout.

### 4.5 🆕 Deux trous ouverts par cette mesure, tous deux hors cadence

1. **Le meilleur finançable n'est PAS ce qui se construit, deux fois sur trois.**
   `never_top_share` — part des chantiers dont le projet n'a JAMAIS été observé en tête des
   finançables — vaut **54,4 % au total, 67,8 % pendant une recherche rail** (24,7 % hors). Le
   candidat de tête du sac à dos est donc régulièrement **injouable** (rejeté par les gardes de son
   mode), et c'est un rang inférieur qui passe. Le classement décide beaucoup moins qu'il n'y
   paraît. **C'est un sujet de qualité de vivier, pas d'ordonnancement.**
2. **Le vivier est VIDE dans 58,6 % des tours de `projects`** — et la correction de la sonde
   tranche l'ambiguïté qui restait : `best_len_missing` (pas de portefeuille du tout) vaut
   **0,0 %**. Les 58,6 % sont donc une vraie vacuité du vivier, jamais un artefact d'objet absent.
   `_portfolioInvalidated` reste inerte (0,27 %).

Avec le facteur 15 de §4.3 (une passe coûte ~3,6 jours de jeu pendant une recherche rail, contre
~0,2 jour d'opcodes A\*), ce sont les trois questions qui survivent à cette fiche. **Aucune n'est
une question de cadence.**

---

## 5. Étape 2 — les leviers candidats (conditionnels, à ne PAS coder avant le §3)

Listés ici pour que l'étape 1 sache ce qu'elle doit permettre de départager, **pas** pour être
écrits. Tous à défaut `0`, un réglage par levier, jamais deux changements dans une même
implémentation ([[seuils_tresorerie_et_sac_a_dos]] : un rejet évité de justesse parce que
l'implémentation changeait deux choses à la fois).

- **L1 — `c39_projects_due_on_capital`** *(préféré)*. Poser `projects.dueCycle = 0` quand le capital
  mobilisable franchit **à la hausse** le coût du meilleur projet finançable du vivier — c'est-à-dire
  quand l'état a changé la décision, et seulement alors. C'est la thèse même de C39
  (« déclencher un rafraîchissement seulement quand il change la décision ») appliquée au dispatch
  au lieu du rafraîchissement, et ça réutilise à l'identique le motif `dueCycle = 0` déjà en place
  pour les invalidations événementielles (`main.nut:5921`). Coût : un tour pris aux 9 autres tâches,
  seulement aux instants où il change quelque chose.
- **L2 — `c39_projects_due_after_slice`**. Poser `projects.dueCycle = 0` à chaque frontière de
  tranche A\* (`slice.done == false`). Plus simple, mais **beaucoup** plus fréquent (1 379 frontières
  sur 5 graines × 6 ans) et aveugle à l'état de la caisse : c'est le levier qui risque le plus de
  rejouer le résultat négatif de `portfolio_max_batch` en fusionnant des cycles au lieu d'en ajouter.
  À ne considérer que si L1 est infaisable.
- **L3 — ne rien faire dans la file.** Si D1 est dominé non par le nombre de tâches mais par la
  **durée** de quelques passes (une reconstruction de catalogue à 2,09 M opcodes en tête), alors le
  sujet n'est pas la cadence de `projects` : c'est le coût de `catalog`, et ça rejoint la question
  restée ouverte par C41.46 — `task_ops` (76,7 % du cumul, croissant avec la maturité) n'est
  **toujours pas ventilé par tâche**. Ce serait la vraie conclusion de la fiche, et elle est
  parfaitement acceptable.

**Si un levier passe l'étape 1** : banc officiel **20 graines × 10 ans apparié** (`AGENTS.md`),
lecture au **test des signes** avant les moyennes — C41.47 est le précédent exact d'un diagnostic 5×6
NUL et sous-puissant démenti par un banc 20×10 net (19/20, p < 0,0001).

---

## 6. Ce que cette fiche ne fait pas

- **Elle ne rouvre pas C41.49.** Aucune règle de décision sur la recherche rail n'y est écrite, et il
  n'y en aura pas : la fiche 04 est fermée sur ce point.
- **Elle ne touche pas à l'offre du vivier.** Un instant où `considered=260 selected=0` avec
  52 952 £ en caisse est un problème d'**offre**, pas d'ordonnancement (fiche 04 §4). Si D3 montre
  que les abstentions sont dominées par `best_len == 0`, la fiche se referme vers C41/vivier, pas
  vers un levier de cadence.
- **Elle ne réordonne pas `_taskQueue`** et ne touche pas à `fleet_before_new` : l'ordre de service
  existant est un principe mesuré, pas un paramètre à balayer.
- **Elle ne mesure pas le coût en opcodes d'un dispatch de `projects`.** Ce serait un prix d'ombre
  (⛔ C35). Le coût d'un levier se juge **au banc, sur les 5 métriques de jeu**, jamais à
  l'instrumentation.

## 7. Critère de clôture

✅ Fiche cadrée. ✅ **Étape 1 livrée et lue le 2026-09-10** (§4.1) : sonde codée, diagnostic 5×6,
0 échec, D1/D2/D3 par graine. ✅ **Décision §3 prise** : fermeture REFUSÉE (médiane D2 = 64 j contre
≤ 5 j exigés), H0 écartée — **mais les leviers L1/L2 du §5 sont écartés eux aussi**, pour un motif
que la mesure a produit et que le cadrage n'avait pas anticipé : `cycles_since_last` ne dépasse
jamais 1, donc `projects` n'est pas affamé ; c'est le cycle entier qui dure 36 j au lieu de 7 j
pendant les 65,5 % de la partie où une recherche rail est en vol. ⬜ **Rien à bancher** : il n'y a
pas de levier instruit. ⬜ **Prochaine mesure** = §4.3, l'écart d'un facteur 15 entre le coût en
opcodes d'une tranche A\* et les jours de jeu qu'elle coûte au cycle.

🔒 **FICHE FERMÉE le 2026-09-10 sur le levier de cadence** (§4.4) : `turns_since_top` vaut 1
(médiane, p90 ; max 2) dans les deux régimes — un projet est bâti au premier tour de `projects` qui
suit le moment où il devient le meilleur finançable. Aucun chantier n'attend la cadence. Les trois
questions qui survivent (§4.3, §4.5) sont ailleurs : le facteur 15 opcodes/jours, le candidat de
tête injouable 2 fois sur 3, le vivier vide 58,6 % du temps.

⚠️ **Ne pas coder L1/L2 sur la foi du « D2 = 192 jours ».** Ce chiffre agrège trois causes
(cadence, file d'attente par rang sous `PORTFOLIO_MAX_BATCH = 1`, concurrence pour la caisse) que la
sonde ne sépare pas, et 55,3 % des tours de `projects` trouvent un vivier VIDE — sujet d'offre, pas
d'ordonnancement.

⚠️ Le volume reste la métrique n°1 (~85 % de l'écart avec AAAHogEx). Cette fiche ne se justifie que
si elle en produit : **un délai raccourci qui ne produit pas de chantier supplémentaire est un
résultat NUL**, et le précédent `portfolio_max_batch` dit que c'est l'issue la plus probable.
