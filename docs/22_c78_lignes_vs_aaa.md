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

## ⛔ Correction du 2026-09-22 (étape 2) : les §3 à §5 sont faux

La sauvegarde stocke la ville d'une gare comme **référence d'objet : identifiant de l'API + 1**
(0 = aucune). Le décodeur partagé (`bench_1v1_5y_20seeds.py`) ne retire pas ce 1 : les villes des
lignes relevées dans la sauvegarde étaient décalées d'une place par rapport aux villes journalisées
par l'IA (`C78_CAND`). Preuve : la ville la plus proche d'une gare d'OpexAI est la ville
« sauvegarde − 1 » dans 11 416 cas, contre ~170 pour tout autre décalage ; après correction, 100 %
des gares des deux compagnies retombent sur leur ville la plus proche.

- **Faux** : les classes du §3 (« 58 % jamais dans le vivier », « 17 % sortis ») et le cas « graine 7,
  paire 12-18, rang 0 » du §4 comparaient des paires de villes décalées.
- **Justes** : les paires construites par les deux compagnies et la comparaison par avion (1 avion
  contre 2 à 5 ; 0-52 k£ contre 25-139 k£ par avion), car les deux côtés venaient de la sauvegarde.
- Le harnais corrige désormais (`towns` = identifiants de l'API, `towns_raw` = valeur brute).
  `diag_b9_air_catchment.py` détectait et corrigeait déjà ce décalage de son côté ; les autres
  scripts comparent des lignes de la sauvegarde entre elles et ne sont pas touchés.
  Résultats corrigés : §6.

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

## 6. Étape 2 (2026-09-22) : où OpexAI perd les meilleures paires d'AAAHogEx

**Dispositif.** Sondes passives sous `probe_portfolio` (branche `c78-etape2-generation`, code agy
relu et corrigé par Claude) :
- `C78_AIRPOOL` (une génération aérienne par an) : villes triées par population avec rang, tuile,
  bornes de distance (`airMin`, `airMax`, `railMin`, `railMax`) et codes d'erreur de l'API publiés
  par l'IA elle-même ;
- `C78_AIRTOWN` / `C78_AIRPAIR` : issue de chaque ville et de chaque paire examinée, dans les trois
  bras (nouvelle paire, hub vers nouveau site, hub vers hub), avec la raison de rejet ;
- `C78_BUILD` : chaque tentative de chantier, avec rang, issue, raison, code du constructeur
  (`AFAIL`/`BFAIL` = aéroport A/B refusé) et erreur de l'API.

Duel 5 graines (42, 100, 7, 12345, 999) × 6 ans, villes corrigées (`results/diag_c78_etape2.json`,
non versionné ; analyse `sweeps/analyse_c78_etape2.py`). Smokes : défaut 2 × 3 et sonde sains. Le
défaut de la branche n'est pas identique au bit près à `master` (gardes de sonde dans des chemins
très appelés).

### 6.1 Classes corrigées (20 meilleures lignes d'AAAHogEx en 1973 et 1975)

| situation chez OpexAI | air | profit AAAHogEx de ces lignes |
|---|---:|---:|
| construite par les deux | 17 | — |
| dans le vivier la même année, non construite | 31 | 4,4 M£ |
| dans le vivier une année antérieure seulement | 50 | **7,8 M£** |
| jamais dans le vivier | 44 | 4,2 M£ |

Rail : 50 lignes (charbon, courrier, bétail et céréales, bois : du fret, 95 tuiles en médiane) ;
OpexAI avait un candidat exact pour 17 d'entre elles, n'en a construit aucune.

### 6.2 Les chantiers aériens échouent presque tous

Sur **2 644 tentatives de chantier aérien, 282 aboutissent (11 %)** :

| raison | tentatives |
|---|---:|
| trop de stations dans la ville (`AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN`, aéroport B ou A) | 698 |
| site B devenu inconstructible avant le chantier (`siteB_unbuildable`) | 605 |
| paire déjà abandonnée, pourtant toujours classée et retentée (`abandoned_pair`) | 568 |
| plan périmé (`batch_plan_dead`) | 257 |
| refus de la municipalité (`ERR_LOCAL_AUTHORITY_REFUSES`) | 73 |
| terrain non plat / zone encombrée | 109 |

Les paires d'AAAHogEx présentes une année puis sorties du vivier (7,8 M£) : **34 sur 50 ont été
tentées** (19 échecs de chantier, 7 paires abandonnées, 2 sites A, 1 plan périmé, 1 manque de
trésorerie ; 4 construites puis disparues). C'est la plus grosse poche : OpexAI **voit** ces lignes,
les classe, puis échoue à les construire, et la paire finit abandonnée.

### 6.3 La génération : le vivier des 24 villes, pas les bandes de distance

Paires jamais générées (44) : 34 ont une ville hors des 24 plus peuplées examinées par la génération
aérienne (`AIR_TOWN_POOL = 24`) ; ville fautive au rang 31,5 en médiane, 394 habitants. **Un vivier
de 48 villes laisse passer ce filtre aux 34.**

Les bandes de distance (question de l'utilisateur, `docs/03_decoupage_pax_candidates.md`) **ne sont
pas en cause** pour ces lignes : `airMin` = 94 tuiles, et seules 2 des 44 paires sont plus courtes ;
les meilleures liaisons d'AAAHogEx font 251 tuiles en médiane (85 au minimum).

### 6.4 Suites proposées (leviers derrière des réglages à défaut 0)

1. **Ne plus classer ce qui échouera** : écarter de la génération les villes dont la limite de
   stations est atteinte (le chantier échoue sur `ERR_STATION_TOO_MANY_STATIONS_IN_TOWN`),
   revalider les sites avant classement, et aligner la clé d'abandon de la génération sur celle du
   chantier (568 retentatives de paires abandonnées).
2. **Élargir le vivier de villes** : `AIR_TOWN_POOL` de 24 à 48, en réglage.
3. Rendement par avion sur les paires communes : inchangé depuis l'étape 1 (C81 a montré que le
   chargement complet seul ne l'explique pas).

## 7. Monopoles aériens : qui tient les créneaux des villes (2026-09-22)

Règle de la partie : sans niveau de bruit (`station_noise_level=false`), une ville accepte **deux
aéroports au plus, toutes compagnies confondues** (échec 771 au-delà, `taches.md` §771). Mesure sur le
même duel (5 graines ; aéroports rattachés à la ville la plus proche, villes corrigées) :

| aéroports (AAAHogEx, OpexAI) | villes fin 1972 | dont 24 plus grandes | villes fin 1975 | dont 24 plus grandes | profit aérien AAAHogEx attribué, 1975 |
|---|---:|---:|---:|---:|---:|
| **(2, 0) verrouillée par AAAHogEx** | 38 | **30** | 50 | **30** | 3,2 M£ |
| (1, 1) partagée | 73 | 70 | 94 | 80 | 4,1 M£ |
| (1, 0) | 42 | 8 | 28 | 0 | 0,7 M£ |
| (0, 1) | 9 | 9 | 9 | 8 | — |

- OpexAI n'a **jamais** deux aéroports dans une même ville ; AAAHogEx en a deux dans 8 grandes villes
  dès fin 1970.
- Les 30 grandes villes verrouillées fin 1972 : 16 étaient à (1, 0) au relevé de décembre précédent
  (fenêtre d'au moins un relevé pour prendre le second créneau), 8 déjà verrouillées fin 1970,
  6 passées de (0, 0) à (2, 0) entre deux relevés.
- **Placement périphérique rattaché à une ville voisine (piste n° 2 du 2026-09-15) : impossible sur
  ces cartes.** La voisine la plus proche ayant un créneau libre est à 40 tuiles en médiane d'une
  ville verrouillée, aucune à moins de 15.
- La note de gare n'explique pas la perte des villes partagées (`09_air_service_quality.md` : note
  voisine ou meilleure chez OpexAI sur 4/7 marchés) ; la captation, si (5 à 9 fois moins de
  passagers en attente par place chez OpexAI).
- OpexAI n'utilise aucune action municipale ; AAAHogEx construit des statues quand il est riche
  (`AAAHogEx-115/main.nut:3637`).

## 8. Course au second slot aéroportuaire — mesure du 22 septembre

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

## 9. C78.3/C78.4 — plafond grande carte et parcours AIR reprenable

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

## 10. C83.1 — fermeture du contrat de ville de slot (2026-09-24)

Le 20×10 précédent avait montré un effet territorial mais `opex_airport_before_second=0`. L'audit
des cas construits a trouvé que ce zéro mélangeait plusieurs notions de « ville » :

- le watcher utilisait `OpexAirTownServed`, qui signifie qu'une origine commerciale de ligne est à
  moins de 15 cases, pas qu'Opex occupe physiquement un slot de cette ville ;
- les projets et la sonde pouvaient rattacher le site via une ville différente de celle qui porte le
  verrou des deux aéroports ;
- la course C83 réutilisait directement la constante early-slot à 6 villes, ce qui empêchait
  d'expérimenter séparément sa largeur de surveillance ;
- le regroupement STNN du harnais n'est pas le TownID du slot moteur et ne peut donc pas servir de
  vérité terrain pour savoir qui a fermé le deuxième slot.

Le correctif donne donc à C83 sa propre constante `AIR_C83_TARGET_TOWNS`; le watcher construit une
fois par passe l'ensemble des aéroports Opex et les rattache par
`AITile.GetClosestTown(AIStation.GetLocation(st))`; une régénération ciblée impose
`ClosestTown(anchor)==targetTownId` et n'utilise pas le cache de site historique sur ce chemin rare.
Les parcours AIR ciblés ne conservent que les paires pouvant toucher cette cible. Enfin la sonde
publie les transitions directes `c83_slot_claimed` (Opex ferme le second slot) et `c83_slot_lost`
(le concurrent le ferme), qui sont la métrique correcte de cette course.

### Validation mécanique

- tests ciblés Docker : **9/9 OK** ; selftest `diag_1v1_shared_monthly.py` OK ;
- smoke sensible graines 999 et 65537 × 3 ans : **2/2 sain**, 20 événements watcher
  (5 `already_funded`, 15 `targeted_regen`), **13 slots claimed / 5 lost** ;
- ablation 5×6 du watcher corrigé : le cœur **6 villes** observe **19 watches, 16 claimed / 2 lost**
  (88,9 % des fermetures résolues), contre **44 watches, 33 claimed / 11 lost** avec 24 villes
  (75,0 %). Étendre 6→24 donne seulement **+13,8 k£/an** de `profit_year` moyen sur ces cinq graines
  mais **−182,9 k£** de valeur moyenne ; l'échantillon est trop petit pour une conclusion économique,
  mais les 18 villes marginales ont un taux de course moins propre. Le défaut final revient donc à
  **`AIR_C83_TARGET_TOWNS=6`**, tout en gardant la constante séparée pour de futures requalifications.

### Qualification causale 20×10 de l'expansion 24 villes

Les deux bras utilisent les 20 graines canoniques × 10 ans, 6 workers / 6 CPU, et terminent
**20/20 sains** au 1979-12-01. Les conteneurs parallèles sont autorisés par le protocole courant.

Économie Opex :

- `profit_year` : **+76 904 £/an** en moyenne, médiane **+53 741 £/an**, **13/7**, test des signes
  p=**0,263176**, IC95 normal indicatif **[-81,4 ; +235,2] k£/an** ;
- valeur d'entreprise : **−138 567 £** en moyenne, ratio des moyennes **−1,54 %**, **10/10** ;
- la règle standard 20×10 n'est donc **pas franchie** sur wins/p, même si le seuil utile moyen
  (+50 k£/an) et la garde valeur (−5 %) sont respectés ;
- l'écart de profit `Opex−AAAHogEx` s'améliore en moyenne d'environ **+60,1 k£/an**, mais l'écart
  de valeur se dégrade d'environ **−766,5 k£**.

Territoire STNN (utile pour comparer les bras, mais pas pour attribuer une fermeture de slot) :

| état `(AAAHogEx,OpexAI)` | contrôle fin 1972 | C83 fin 1972 | contrôle fin 1975 | C83 fin 1975 | contrôle fin 1979 | C83 fin 1979 |
|---|---:|---:|---:|---:|---:|---:|
| `(2,0)` monopole AAA | **142** | **119** | **184** | **178** | **215** | **193** |
| `(1,1)` partagé | 247 | 264 | 353 | 358 | 426 | 401 |
| `(0,2)` double Opex | 0 | **26** | 0 | **36** | 1 | **48** |

La mesure directe du verrou est plus nette : **200 `c83_slot_watch`**, dont 103 trouvent déjà un
candidat financé et 97 déclenchent une régénération ciblée ; **136 slots sont ensuite claimed par
Opex contre 57 lost**, soit **70,5 %** des fermetures observées. Le solde `claimed−lost` est positif
sur **17/20 graines** (exploratoire : test des signes p≈0,00258). Le binomial événement par événement
serait encore plus petit mais n'est pas utilisé comme preuve indépendante, les événements d'une même
graine étant corrélés.

Cette expansion prouve que C83.1 fonctionne comme **mécanisme territorial direct**, mais elle n'est
pas retenue comme largeur par défaut : le 20×10 reste 13/7 sur `profit_year`, et l'ablation 5×6
montre que les villes 7–24 diluent le taux de fermeture. Les **57 courses perdues** appartiennent donc
au diagnostic 24-villes, pas au reliquat du défaut final à six villes.

### Qualification causale 20×10 du défaut final à 6 villes

Le défaut final `AIR_C83_TARGET_TOWNS=6` a ensuite été rejoué sur les mêmes 20 graines canoniques
× 10 ans, 6 workers / 6 CPU, contre le même contrôle signal-off. Les deux bras sont **20/20 sains**
au 1979-12-01. Le contrôle publie bien 0 événement `c83_slot_watch/claimed/lost`, donc la largeur
6/24 n'intervient pas dans ce bras.

Économie Opex :

- `profit_year` : **+165 329 £/an** en moyenne, médiane **+230 108 £/an**, **15/5**,
  test des signes p=**0,041389**, IC95 normal indicatif **[+36,4 ; +294,2] k£/an** ;
- valeur d'entreprise : **+609 128 £** en moyenne, **13/7**, ratio des moyennes **+6,78 %** ;
- la règle standard 20×10 est donc **franchie** : effet moyen > +50 k£/an, au moins 15 victoires,
  p<0,05 et garde valeur largement respectée ;
- AAAHogEx recule en moyenne de **314 729 £/an** de `profit_year` et de **668 167 £** de valeur ;
  l'écart `Opex−AAAHogEx` s'améliore donc d'environ **+480,1 k£/an** en profit et **+1,277 M£**
  en valeur.

Territoire STNN, toujours utile pour la comparaison entre bras mais pas pour attribuer la fermeture
du slot moteur :

| état `(AAAHogEx,OpexAI)` | contrôle fin 1972 | C83-6 fin 1972 | contrôle fin 1975 | C83-6 fin 1975 | contrôle fin 1979 | C83-6 fin 1979 |
|---|---:|---:|---:|---:|---:|---:|
| `(2,0)` monopole AAA | **142** | **119** | **184** | **159** | **215** | **178** |
| `(1,1)` partagé | 247 | **284** | 353 | **372** | 426 | **435** |
| `(0,2)` double Opex | 0 | **12** | 0 | **15** | 1 | **15** |

La mesure directe du verrou sur le défaut final compte **76 watches** :
35 trouvent déjà un candidat financé et 41 déclenchent une régénération ciblée. Elles se résolvent
en **56 `c83_slot_claimed` contre 17 `c83_slot_lost`**, soit **76,7 %** des fermetures observées
en faveur d'Opex. Le solde `claimed−lost` est positif sur **17/20 graines**, négatif sur une et nul
sur deux ; test des signes exploratoire sur les graines non nulles p≈**0,000145**.

Conclusion : **C83.1 est terminé et qualifié avec le défaut final à 6 villes**, à la fois comme
mécanisme territorial direct et comme amélioration économique sur ce protocole. L'expansion à
24 villes reste un diagnostic utile mais n'est pas retenue.

Artefacts :
`results/diag_c83_slot_control_5x6_20260924.json`,
`results/diag_c83_slot_treatment_5x6_20260924.json`,
`results/diag_c83_slot_control_20x10_20260924.json` et
`results/diag_c83_slot_treatment_20x10_20260924.json` (expansion 24 villes), plus
`results/diag_c83_slot_final6_treatment_20x10_20260924.json` pour le défaut final à 6 villes.
