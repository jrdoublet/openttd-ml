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
