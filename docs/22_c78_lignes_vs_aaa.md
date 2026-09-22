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
