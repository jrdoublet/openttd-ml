# C78 — Les meilleures lignes d'AAAHogEx, vues depuis le vivier d'OpexAI

**Étape 1, mesurée dans la nuit du 2026-09-22.** Sonde passive (réglage `probe_portfolio`, aucune
décision changée), harnais et analyse écrits par agy, relus et lancés par Claude.

## 1. Question

Pour chacune des lignes les plus rentables d'AAAHogEx : OpexAI a-t-il **généré** la même paire de
villes comme candidat, comment l'a-t-il **classée**, l'a-t-il **construite**, et avec quel
résultat ?

## 2. Dispositif

- **Sonde** (`task_report.nut`, `_reportC78Candidates`) : à chaque rapport annuel, une ligne
  `C78_CAND` par candidat du vivier (au plus 400, par profit prédit décroissant) : mode, villes et
  industries des extrémités, profit prédit P, capital C, rang dans le classement, finançable ou non.
  Le fret porte aussi la ville la plus proche de chaque extrémité (correctif de relecture : sans
  lui, une ligne fret d'AAAHogEx, repérée par la ville de ses gares, ne pouvait jamais être
  retrouvée dans le vivier).
- **Harnais** (`sweeps/diag_c78_lines_vs_aaa.py`) : duel OpexAI (sonde) contre AAAHogEx, relevé
  des lignes des deux compagnies à chaque sauvegarde de décembre (villes, véhicules, profit de
  l'année précédente, aéroports).
- **Analyse** (`sweeps/analyse_c78.py` + requêtes du §4) : 20 meilleures lignes d'AAAHogEx par an
  et par graine, en 1973 et 1975, appariées à OpexAI par paire de villes non ordonnée et par mode.
- **Passe** : 3 graines (42, 100, 7) × 6 ans, `results/diag_c78_lines_vs_aaa.json` (non versionné,
  2 Mo). Smokes : défaut 2 × 3 ans et sonde 1 × 2 ans sains.

⚠️ Le duel n'est pas déterministe et 3 graines ne font pas un banc : ce sont des ordres de grandeur
pour orienter la suite, pas un verdict. Le profit relevé en décembre de l'année Y est celui de
l'année Y − 1 ; le vivier comparé est celui du rapport du 1er janvier de Y.

## 3. Résultat : quatre classes

120 lignes d'AAAHogEx (83 aériennes, 33 rail, 4 route).

| classe | air | rail | route |
|---|---:|---:|---:|
| construite par les deux | 12 (14 %) | 0 | 0 |
| dans le vivier la même année, non construite | 9 (11 %) | 1 | 0 |
| dans le vivier une année antérieure seulement | 14 (17 %) | 1 | 0 |
| **jamais dans le vivier** | **48 (58 %)** | **31** | **4** |

## 4. Ce que disent les classes

**Génération.** Plus de la moitié des meilleures liaisons aériennes d'AAAHogEx, et presque toutes
ses lignes ferroviaires rentables, ne sont **jamais** entrées dans le vivier d'OpexAI, aucune année.
C'est l'écart le plus large. Il ne contredit pas C55 (relâcher le filtre d'origine ne payait pas) :
C55 testait des candidats rejetés par un filtre, ici les paires ne sont pas produites du tout.

**Course perdue.** 17 % des paires aériennes étaient dans le vivier une année, puis en sont sorties,
en général après l'installation d'AAAHogEx sur la paire. Plusieurs étaient bien classées et
finançables : graine 7, paire 12-18, **rang 0 et finançable au rapport de 1973** (P = 79 k£), jamais
construite, alors qu'AAAHogEx l'exploite depuis 1971 (236 k£ en 1974) ; graine 7, paire 10-28, rang
1 en 1975 (AAAHogEx : 151 k£). Pourquoi un premier rang n'est pas construit n'est pas lisible dans
cette passe (échec de chantier, régénération du vivier avant la passe `projects` ?).

**Évaluation.** Pour les paires présentes mais non construites, le profit prédit vaut en médiane
**0,14 fois** le profit réel qu'en tire AAAHogEx (moyenne 0,49, de 0,02 à 2,94).

**Exploitation.** Sur les 12 paires construites par les deux compagnies, OpexAI y met 1 avion
(2 dans un cas), AAAHogEx 2 à 5. Par avion, AAAHogEx gagne 25 à 139 k£ par an, OpexAI 0 à 52 k£ ;
deux exceptions (graine 100, paire 7-26 : 53 et 46 k£ par avion contre 6 et 7 k£).

## 5. Suites proposées

1. **Pourquoi les paires ne sont pas générées** (l'écart n° 1) : journaliser, pour les paires
   aériennes d'AAAHogEx absentes, le filtre de génération qui les élimine (distance, population,
   site d'aéroport, borne du nombre de paires examinées).
2. **Pourquoi un premier rang finançable n'est pas construit** : relier les `C78_CAND` de rang 0 aux
   tentatives de chantier et à leurs raisons d'échec.
3. **Rendement par avion sur les paires communes** : le chargement complet à la gare de départ
   (C81, `docs/20_nuit_2026-09-22.md`) est une explication candidate ; la couverture des aéroports
   en est une autre (phase 4 de C67, `docs/21_cartographie_opportuniste.md`).

## 6. Course au second slot aéroportuaire — mesure du 22 septembre

Le premier diagnostic temporel confirme que la fenêtre physique existe généralement, mais que
le comportement courant ne la convertit pas en implantation Opex. La sonde `C78_SLOT` reste sous
`probe_portfolio=1` et ne modifie ni classement, ni cadence, ni construction. À chaque passage
`projects`, elle publie les candidats AIR du vivier avec `townA/townB`, rang, profit, capital,
capital de financement, finançabilité, score et âge, plus un horodatage des passages qui bâtissent.

Le signal adverse vient du harnais partagé, pas d'un événement NoAI : `AIStation` ne donne pas un
accès exploitable aux stations concurrentes. `sweeps/diag_1v1_shared_monthly.py
--air-slot-intercept` relève donc les `build_date` STNN d'AAAHogEx et cherche le premier passage
`projects` et le premier chantier Opex après chaque premier aéroport AAA.

Sur `results/diag_c78_slot_intercept_6y_5seeds_20260922.json`, graines 42, 100, 999, 1234 et
5678, six ans : 51 villes atteignent deux aéroports AAA. La fenêtre premier→second aéroport est
de 211 jours en médiane. Opex repasse par `projects` avant le second AAA dans 50/51 cas, après 19
jours en médiane. À ce premier passage, 11/51 villes ont au moins un candidat AIR finançable qui
les touche et 7/51 ont au moins un tel candidat déjà dans le portefeuille financé. Pourtant aucun
de ces 51 cas ne produit un aéroport Opex dans la ville avant le second aéroport AAA.

Le levier suivant est donc plus étroit que « réagir plus vite » : instrumenter les sept candidats
déjà financés pour savoir s'ils sont réellement tentés dans la passe, dépassés par un rang antérieur,
arrêtés par une recherche rail, invalidés avant tentative ou refusés par le constructeur AIR. Cette
preuve doit précéder toute règle qui ferait remonter ou forcer une interception de slot.

La tranche 2 ferme ce point sur l'état courant. `C78_SLOT` journalise aussi `air_attempt`,
`air_outcome`, `pass_stop` et `projects_exit`, puis le harnais rattache ces événements au même
identifiant de passage même si l'exécution franchit un changement de date. Le 5×6 sain
(`results/diag_c78_slot_intercept_tranche2_5x6.json`, mêmes graines), dont le bloc d'analyse a été
recalculé à partir des lignes brutes après cette correction, trouve 43 villes qui
atteignent deux aéroports AAA ; Opex repasse avant le second dans 43/43 cas, avec une fenêtre
médiane de 229 jours et 17 jours jusqu'au passage suivant. Dix villes ont alors un candidat AIR
finançable et huit en ont un dans le portefeuille financé, mais aucun aéroport Opex n'est posé
avant le second AAA.

Les huit cas financés sont désormais expliqués au premier passage : quatre sont coupés par
`k_pass`, trois par `cash` après des constructions antérieures de la même passe, et un seul est
réellement tenté ; celui-ci échoue dans le constructeur AIR avec `build_failed`, détail `AFAIL`,
erreur 263. Cette mesure ne justifie donc pas à elle seule une politique d'interception : elle
localise le reliquat dans l'exécution du portefeuille et le chantier, pas dans l'absence d'un
passage `projects` pendant la fenêtre adverse.

Un rerun lancé ensuite sur le dépôt pendant l'intégration concurrente de C78.4 n'est pas une
preuve exploitable : Opex n'y émet aucun marqueur (`missing_emitter`) et reste à zéro gare/véhicule.
Il ne remplace donc pas le 5×6 sain ci-dessus ; C78.4 doit retrouver un smoke sain avant toute
nouvelle mesure de performance ou de couverture sur l'état courant.

## 7. C78.3/C78.4 — plafond grande carte et parcours AIR reprenable

Le défaut intermédiaire missing_emitter est corrigé. La cause était structurelle : découper
seulement la boucle quadratique des paires ne suffisait pas, car le pré-scan des sites AIR pouvait
déjà traverser plusieurs suspensions et retarder la publication du portefeuille. C78.4 conserve
désormais dans son curseur les villes triées et leur limite, scanIndex/scanSites/scanProbes,
la revalidation rankIndex/rankSites, puis combo/a/b. Une tranche consomme au moins une paire
avant de rendre la main, ce qui évite de rester bloqué lorsque le coût fixe de reprise dépasse le
reliquat d'opcodes. Sur grande carte, le catalogue peut publier une première série AIR rentable
avant la fin du parcours puis la remplacer par le lot exact à l'achèvement.

C78.3 borne le vivier AIR par min(towns, cellsX*cellsY, 4*(cellsX+cellsY)), avec
cells = ceil(mapSize / AIR_TOWN_MIN_DISTANCE). Sur 1024² et AIR_TOWN_MIN_DISTANCE = 32,
cela donne **256 villes** même lorsque la carte en contient 717–733. La boucle directe a donc
un plafond combinatoire de **C(256,2) = 32 640 paires** avant les filtres et avant l'éventuelle
disparition de sites non constructibles. Le diagnostic antérieur à C78.3 (395–418 sites,
77 815–87 153 paires directes, ~11–12,5 M opcodes avant les paires) mesurait l'ancien vivier
non borné ; il ne décrit plus le chemin courant.

Validation sur le working tree courant :

- tests ciblés C78/revue : **28/28 OK** ;
- results/smoke_c78_resume_postfix_1x1.json : graine 42, 1 an, **13 véhicules / 9 gares**,
  valeur 392 579, profit annuel 298 717, statut moteur sain ;
- results/diag_c78_map1024_10x1_partial.json : malgré son nom historique partial, le fichier
  final est complet (**10/10** parties attendues/obtenues, aucune erreur de santé) ; 13 véhicules
  et 23 gares au total après un an, aucune graine sans gare. La graine 17 termine avec 0 véhicule
  mais 1 gare : c'est un résultat de construction/exploitation à analyser séparément, pas un
  retour de missing_emitter ;
- durée hôte observée du lot 1024² : environ **81 s** entre la création du checkpoint JSONL
  (18:25:22) et l'écriture du JSON final (18:26:43). Ce temps est un ordre de grandeur de campagne,
  pas un microbenchmark isolé du générateur AIR.

Le curseur C78.4 est volontairement transitoire : Save() ne sérialise que les dueCycle des tâches
de fond, pas c78AirRebuild. Après rechargement, un parcours inachevé est donc reconstruit depuis
le catalogue plutôt que de sérialiser des plans/sites complexes. Cette propriété évite de
réintroduire le coût et les risques de sérialisation qui avaient déjà affecté Save().

La prochaine question C78 n'est plus « le parcours 1024² bloque-t-il l'IA ? » mais « la sélection
des 256 villes garde-t-elle les bonnes occasions ? ». Une stratification spatiale ne doit être
introduite qu'après une mesure de rappel/qualité du vivier contre les lignes rentables d'AAAHogEx.
